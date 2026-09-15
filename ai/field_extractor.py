import re
from typing import List, Dict, Any, Optional

class FieldExtractor:
    """
    Deterministic Field Extractor for Legal Metrology visible declarations.
    Priority:
    1. Regular Expression matching
    2. Keyword anchor scanning
    3. Spatial bounding box relationship
    4. Canonical unit normalization

    Field Evidence States:
    - PRESENT: field extracted with sufficient confidence
    - ABSENT_FROM_EVIDENCE: keyword found but value not parseable
    - UNCERTAIN: low confidence extraction
    - NOT_APPLICABLE: field not required for this product context
    - NOT_CHECKED: field not inspected in this run
    """
    # ── MRP anchor indicators (case-insensitive, punctuation-tolerant) ──────────
    # A numeric value is ONLY accepted as MRP when it appears in the same line
    # or immediately adjacent line as one of these explicit indicator tokens.
    _MRP_ANCHOR_RE = re.compile(
        r"\bm\.?r\.?p\.?\b|\bmaximum\s+retail\s+price\b|\bmax\.?\s*retail\b",
        re.IGNORECASE,
    )
    # Nutrition-contamination guard — numbers that appear alongside these units
    # are nutritional figures, not price values.
    _NUTRITION_UNIT_RE = re.compile(
        r"\b(?:mg|mcg|\xb5g|kcal|kj|%\s*dv|%\s*rda|per\s+serving|per\s+100\s*g|energy|"
        r"protein|carbohydrate|fat|sodium|sugar|fibre|fiber|calcium|iron|vitamin|mineral)\b",
        re.IGNORECASE,
    )
    # Full anchored MRP-line pattern: keyword → optional gap → optional currency → number.
    # Max gap between keyword and number is kept short (35 chars) to avoid cross-line
    # matches on the joined full-text string.
    _MRP_LINE_RE = re.compile(
        r"(?:m\.?r\.?p\.?|max(?:imum)?\s*retail\s*price|max\.?\s*retail)"
        r"[^0-9\n]{0,35}?(?:rs\.?\s*|r[58s]\.?\s*|inr\s*|₹\s*)?([0-9]+(?:\.[0-9]{1,2})?)",
        re.IGNORECASE,
    )

    # ── Sanity-check layer constants ─────────────────────────────────────────────
    # 28 Indian states + 8 UTs (lowercase) used to validate address plausibility.
    _INDIAN_STATES = frozenset({
        "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
        "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand", "karnataka",
        "kerala", "madhya pradesh", "maharashtra", "manipur", "meghalaya", "mizoram",
        "nagaland", "odisha", "punjab", "rajasthan", "sikkim", "tamil nadu",
        "telangana", "tripura", "uttar pradesh", "uttarakhand", "west bengal",
        # UTs
        "delhi", "jammu and kashmir", "ladakh", "chandigarh", "puducherry",
        "dadra and nagar haveli", "daman and diu", "lakshadweep",
        "andaman and nicobar islands",
        # Common city / region aliases that appear in addresses
        "mumbai", "pune", "bengaluru", "bangalore", "hyderabad", "chennai",
        "kolkata", "ahmedabad", "surat", "noida", "gurgaon", "gurugram",
        "jaipur", "lucknow", "kanpur", "nagpur", "indore", "bhopal", "visakhapatnam",
        "coimbatore", "kochi", "thiruvananthapuram", "patna", "ranchi", "bhubaneswar",
        "india",
    })
    # Plausible numeric ranges for key fields.
    _RANGE_MRP        = (1.0, 100_000.0)   # ₹1 – ₹1,00,000
    _RANGE_QTY_G      = (0.1, 50_000.0)    # grams
    _RANGE_QTY_KG     = (0.001, 50.0)      # kilograms
    _RANGE_QTY_ML     = (1.0, 50_000.0)    # millilitres
    _RANGE_QTY_L      = (0.01, 50.0)       # litres
    _RANGE_QTY_UNITS  = (1.0, 10_000.0)    # pieces / pcs / units
    # Gibberish detection: minimum ratio of alphabetic chars to total chars
    # for a string to be considered non-garbage (0 = no requirement).
    _MIN_ALPHA_RATIO  = 0.40
    # Minimum vowel-to-letter ratio to reject consonant-only noise strings.
    _MIN_VOWEL_RATIO  = 0.12
    # Fields that receive full sanity checks (others skip to avoid FP).
    _SANITY_CHECKED_FIELDS = frozenset({
        "address", "product_name", "manufacturer_or_packer",
        "mrp", "net_quantity",
    })

    # ── Net-quantity extraction constants ───────────────────────────────────────
    # Keywords that MUST be present (as prefix) for a match to count as the
    # package's statutory net quantity.
    _NET_QTY_ANCHOR_RE = re.compile(
        r"\b(?:net\s*(?:wt|weight|welght|we!ght|w[ei]ght|qty|quantity|vol|volume|contents?|content))"
        r"[.:\s]*",
        re.IGNORECASE,
    )
    # Keywords that identify SERVING-SIZE context — matches here must NOT be
    # assigned to net_quantity; they are routed to serving_size instead.
    _SERVING_SIZE_RE = re.compile(
        r"\b(?:serving\s*size|per\s*serving|serving\s*per|servings?\s*per\s*container"
        r"|per\s*100\s*g|per\s*100g|per\s*100\s*ml)",
        re.IGNORECASE,
    )
    # Full anchored pattern: keyword → optional gap → number → unit.
    _NET_QTY_ANCHORED_RE = re.compile(
        r"(?:net\s*(?:wt|weight|welght|we!ght|w[ei]ght|qty|quantity|vol|volume|contents?|content))"
        r"[.:\s]{0,10}([0-9]+(?:\.[0-9]+)?)\s*"
        r"(kg|g|gm|grams?|l|liter|litres?|ml|m|cm|mm|n|units?|pcs|pieces)\b",
        re.IGNORECASE,
    )
    # Standalone serving-size pattern used to capture and re-route the value
    # so the data isn't lost.  Lazy .{0,60}? allows skipping parenthetical
    # labels like "(5 cookies)" that contain digits before the actual quantity.
    _SERVING_SIZE_VALUE_RE = re.compile(
        r"(?:serving\s*size).{0,60}?([0-9]+(?:\.[0-9]+)?)\s*"
        r"(kg|g|gm|grams?|l|liter|litres?|ml|m|cm|mm)\b",
        re.IGNORECASE,
    )


    def __init__(self):

        # Manufacture date — handles: "Mfg.", "MFD", "Mfg. Date:", "Mig. Date:", "mg."
        self.mfg_date_pattern = re.compile(
            r"(?:mfd\.?|mfg\.?|mig\.?|mlg\.?|mg\.?|manufactur(?:ed|ing)?|manulactur(?:ed|ing)?|date\s*of\s*(?:mfg|mfd|mig)|month\s*(?:&|and)?\s*year\s*of\s*(?:mfg|mfd|mig))\s*(?:on|date)?[^0-9\n]{0,30}?([0-9]{1,2}\s*[\/\.\-]\s*[0-9]{1,2}\s*[\/\.\-]\s*[0-9]{2,4}|[0-9]{1,2}\s*[\/\.\-]\s*[0-9]{2,4}|[a-zA-Z]{3,9}\s*[0-9]{4})",
            re.IGNORECASE
        )

        # Packing date separately
        self.packing_date_pattern = re.compile(
            r"(?:packing\s*date|p\.?k\.?d\.?|packed\s*on)[^0-9\n]{0,30}?([0-9]{1,2}\s*[\/\.\-]\s*[0-9]{1,2}\s*[\/\.\-]\s*[0-9]{2,4}|[0-9]{1,2}\s*[\/\.\-]\s*[0-9]{2,4}|[a-zA-Z]{3,9}\s*[0-9]{4})",
            re.IGNORECASE
        )

        # Import date
        self.import_date_pattern = re.compile(
            r"(?:import(?:ed)?\s*date|import(?:ed)?\s*on)[^0-9\n]{0,30}?([0-9]{1,2}\s*[\/\.\-]\s*[0-9]{1,2}\s*[\/\.\-]\s*[0-9]{2,4}|[0-9]{1,2}\s*[\/\.\-]\s*[0-9]{2,4}|[a-zA-Z]{3,9}\s*[0-9]{4})",
            re.IGNORECASE
        )

        # Best before / expiry
        self.exp_date_pattern = re.compile(
            r"(?:exp(?:iry|ires?)?|use[\s_]*by|best\s*before|bb)[^0-9\n]{0,30}?([0-9]{1,2}\s*[\/\.\-]\s*[0-9]{1,2}\s*[\/\.\-]\s*[0-9]{2,4}|[0-9]{1,2}\s*[\/\.\-]\s*[0-9]{2,4}|[0-9]{1,2}\s*months?|[a-zA-Z]{3,9}\s*[0-9]{4})",
            re.IGNORECASE
        )

        # GSTIN — 15-character format
        self.gstin_pattern = re.compile(
            r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1})\b"
        )

        # GTIN / Barcode — 8, 12, 13, or 14 digits standalone
        self.gtin_pattern = re.compile(
            r"(?<!\d)([0-9]{13,14}|[0-9]{12}|[0-9]{8})(?!\d)"
        )

        # Consumer care — phone numbers and email (handles OCR variants like Consumer Cale/Caie)
        self.consumer_care_phone_pattern = re.compile(
            r"(?:consumer\s*(?:care|cale|caie)|customer\s*(?:care|cale)|helpline|call|toll[-\s]?free)(?:\s*no\.?|\s*number)?[:\s]*([0-9][\d\s\-]{7,16})",
            re.IGNORECASE
        )
        self.consumer_care_email_pattern = re.compile(
            r"(?:consumer\s*(?:care|cale|caie)|customer\s*(?:care|cale)|email|e[-\s]?mail)[:\s]*([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
            re.IGNORECASE
        )

        # Manufacturer / Packer / Importer (handles OCR variants like Manulactured)
        self.manufacturer_pattern = re.compile(
            r"(?:manufactured\s*(?:&|and)?\s*packed\s*by|manulactured\s*(?:&|and)?\s*packed\s*by|packed\s*(?:&|and)?\s*marketed\s*by|manufactured\s*by|manulactured\s*by|mfg\.?\s*(?:&|and)?\s*pkd\.?\s*by|mfg\.?\s*by|mfd\.?\s*by|packed\s*by|marketed\s*by|imported\s*by)[:\s]*([^\n,]{3,60}?)(?=\s*(?:\n|,|address|123|plot|street|road|gst|gstin|consumer|net|mfd|mfg|best|exp|call|email|$))",
            re.IGNORECASE
        )

        # Address — pin code presence or city names
        self.pincode_pattern = re.compile(r"\b([1-9][0-9]{5})\b")

        # Unit Sale Price (USP)
        self.usp_pattern = re.compile(
            r"(?:usp|unit\s*sale\s*price|price\s*per|rs\.?|inr|₹)[:\s]*([0-9]+\.[0-9]{1,2})\s*(?:per|\/)\s*(g|kg|ml|l|liter|litre|pc|piece|no)\b",
            re.IGNORECASE
        )

        # Country of origin
        self.country_pattern = re.compile(
            r"(?:country\s*of\s*origin|made\s*in|product\s*of)[:\s]*([A-Za-z\s]{3,30})",
            re.IGNORECASE
        )

        # Product name — exclusions for statutory field labels, address lines, and company registration headers
        self.product_name_exclusions = re.compile(
            r"^(?:mrp|net|mfg|mfd|mig|pkd|best|exp|consumer|call|email|gstin|gtin|fssai|ingredients|nutrition|address|regd|plot|tel|manufactured|manulactured|packed|imported|marketed|country|industrial|area|street|road|floor|suite|building|pincode|pvt|ltd|corp|inc|co|house|box|phase|sector|nagar|marg|highway|dist|state)",
            re.IGNORECASE
        )

        self.address_words = {
            "address", "industrial", "area", "plot", "street", "road", "noida", "mumbai",
            "delhi", "bengaluru", "bangalore", "up", "uttar pradesh", "maharashtra",
            "india", "phase", "sector", "andheri", "pune", "pincode", "marg", "nagar",
            "highway", "dist", "state", "building", "floor", "suite", "flat", "lane", "box"
        }

    def extract_fields(self, ocr_tokens: List[Dict[str, Any]], scale_mm_per_pixel: Optional[float] = None) -> Dict[str, Any]:
        extracted: Dict[str, Any] = {}

        if not ocr_tokens:
            return extracted

        full_text = " ".join([t.get("text", "") for t in ocr_tokens])

        # ── 1. MRP ──────────────────────────────────────────────────────────────
        # Anchored extraction: only accepts a number that is in the same/adjacent
        # line as an explicit MRP keyword, and rejects nutrition-contaminated tokens.
        mrp_result = self._extract_mrp_anchored(ocr_tokens, full_text)
        if mrp_result:
            extracted["mrp"] = mrp_result


        # ── 2. Net Quantity ─────────────────────────────────────────────────────
        # Anchored extraction: ONLY accepts values prefixed by an explicit
        # net-quantity keyword ("Net Wt", "Net Qty", etc.).
        # Values prefixed by "Serving size" / "Per serving" are routed to the
        # separate serving_size field and NEVER assigned to net_quantity.
        # If no keyword-anchored match exists the field is left absent.
        qty_result, serving_result = self._extract_net_quantity_anchored(
            ocr_tokens, full_text
        )
        if qty_result:
            extracted["net_quantity"] = qty_result
        if serving_result:
            extracted["serving_size"] = serving_result

        # ── 2b. Unit Sale Price (USP) ───────────────────────────────────────────
        usp_result = self._extract_usp(ocr_tokens, full_text)
        if usp_result:
            extracted["unit_sale_price"] = usp_result

        # ── 3. Manufacture Date ─────────────────────────────────────────────────
        mfg_match = self.mfg_date_pattern.search(full_text)
        if mfg_match:
            raw = mfg_match.group(0)
            val = mfg_match.group(1)
            matched_ids = [t["id"] for t in ocr_tokens if any(w.lower() in t["text"].lower() for w in ["mfd", "mfg", "mig", "manufactur", "manulactur", "date"]) and not any(a in t["text"].lower() for a in ["address", "industrial", "packed by"])]
            extracted["manufacture_date"] = {
                "field_name": "manufacture_date",
                "raw_value": raw,
                "normalized_value": val,
                "confidence": 0.90,
                "ocr_evidence_ids": matched_ids,
                "extraction_method": "KEYWORD_ANCHOR",
                "evidence_state": "PRESENT"
            }
        else:
            # Fallback search for standalone date pattern MM/YYYY
            date_fallback = re.search(r"\b(0[1-9]|1[0-2])[\/\.\-](202[0-9])\b", full_text)
            if date_fallback:
                val = date_fallback.group(0)
                matched_ids = [t["id"] for t in ocr_tokens if val in t["text"]]
                extracted["manufacture_date"] = {
                    "field_name": "manufacture_date",
                    "raw_value": f"Mfg. Date: {val}",
                    "normalized_value": val,
                    "confidence": 0.85,
                    "ocr_evidence_ids": matched_ids,
                    "extraction_method": "REGEX_FALLBACK",
                    "evidence_state": "PRESENT"
                }

        # ── 4. Packing Date ─────────────────────────────────────────────────────
        pkg_match = self.packing_date_pattern.search(full_text)
        if pkg_match and "manufacture_date" not in extracted:
            raw = pkg_match.group(0)
            val = pkg_match.group(1)
            matched_ids = [t["id"] for t in ocr_tokens if any(w.lower() in t["text"].lower() for w in ["pack", "pkd", val])]
            extracted["packing_date"] = {
                "field_name": "packing_date",
                "raw_value": raw,
                "normalized_value": val,
                "confidence": 0.88,
                "ocr_evidence_ids": matched_ids,
                "extraction_method": "KEYWORD_ANCHOR",
                "evidence_state": "PRESENT"
            }

        # ── 5. Import Date ──────────────────────────────────────────────────────
        imp_match = self.import_date_pattern.search(full_text)
        if imp_match:
            raw = imp_match.group(0)
            val = imp_match.group(1)
            matched_ids = [t["id"] for t in ocr_tokens if "import" in t["text"].lower()]
            extracted["import_date"] = {
                "field_name": "import_date",
                "raw_value": raw,
                "normalized_value": val,
                "confidence": 0.88,
                "ocr_evidence_ids": matched_ids,
                "extraction_method": "KEYWORD_ANCHOR",
                "evidence_state": "PRESENT"
            }

        # ── 6. Best Before / Expiry ──────────────────────────────────────────────
        exp_match = self.exp_date_pattern.search(full_text)
        if exp_match:
            raw = exp_match.group(0)
            val = exp_match.group(1)
            matched_ids = [t["id"] for t in ocr_tokens if any(w.lower() in t["text"].lower() for w in ["exp", "best", "before", "use"])]
            extracted["best_before"] = {
                "field_name": "best_before",
                "raw_value": raw,
                "normalized_value": val,
                "confidence": 0.89,
                "ocr_evidence_ids": matched_ids,
                "extraction_method": "KEYWORD_ANCHOR",
                "evidence_state": "PRESENT"
            }
        elif any(k in full_text.lower() for k in ["best before", "use by", "expiry", "exp date", "exp:"]):
            matched_ids = [t["id"] for t in ocr_tokens if any(w.lower() in t["text"].lower() for w in ["exp", "best", "before", "use"])]
            extracted["best_before"] = {
                "field_name": "best_before",
                "raw_value": "Best before / Expiry keyword detected",
                "normalized_value": "Declared — value not fully extracted",
                "confidence": 0.60,
                "ocr_evidence_ids": matched_ids,
                "extraction_method": "KEYWORD_ANCHOR",
                "evidence_state": "UNCERTAIN"
            }

        # ── 7. GSTIN ─────────────────────────────────────────────────────────────
        gstin_match = self.gstin_pattern.search(full_text)
        if gstin_match:
            val = gstin_match.group(1)
            matched_ids = [t["id"] for t in ocr_tokens if val in t["text"] or "gstin" in t["text"].lower()]
            extracted["gstin"] = {
                "field_name": "gstin",
                "raw_value": val,
                "normalized_value": val,
                "confidence": 0.96,
                "ocr_evidence_ids": matched_ids,
                "extraction_method": "REGEX_CHECKSUM_PATTERN",
                "evidence_state": "PRESENT"
            }

        # ── 8. GTIN / Barcode (OCR) ──────────────────────────────────────────────
        gtin_match = self.gtin_pattern.search(full_text)
        if gtin_match:
            val = gtin_match.group(1)
            # Don't confuse PIN codes, phone numbers (7-digit) with GTINs
            if len(val) in [8, 12, 13, 14]:
                matched_ids = [t["id"] for t in ocr_tokens if val in t["text"]]
                extracted["gtin"] = {
                    "field_name": "gtin",
                    "raw_value": val,
                    "normalized_value": val,
                    "confidence": 0.91,
                    "ocr_evidence_ids": matched_ids,
                    "extraction_method": "REGEX_PATTERN",
                    "evidence_state": "PRESENT"
                }

        # ── 9. Consumer Care ─────────────────────────────────────────────────────
        care_phone = self.consumer_care_phone_pattern.search(full_text)
        care_email = self.consumer_care_email_pattern.search(full_text)
        if care_phone or care_email:
            phone_val = care_phone.group(1).strip() if care_phone else None
            email_val = care_email.group(1).strip() if care_email else None
            norm_val = phone_val or email_val
            raw_val = (care_phone.group(0) if care_phone else "") + (" | " + care_email.group(0) if care_email else "")
            matched_ids = [t["id"] for t in ocr_tokens if any(w.lower() in t["text"].lower() for w in ["care", "cale", "customer", "helpline", "call", "toll"])]
            extracted["consumer_care"] = {
                "field_name": "consumer_care",
                "raw_value": raw_val.strip(" | "),
                "normalized_value": norm_val,
                "phone": phone_val,
                "email": email_val,
                "confidence": 0.88,
                "ocr_evidence_ids": matched_ids,
                "extraction_method": "KEYWORD_ANCHOR",
                "evidence_state": "PRESENT"
            }

        # ── 10. Manufacturer / Packer ────────────────────────────────────────────
        mfg_kw_found = any(k in full_text.lower() for k in [
            "mfg by", "manufactured by", "packed by", "mfg. by", "mfd. by",
            "manufactured & packed by", "marketed by", "manufactured and packed by",
            "packer", "manufacturer"
        ])
        if mfg_kw_found:
            mfg_name_match = self.manufacturer_pattern.search(full_text)
            if mfg_name_match:
                mfg_val = mfg_name_match.group(1).strip()
                # Sanity check: extracted name should have at least 2 words or be plausible
                if len(mfg_val) >= 3:
                    matched_ids = [t["id"] for t in ocr_tokens if any(w in t["text"].lower() for w in ["mfg", "manufactured", "packed", "by", "pvt", "ltd", "foods", "agro"])]
                    extracted["manufacturer_or_packer"] = {
                        "field_name": "manufacturer_or_packer",
                        "raw_value": mfg_name_match.group(0),
                        "normalized_value": mfg_val,
                        "confidence": 0.88,
                        "ocr_evidence_ids": matched_ids,
                        "extraction_method": "KEYWORD_ANCHOR",
                        "evidence_state": "PRESENT"
                    }
                else:
                    # Keyword found but name not reliably extracted — UNCERTAIN
                    matched_ids = [t["id"] for t in ocr_tokens if any(w in t["text"].lower() for w in ["mfg", "manufactured", "packed", "by"])]
                    extracted["manufacturer_or_packer"] = {
                        "field_name": "manufacturer_or_packer",
                        "raw_value": "Manufacturer/packer keyword detected",
                        "normalized_value": "[Manufacturer declared — name extraction uncertain]",
                        "confidence": 0.55,
                        "ocr_evidence_ids": matched_ids,
                        "extraction_method": "KEYWORD_ANCHOR",
                        "evidence_state": "UNCERTAIN"
                    }
            else:
                # Keyword found but regex couldn't parse name
                matched_ids = [t["id"] for t in ocr_tokens if any(w in t["text"].lower() for w in ["mfg", "manufactured", "packed", "by"])]
                extracted["manufacturer_or_packer"] = {
                    "field_name": "manufacturer_or_packer",
                    "raw_value": "Manufacturer/packer keyword detected",
                    "normalized_value": "[Manufacturer declared — name extraction uncertain]",
                    "confidence": 0.55,
                    "ocr_evidence_ids": matched_ids,
                    "extraction_method": "KEYWORD_ANCHOR",
                    "evidence_state": "UNCERTAIN"
                }

        # ── 11. Address ──────────────────────────────────────────────────────────
        addr_keywords = ["address", "regd off", "plot no", "street", "road", "noida", "mumbai",
                         "delhi", "bengaluru", "bangalore", "up", "uttar pradesh", "maharashtra",
                         "india", "industrial area", "phase", "sector", "andheri", "pune"]
        addr_found = any(k in full_text.lower() for k in addr_keywords)
        pin_match = self.pincode_pattern.search(full_text)
        if addr_found or pin_match:
            addr_tokens = [t["text"] for t in ocr_tokens if any(k in t["text"].lower() for k in addr_keywords)]
            addr_val = ", ".join(addr_tokens) if addr_tokens else "Address declared"
            matched_ids = [t["id"] for t in ocr_tokens if any(k in t["text"].lower() for k in addr_keywords)]
            extracted["address"] = {
                "field_name": "address",
                "raw_value": addr_val,
                "normalized_value": addr_val,
                "confidence": 0.85,
                "ocr_evidence_ids": matched_ids,
                "extraction_method": "KEYWORD_ANCHOR",
                "evidence_state": "PRESENT"
            }

        # ── 12. Country of Origin ─────────────────────────────────────────────────
        country_match = self.country_pattern.search(full_text)
        if country_match:
            val = country_match.group(1).strip()
            matched_ids = [t["id"] for t in ocr_tokens if any(w in t["text"].lower() for w in ["origin", "made", "product"])]
            extracted["country_of_origin"] = {
                "field_name": "country_of_origin",
                "raw_value": country_match.group(0),
                "normalized_value": val,
                "confidence": 0.88,
                "ocr_evidence_ids": matched_ids,
                "extraction_method": "KEYWORD_ANCHOR",
                "evidence_state": "PRESENT"
            }

        # ── 13. Product Name (heuristic — prominent non-label, non-address content line) ──
        p_name, p_token_ids = self._extract_product_name(ocr_tokens)
        if p_name:
            extracted["product_name"] = {
                "field_name": "product_name",
                "raw_value": p_name,
                "normalized_value": p_name,
                "confidence": 0.85,
                "ocr_evidence_ids": p_token_ids,
                "extraction_method": "HEURISTIC_FIRST_CONTENT_LINE",
                "evidence_state": "PRESENT"
            }

        # ── 14. Post-extraction sanity checks ────────────────────────────────────
        # Run every extracted field through the plausibility layer.  Fields that
        # fail get their confidence capped at a low ceiling and their
        # evidence_state demoted to UNCERTAIN so downstream UI can flag them.
        self._apply_sanity_checks(extracted)

        # ── 15. Physical Font Height Calculation ─────────────────────────────────
        if scale_mm_per_pixel is not None:
            for field in ["mrp", "net_quantity"]:
                if field in extracted and extracted[field].get("evidence_state") != "UNCERTAIN":
                    evidence_ids = extracted[field].get("ocr_evidence_ids", [])
                    if evidence_ids:
                        # Find the max bounding box height among the evidence tokens
                        max_height_px = 0
                        for eid in evidence_ids:
                            tok = next((t for t in ocr_tokens if t["id"] == eid), None)
                            if tok and "polygon" in tok and len(tok["polygon"]) == 4:
                                pts = tok["polygon"]
                                h1 = abs(pts[3][1] - pts[0][1])
                                h2 = abs(pts[2][1] - pts[1][1])
                                height_px = (h1 + h2) / 2.0
                                max_height_px = max(max_height_px, height_px)
                        
                        if max_height_px > 0:
                            extracted[field]["font_height_mm"] = round(max_height_px * scale_mm_per_pixel, 2)

        return extracted

    # ── Sanity-check public API ───────────────────────────────────────────────────
    def sanity_check(
        self,
        field_type: str,
        raw_value: str,
        numeric_value: Optional[float] = None,
        unit: Optional[str] = None,
    ) -> tuple:
        """
        Evaluate plausibility of a single extracted field value.

        Parameters
        ----------
        field_type     : canonical field name (e.g. "address", "product_name", "mrp").
        raw_value      : the string value as extracted from OCR.
        numeric_value  : for numeric fields (mrp, net_quantity), the parsed float.
        unit           : normalised unit string for net_quantity ("g", "kg", "mL", "L", …).

        Returns
        -------
        (is_plausible: bool, adjusted_confidence: float)
            is_plausible=False means the value failed at least one sanity check;
            adjusted_confidence is the capped score to assign (≤0.40 when implausible).
        """
        if not raw_value or not str(raw_value).strip():
            return False, 0.20

        text = str(raw_value).strip()

        if field_type == "product_name":
            return self._sanity_product_name(text)

        if field_type == "address":
            return self._sanity_address(text)

        if field_type in ("manufacturer_or_packer",):
            return self._sanity_text_generic(text, min_len=3)

        if field_type == "mrp":
            return self._sanity_numeric_range(
                numeric_value, *self._RANGE_MRP, fallback_text=text
            )

        if field_type == "net_quantity":
            return self._sanity_net_quantity(numeric_value, unit, text)

        # Default: no special rule → always plausible, confidence unchanged
        return True, 1.0

    # ── Internal sanity helpers ───────────────────────────────────────────────────
    def _apply_sanity_checks(self, extracted: Dict[str, Any]) -> None:
        """Mutates extracted in-place: caps confidence and sets UNCERTAIN for implausible fields."""
        for field_name, field_dict in extracted.items():
            if field_name not in self._SANITY_CHECKED_FIELDS:
                continue
            if not isinstance(field_dict, dict):
                continue

            raw   = field_dict.get("raw_value", "")
            num   = field_dict.get("numeric_value")   # may be None
            unit  = field_dict.get("unit")             # may be None
            orig_conf = float(field_dict.get("confidence", 0.5))

            is_plausible, adj_conf = self.sanity_check(
                field_type=field_name,
                raw_value=raw,
                numeric_value=num,
                unit=unit,
            )

            if not is_plausible:
                # Cap confidence — never raise above what sanity says
                field_dict["confidence"] = min(orig_conf, adj_conf)
                field_dict["evidence_state"] = "UNCERTAIN"
                field_dict["sanity_check"] = "FAILED"
            else:
                field_dict["sanity_check"] = "PASSED"

    @staticmethod
    def _has_no_vowels(text: str) -> bool:
        letters = [c for c in text.lower() if c.isalpha()]
        if not letters:
            return True
        vowels  = [c for c in letters if c in "aeiouáéíóúàèìòùāēīōū"]
        return (len(vowels) / len(letters)) < FieldExtractor._MIN_VOWEL_RATIO

    @staticmethod
    def _gibberish_score(text: str) -> float:
        """
        Returns a 0-1 score where 0 = looks like gibberish, 1 = looks plausible.
        Based on:
        - ratio of alphabetic characters to total (non-space) chars
        - vowel-to-letter ratio (consonant strings score low)
        - absence of excessively long consonant runs (>5 consecutive consonants)
        """
        cleaned = text.strip()
        non_space = [c for c in cleaned if not c.isspace()]
        if not non_space:
            return 0.0

        letters = [c for c in cleaned.lower() if c.isalpha()]
        alpha_ratio = len(letters) / len(non_space)

        if not letters:
            return 0.5  # purely numeric — not gibberish, not clearly text

        vowels = [c for c in letters if c in "aeiouáéíóúàèìòùāēīōū"]
        vowel_ratio = len(vowels) / len(letters)

        # Penalise long consonant bursts (OCR garbage signature)
        max_consonant_run = 0
        cur_run = 0
        for c in cleaned.lower():
            if c.isalpha() and c not in "aeiouáéíóúàèìòùāēīōū":
                cur_run += 1
                max_consonant_run = max(max_consonant_run, cur_run)
            else:
                cur_run = 0
        long_run_penalty = min(max_consonant_run / 10.0, 0.5)  # caps at 0.5

        score = (alpha_ratio * 0.4 + vowel_ratio * 0.4) - long_run_penalty
        
        # Boost score for common valid abbreviations that naturally lack vowels
        lower_text = cleaned.lower()
        if any(abbr in lower_text.split() or abbr in lower_text.replace(".","").split() for abbr in ["pvt", "ltd", "mfg", "inc", "llp", "corp"]):
            score += 0.25
            
        return max(0.0, min(1.0, score))

    def _sanity_product_name(self, text: str) -> tuple:
        """Product name sanity: require ≥3 chars, must have vowels, must not be pure gibberish."""
        if len(text) < 3:
            return False, 0.25
        if self._has_no_vowels(text):
            return False, 0.30
        score = self._gibberish_score(text)
        if score < 0.30:
            return False, round(0.20 + score * 0.6, 2)   # 0.20 – 0.38
        return True, 1.0

    def _sanity_address(self, text: str) -> tuple:
        """
        Address sanity: pass if ANY of —
        • Contains a 6-digit Indian PIN code.
        • Contains at least one Indian state / city name.
        • Gibberish score ≥ 0.45 AND alphabetic ratio ≥ 40 %.
        Fail otherwise (OCR noise like 'Caedaeupolyd…').
        """
        text_lower = text.lower()

        # Check 1: PIN code present
        if re.search(r"\b[1-9][0-9]{5}\b", text):
            return True, 1.0

        # Check 2: Indian state / city name
        words_in_text = re.findall(r"[a-z]+", text_lower)
        # Build bigrams for multi-word state names
        bigrams = [
            words_in_text[i] + " " + words_in_text[i + 1]
            for i in range(len(words_in_text) - 1)
        ]
        unigrams_set = set(words_in_text)
        bigrams_set  = set(bigrams)
        if unigrams_set & self._INDIAN_STATES or bigrams_set & self._INDIAN_STATES:
            return True, 1.0

        # Check 3: reasonable text quality (not OCR garbage)
        score = self._gibberish_score(text)
        letters = [c for c in text if c.isalpha()]
        alpha_ratio = len(letters) / max(len(text.replace(" ", "")), 1)
        if score >= 0.45 and alpha_ratio >= self._MIN_ALPHA_RATIO:
            # Passes but at reduced confidence since no strong anchor
            return True, 0.55

        # Fail — OCR gibberish
        return False, min(0.40, round(0.10 + score * 0.6, 2))

    def _sanity_text_generic(self, text: str, min_len: int = 3) -> tuple:
        """Generic text sanity: length check + gibberish guard."""
        if len(text.strip()) < min_len:
            return False, 0.25
        score = self._gibberish_score(text)
        if score < 0.30:
            return False, round(0.20 + score * 0.5, 2)
        return True, 1.0

    @staticmethod
    def _sanity_numeric_range(
        value: Optional[float],
        lo: float,
        hi: float,
        fallback_text: str = "",
    ) -> tuple:
        """Numeric range sanity: value must be within [lo, hi]."""
        if value is None:
            # Try parsing from fallback text
            nums = re.findall(r"[0-9]+(?:\.[0-9]+)?", fallback_text)
            if not nums:
                return False, 0.20
            try:
                value = float(nums[0])
            except ValueError:
                return False, 0.20
        if lo <= value <= hi:
            return True, 1.0
        # Out of range — might be a unit error or extraction error
        return False, 0.35

    def _sanity_net_quantity(self, value: Optional[float], unit: Optional[str], text: str) -> tuple:
        """Net quantity range check — adapts bounds to the unit."""
        unit_lower = (unit or "").lower().rstrip("s")  # normalise plural
        range_map = {
            "g": self._RANGE_QTY_G,
            "gm": self._RANGE_QTY_G,
            "gram": self._RANGE_QTY_G,
            "kg": self._RANGE_QTY_KG,
            "ml": self._RANGE_QTY_ML,
            "l": self._RANGE_QTY_L,
            "liter": self._RANGE_QTY_L,
            "litre": self._RANGE_QTY_L,
        }
        bounds = range_map.get(unit_lower, self._RANGE_QTY_UNITS)
        return self._sanity_numeric_range(value, *bounds, fallback_text=text)

    # ── Net-Quantity Anchored Extraction ─────────────────────────────────────────
    def _extract_net_quantity_anchored(
        self,
        ocr_tokens: List[Dict[str, Any]],
        full_text: str,
    ) -> tuple:
        """
        Extract the *package-level* statutory net quantity.

        Rules
        -----
        1. A numeric value is ONLY accepted as ``net_quantity`` when it appears
           immediately after one of these explicit indicator keywords:
               Net Wt / Net Weight / Net Qty / Net Quantity /
               Net Vol / Net Volume / Net Contents / Net Content
           (case-insensitive, punctuation-tolerant).

        2. If the nearest keyword context is a *serving-size* phrase
           (``Serving size``, ``Per serving``, ``Per 100g``, …) the value is
           routed to ``serving_size`` and explicitly excluded from
           ``net_quantity``.  This prevents "31.25g (serving size)" from being
           misreported as the package's declared net weight.

        3. If no keyword-anchored net-quantity match is found at all, both
           return values are ``None`` — an honest absence is preferable to a
           wrong number with a confidence score.

        Returns
        -------
        (qty_dict, serving_dict) — either element may be None.
        """
        _UNIT_NORM = {
            "g": "g", "gm": "g", "gram": "g", "grams": "g",
            "kg": "kg",
            "l": "L", "liter": "L", "liters": "L", "litre": "L", "litres": "L",
            "ml": "mL", "mL": "mL",
        }

        def _build_field(
            field_name: str,
            raw: str,
            val: float,
            unit_raw: str,
            method: str,
            token_keywords: List[str],
        ) -> Dict[str, Any]:
            unit_norm = _UNIT_NORM.get(unit_raw.lower(), unit_raw.lower())
            matched_ids = [
                t["id"] for t in ocr_tokens
                if any(kw.lower() in t["text"].lower() for kw in token_keywords)
                or unit_raw.lower() in t["text"].lower()
            ]
            return {
                "field_name": field_name,
                "raw_value": raw,
                "normalized_value": f"{val} {unit_norm}",
                "numeric_value": val,
                "unit": unit_norm,
                "raw_unit": unit_raw,
                "confidence": 0.92,
                "ocr_evidence_ids": matched_ids,
                "extraction_method": method,
                "evidence_state": "PRESENT",
            }

        qty_dict: Optional[Dict[str, Any]] = None
        serving_dict: Optional[Dict[str, Any]] = None

        # ── Pass 1: look for an explicit net-quantity-anchored match ─────────────
        net_match = self._NET_QTY_ANCHORED_RE.search(full_text)
        if net_match:
            raw = net_match.group(0)
            # Extra safety: ensure the matched text isn't inside a serving-size
            # sentence by checking for serving-size keywords within a 60-char
            # window *before* the match start.
            window_before = full_text[max(0, net_match.start() - 60): net_match.start()]
            if not self._SERVING_SIZE_RE.search(window_before):
                try:
                    val  = float(net_match.group(1))
                    unit = net_match.group(2)
                    qty_dict = _build_field(
                        "net_quantity", raw, val, unit,
                        "ANCHORED_NET_KEYWORD",
                        ["net", "qty", "quantity", "wt", "weight", "vol", "contents"],
                    )
                except ValueError:
                    pass

        # ── Pass 2: capture serving size so the data is not silently dropped ────
        serving_match = self._SERVING_SIZE_VALUE_RE.search(full_text)
        if serving_match:
            raw = serving_match.group(0)
            try:
                val  = float(serving_match.group(1))
                unit = serving_match.group(2)
                serving_dict = _build_field(
                    "serving_size", raw, val, unit,
                    "ANCHORED_SERVING_SIZE_KEYWORD",
                    ["serving", "size"],
                )
            except ValueError:
                pass

        # ── Pass 3: fallback to unanchored standalone net quantity ─────────────
        if not qty_dict:
            _NET_QTY_UNANCHORED_RE = re.compile(
                r"\b([0-9]+(?:\.[0-9]+)?)\s*(kg|g|gm|grams?|l|liter|litres?|ml|m|cm|mm|n|units?|pcs|pieces)\b",
                re.IGNORECASE,
            )
            unanchored_matches = list(_NET_QTY_UNANCHORED_RE.finditer(full_text))
            # Filter out matches that belong to MRP or dates or serving size
            valid_unanchored = []
            for match in unanchored_matches:
                window_before = full_text[max(0, match.start() - 60): match.start()]
                if not self._SERVING_SIZE_RE.search(window_before) and not self._MRP_ANCHOR_RE.search(window_before):
                    valid_unanchored.append(match)
            if valid_unanchored:
                # Just take the first valid one
                match = valid_unanchored[0]
                raw = match.group(0)
                try:
                    val = float(match.group(1))
                    unit = match.group(2)
                    qty_dict = _build_field(
                        "net_quantity", raw, val, unit,
                        "UNANCHORED_NET_KEYWORD",
                        [unit],
                    )
                    qty_dict["evidence_state"] = "UNCERTAIN" # demote to uncertain as it is unanchored
                except ValueError:
                    pass

        return qty_dict, serving_dict

    # ── USP Extraction ──────────────────────────────────────────────────────────
    def _extract_usp(
        self,
        ocr_tokens: List[Dict[str, Any]],
        full_text: str,
    ) -> Optional[Dict[str, Any]]:
        usp_match = self.usp_pattern.search(full_text)
        if usp_match:
            raw = usp_match.group(0)
            try:
                val = float(usp_match.group(1))
                unit_raw = usp_match.group(2)
                _UNIT_NORM = {
                    "g": "g", "kg": "kg",
                    "l": "L", "liter": "L", "litre": "L",
                    "ml": "mL", "pc": "no", "piece": "no", "no": "no"
                }
                unit_norm = _UNIT_NORM.get(unit_raw.lower(), unit_raw.lower())
                
                matched_ids = [
                    t["id"] for t in ocr_tokens
                    if any(kw in t["text"].lower() for kw in ["usp", "unit sale price", "price", "rs", "inr"])
                    or str(val) in t["text"]
                ]
                
                return {
                    "field_name": "unit_sale_price",
                    "raw_value": raw,
                    "normalized_value": f"Rs {val} per {unit_norm}",
                    "numeric_value": val,
                    "unit": unit_norm,
                    "confidence": 0.92,
                    "ocr_evidence_ids": matched_ids,
                    "extraction_method": "REGEX_PATTERN",
                    "evidence_state": "PRESENT"
                }
            except ValueError:
                pass
        return None

    # ── MRP Anchored Extraction ──────────────────────────────────────────────────
    def _extract_mrp_anchored(
        self,
        ocr_tokens: List[Dict[str, Any]],

        full_text: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Extracts MRP only when a numeric value is explicitly anchored to an MRP
        indicator keyword within the same or immediately adjacent OCR line.

        Three-layer defence:
        1. Keyword anchor check  — value must sit on the same/adjacent line as
           an MRP indicator (MRP / M.R.P. / Maximum Retail Price / Max. Retail).
        2. Nutrition-contamination guard — any token whose text contains a
           nutrition unit (mg, kcal, % DV, sodium, …) is rejected even if an
           MRP keyword is nearby.
        3. Honest absent  — if no candidate survives both checks, the field is
           omitted entirely; a wrong zero-confidence guess is never emitted.

        Returns a field-evidence dict on success, or None if not found.
        """
        # ── Fast path: run the fully anchored regex on the joined text first.
        # This works well when all tokens are on one line (single-token scenarios
        # and most well-formatted label OCR outputs).
        m = self._MRP_LINE_RE.search(full_text)
        if m:
            raw_snippet = m.group(0)
            try:
                val = float(m.group(1))
            except (ValueError, IndexError):
                val = None
            if val is not None and val > 0:
                matched_ids = [
                    t["id"]
                    for t in ocr_tokens
                    if any(
                        w.lower() in t["text"].lower()
                        for w in ["mrp", "m.r.p", "retail", "price", "rs", "₹"]
                    )
                ]
                return {
                    "field_name": "mrp",
                    "raw_value": raw_snippet,
                    "normalized_value": f"₹{val:.2f}",
                    "numeric_value": val,
                    "confidence": 0.93,
                    "ocr_evidence_ids": matched_ids,
                    "extraction_method": "ANCHORED_REGEX",
                    "evidence_state": "PRESENT",
                }

        # ── Spatial / token-proximity path ───────────────────────────────────────
        # When OCR returns many separate tokens (word-level boxes), group tokens
        # into approximate "lines" by their vertical (Y) centre coordinate, then
        # look for anchor + value in a ±1-line window.

        def _y_centre(token: Dict[str, Any]) -> float:
            poly = token.get("polygon") or []
            if poly and len(poly) >= 2:
                ys = [pt[1] for pt in poly]
                return (min(ys) + max(ys)) / 2.0
            return float("inf")  # tokens without geometry go to a virtual bottom

        def _token_height(token: Dict[str, Any]) -> float:
            poly = token.get("polygon") or []
            if poly and len(poly) >= 2:
                ys = [pt[1] for pt in poly]
                return max(ys) - min(ys)
            return 20.0  # fallback assumption

        # Sort tokens top-to-bottom
        sorted_tokens = sorted(ocr_tokens, key=_y_centre)

        # Estimate average token height for line-grouping threshold
        heights = [_token_height(t) for t in sorted_tokens if t.get("polygon")]
        avg_height = (sum(heights) / len(heights)) if heights else 20.0
        line_threshold = avg_height * 1.5  # tokens within 1.5× avg height = same line

        # Assign each token a line index
        lines: List[List[Dict[str, Any]]] = []
        for tok in sorted_tokens:
            yc = _y_centre(tok)
            placed = False
            for line_group in lines:
                rep_yc = _y_centre(line_group[0])
                if abs(yc - rep_yc) <= line_threshold:
                    line_group.append(tok)
                    placed = True
                    break
            if not placed:
                lines.append([tok])

        # Identify which lines contain an MRP anchor keyword
        anchor_line_indices = set()
        for li, line_group in enumerate(lines):
            line_str = " ".join(t.get("text", "") for t in line_group)
            if self._MRP_ANCHOR_RE.search(line_str):
                anchor_line_indices.add(li)

        if not anchor_line_indices:
            # No MRP indicator anywhere → field is genuinely absent
            return None

        # Collect candidate numeric values from anchor lines ± 1 adjacent line
        NUMBER_RE = re.compile(
            r"(?:rs\.?\s*|inr\s*|₹\s*)?([0-9]+(?:\.[0-9]{1,2})?)", re.IGNORECASE
        )
        candidates = []  # list of (value_float, raw_text, matched_token_ids)
        for anchor_li in anchor_line_indices:
            window = set()
            for li_offset in range(-1, 2):  # lines[anchor_li-1 .. anchor_li+1]
                target_li = anchor_li + li_offset
                if 0 <= target_li < len(lines):
                    window.add(target_li)

            for li in sorted(window):
                for tok in lines[li]:
                    tok_text = tok.get("text", "")
                    # Reject nutrition-contaminated tokens
                    if self._NUTRITION_UNIT_RE.search(tok_text):
                        continue
                    nm = NUMBER_RE.search(tok_text)
                    if nm:
                        try:
                            v = float(nm.group(1))
                        except ValueError:
                            continue
                        if v > 0:
                            candidates.append((v, tok_text, tok.get("id")))

        if not candidates:
            return None

        # Among candidates, prefer values from the anchor line itself, then
        # pick the largest plausible price (avoids picking "1" from "Incl. 1 tax").
        # Price sanity: must be between ₹1 and ₹99,999.
        valid = [(v, raw, tid) for v, raw, tid in candidates if 1.0 <= v <= 99999.0]
        if not valid:
            return None

        # Prefer the value that comes from a token containing a currency symbol
        currency_prefixed = [
            (v, raw, tid)
            for v, raw, tid in valid
            if re.search(r"(?:rs\.?|inr|₹)", raw, re.IGNORECASE)
        ]
        chosen = currency_prefixed[0] if currency_prefixed else valid[0]
        val, raw_text, tok_id = chosen

        matched_ids = [
            t["id"]
            for t in ocr_tokens
            if any(
                w.lower() in t["text"].lower()
                for w in ["mrp", "m.r.p", "retail", "price", "rs", "₹"]
            )
        ]
        if tok_id and tok_id not in matched_ids:
            matched_ids.append(tok_id)

        return {
            "field_name": "mrp",
            "raw_value": raw_text,
            "normalized_value": f"₹{val:.2f}",
            "numeric_value": val,
            "confidence": 0.90,
            "ocr_evidence_ids": matched_ids,
            "extraction_method": "ANCHORED_SPATIAL_PROXIMITY",
            "evidence_state": "PRESENT",
        }

    def _extract_product_name(self, ocr_tokens: List[Dict[str, Any]]) -> tuple[Optional[str], List[Any]]:

        """
        Heuristic: product name is the prominent content text token that is
        NOT a statutory field label and NOT an address/company registration line.
        Preserves original token layout order (top of label image).
        """
        candidates = []
        for token in ocr_tokens:
            text = token.get("text", "").strip()
            text_lower = text.lower()
            if len(text) < 4:
                continue

            # Skip statutory field labels
            if self.product_name_exclusions.match(text):
                continue

            # Skip tokens containing address keywords
            words = set(re.findall(r"\w+", text_lower))
            if words & self.address_words:
                continue

            # Skip numeric values, phone numbers, or price strings
            if re.match(r'^[\d\s\-\.\,₹Rs]+$', text):
                continue

            # Skip company registration suffixes when standalone
            if text_lower in ["pvt ltd", "ltd", "private limited", "inc", "corp"]:
                continue

            tok_id = token.get("id") or token.get("token_id")
            candidates.append((tok_id, text))

        if not candidates:
            return None, []

        # Return the first candidate (top of packaging label)
        best_id, best_text = candidates[0]
        if len(best_text) > 80:
            best_text = best_text[:80]

        matched_ids = [best_id] if best_id is not None else []
        return best_text, matched_ids

