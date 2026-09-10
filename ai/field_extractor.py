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
    def __init__(self):
        # MRP pattern — handles: MRP, M.R.P., Max Retail Price, Rs., INR, ₹
        self.mrp_pattern = re.compile(
            r"(?:m\.?r\.?p\.?|max(?:imum)?\s*retail\s*price|mrp\.?)[^0-9\n]{0,25}?([0-9]+(?:\.[0-9]{1,2})?)",
            re.IGNORECASE
        )
        # Also match "Rs. 150.00" or "₹ 150.00" standalone
        self.rs_pattern = re.compile(
            r"(?:rs\.?|inr|₹)\s*([0-9]+(?:\.[0-9]{1,2})?)",
            re.IGNORECASE
        )

        # Net quantity — handles: "Net Qty:", "Net Wt:", "Net Weight:", "250 g", "5.0 kg"
        self.qty_pattern = re.compile(
            r"(?:net\s*(?:qty|quantity|wt|weight|vol|volume|contents?)?[:\s]*)?([0-9]+(?:\.[0-9]+)?)\s*(kg|g|gm|grams?|l|liter|litres?|ml|m|cm|mm|n|units?|pcs|pieces)\b",
            re.IGNORECASE
        )

        # Manufacture / Packing date — handles: "Mfg.", "MFD", "Mfg. Date:", "Mig. Date:", "Pkd.", "Packed:"
        self.mfg_date_pattern = re.compile(
            r"(?:mfd\.?|mfg\.?|mig\.?|mlg\.?|mg\.?|manufactur(?:ed|ing)?|manulactur(?:ed|ing)?|pkd\.?|packed|date\s*of\s*(?:mfg|mfd|mig)|month\s*(?:&|and)?\s*year\s*of\s*(?:mfg|mfd|mig))\s*(?:on|date)?[:\s]*([0-9]{1,2}\s*[\/\.\-]\s*[0-9]{2,4}|[a-zA-Z]{3,9}\s*[0-9]{4})",
            re.IGNORECASE
        )

        # Packing date separately
        self.packing_date_pattern = re.compile(
            r"(?:packing\s*date|p\.?k\.?d\.?)[:\s]*([0-9]{1,2}\s*[\/\.\-]\s*[0-9]{2,4}|[a-zA-Z]{3,9}\s*[0-9]{4})",
            re.IGNORECASE
        )

        # Import date
        self.import_date_pattern = re.compile(
            r"(?:import(?:ed)?\s*date|import(?:ed)?\s*on)[:\s]*([0-9]{1,2}\s*[\/\.\-]\s*[0-9]{2,4}|[a-zA-Z]{3,9}\s*[0-9]{4})",
            re.IGNORECASE
        )

        # Best before / expiry
        self.exp_date_pattern = re.compile(
            r"(?:exp(?:iry|ires?)?|use\s*by|best\s*before|bb)[:\s\.]*([0-9]{1,2}\s*[\/\.\-]\s*[0-9]{2,4}|[0-9]{1,2}\s*months?|[a-zA-Z]{3,9}\s*[0-9]{4})",
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
            r"(?:consumer\s*(?:care|cale|caie)|customer\s*(?:care|cale)|helpline|call|toll[-\s]?free)[:\s]*([0-9][\d\s\-]{7,16})",
            re.IGNORECASE
        )
        self.consumer_care_email_pattern = re.compile(
            r"(?:consumer\s*(?:care|cale|caie)|customer\s*(?:care|cale)|email|e[-\s]?mail)[:\s]*([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})",
            re.IGNORECASE
        )

        # Manufacturer / Packer / Importer (handles OCR variants like Manulactured)
        self.manufacturer_pattern = re.compile(
            r"(?:manufactured\s*(?:&|and)?\s*packed\s*by|manulactured\s*(?:&|and)?\s*packed\s*by|manufactured\s*by|manulactured\s*by|mfg\.?\s*(?:&|and)?\s*pkd\.?\s*by|mfg\.?\s*by|mfd\.?\s*by|packed\s*by|marketed\s*by|imported\s*by)[:\s]*([^\n,]{3,60}?)(?=\s*(?:\n|,|address|123|plot|street|road|gst|gstin|consumer|net|mfd|mfg|best|exp|call|email|$))",
            re.IGNORECASE
        )

        # Address — pin code presence or city names
        self.pincode_pattern = re.compile(r"\b([1-9][0-9]{5})\b")

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

    def extract_fields(self, ocr_tokens: List[Dict[str, Any]]) -> Dict[str, Any]:
        extracted: Dict[str, Any] = {}

        if not ocr_tokens:
            return extracted

        full_text = " ".join([t.get("text", "") for t in ocr_tokens])

        # ── 1. MRP ──────────────────────────────────────────────────────────────
        mrp_match = self.mrp_pattern.search(full_text)
        if not mrp_match:
            # Try "Rs. 150.00" pattern as fallback
            mrp_match = self.rs_pattern.search(full_text)
        if mrp_match:
            raw = mrp_match.group(0)
            try:
                val = float(mrp_match.group(1))
                matched_ids = [t["id"] for t in ocr_tokens if any(w.lower() in t["text"].lower() for w in ["mrp", "rs", "₹", "price"])]
                extracted["mrp"] = {
                    "field_name": "mrp",
                    "raw_value": raw,
                    "normalized_value": f"₹{val:.2f}",
                    "numeric_value": val,
                    "confidence": 0.94,
                    "ocr_evidence_ids": matched_ids,
                    "extraction_method": "REGEX_PATTERN",
                    "evidence_state": "PRESENT"
                }
            except ValueError:
                pass

        # ── 2. Net Quantity ─────────────────────────────────────────────────────
        qty_match = self.qty_pattern.search(full_text)
        if qty_match:
            raw = qty_match.group(0)
            try:
                val = float(qty_match.group(1))
                unit = qty_match.group(2).lower()
                unit_norm_map = {
                    "g": "g", "gm": "g", "gram": "g", "grams": "g",
                    "kg": "kg",
                    "l": "L", "liter": "L", "liters": "L", "litre": "L", "litres": "L",
                    "ml": "mL"
                }
                unit_norm = unit_norm_map.get(unit, unit)
                matched_ids = [t["id"] for t in ocr_tokens if any(w.lower() in t["text"].lower() for w in ["net", "qty", "quantity"]) or unit in t["text"].lower()]
                extracted["net_quantity"] = {
                    "field_name": "net_quantity",
                    "raw_value": raw,
                    "normalized_value": f"{val} {unit_norm}",
                    "numeric_value": val,
                    "unit": unit_norm,
                    "confidence": 0.92,
                    "ocr_evidence_ids": matched_ids,
                    "extraction_method": "REGEX_PATTERN",
                    "evidence_state": "PRESENT"
                }
            except ValueError:
                pass

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

        return extracted

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

