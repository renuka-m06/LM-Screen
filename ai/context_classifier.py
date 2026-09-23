from typing import Dict, Any, List

class ContextClassifier:
    """
    Context Classifier for LM-Screen.
    Determines product category, package type, origin, market context, and geometry support.
    Market Context options: retail, institutional, industrial, wholesale, transport, unknown.
    """
    def classify_context(
        self,
        text_tokens: List[Dict[str, Any]],
        metadata: Dict[str, Any] = None,
        evidence_list: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        if metadata is None:
            metadata = {}
        if evidence_list is None:
            evidence_list = []

        full_text = " ".join([t.get("text", "") for t in text_tokens]).lower()

        # 1. Product Category Scoring
        category_scores = {
            "food": 0.0,
            "cosmetics": 0.0,
            "pharmaceutical": 0.0,
            "electronics": 0.0,
            "textile": 0.0,
            "cable": 0.0,
            "mattress": 0.0,
            "general": 0.1  # Baseline pre-packaged commodity
        }

        # ── Tier 2: OCR Semantic Evidence ─────────────────────────────────────────
        food_keywords = [
            "food", "fssai", "fsal", "license", "licence", "lic no", "ingredients", "nutrition",
            "coriander", "leaves", "cilantro", "mint", "spinach", "vegetable", "vegetables", "fruit", "fruits",
            "fresh", "produce", "herb", "herbs", "organic", "atta", "flour", "wheat", "rice", "dal", "pulse",
            "cereal", "grain", "spice", "spices", "masala", "sugar", "salt", "oil", "ghee", "milk", "paneer",
            "biscuit", "biscuits", "snack", "snacks", "cookie", "cookies", "chips", "chocolate", "confectionery",
            "edible", "bread", "beverage", "tea", "coffee", "juice", "jam", "pickle", "sauce",
            "use by", "best before", "packed on", "pkd on", "per serving", "net weight", "net wt"
        ]
        for w in food_keywords:
            if w in full_text:
                category_scores["food"] += 0.2

        cosmetic_keywords = [
            "cosmetic", "shampoo", "soap", "lotion", "cream", "dermatologically", "face wash",
            "sunscreen", "perfume", "deodorant", "hair oil", "body wash", "moisturizer"
        ]
        for w in cosmetic_keywords:
            if w in full_text:
                category_scores["cosmetics"] += 0.2

        pharma_keywords = [
            "pharma", "pharmaceutical", "medicine", "tablets", "syrup", "capsule", "dosage",
            "mg", "paracetamol", "prescription", "schedule h", "pharmacopoeia", "ip/bp/usp"
        ]
        for w in pharma_keywords:
            if w in full_text:
                category_scores["pharmaceutical"] += 0.2

        electronics_keywords = [
            "electronics", "voltage", "watt", "hz", "plug", "socket", "battery", "charger",
            "cable", "usb", "screen", "display", "input:", "output:", "mah", "amperes"
        ]
        for w in electronics_keywords:
            if w in full_text:
                category_scores["electronics"] += 0.2

        textile_keywords = [
            "textile", "cotton", "polyester", "fabric", "garment", "shirt", "pant", "size",
            "cm", "thread", "fibre", "wash care", "dry clean"
        ]
        for w in textile_keywords:
            if w in full_text:
                category_scores["textile"] += 0.2

        cable_keywords = ["wire", "cable", "conductor", "insulation", "length", "sq mm"]
        for w in cable_keywords:
            if w in full_text:
                category_scores["cable"] += 0.2

        mattress_keywords = ["mattress", "foam", "bedding", "spring", "coir"]
        for w in mattress_keywords:
            if w in full_text:
                category_scores["mattress"] += 0.2

        # ── Tier 3: Structured Declaration Evidence ───────────────────────────────
        ev_fields = {e.get("field") for e in evidence_list if e.get("found")}
        if "fssai_license" in ev_fields or "certifications" in ev_fields:
            category_scores["food"] += 0.5
        if "best_before" in ev_fields:
            category_scores["food"] += 0.4
        if "packing_date" in ev_fields and ("use by" in full_text or "best before" in full_text):
            category_scores["food"] += 0.3
        if "serving_size" in ev_fields or "nutrition_information" in ev_fields:
            category_scores["food"] += 0.5

        # Check product name evidence
        prod_ev = next((e for e in evidence_list if e.get("field") == "product_name"), None)
        if prod_ev and prod_ev.get("value"):
            p_val = str(prod_ev["value"]).lower()
            if any(k in p_val for k in ["coriander", "leaves", "atta", "tea", "coffee", "rice", "dal", "fresh", "biscuit", "chocolate"]):
                category_scores["food"] += 0.5

        # ── Tier 4 & 5: Classification Tier Resolution ────────────────────────────
        best_category = max(category_scores, key=category_scores.get)
        best_score = category_scores[best_category]

        has_structured_food_evidence = bool(
            ("fssai_license" in ev_fields or "certifications" in ev_fields or "best_before" in ev_fields)
            and best_category == "food"
        )
        has_semantic_evidence = best_score >= 0.3

        if has_structured_food_evidence:
            product_category = "food"
            method = "STRUCTURED_DECLARATION_EVIDENCE"
            status = "SUCCESS"
        elif has_semantic_evidence:
            product_category = best_category
            method = "OCR_SEMANTIC_ANALYSIS"
            status = "SUCCESS"
        elif len(ev_fields) >= 2:
            # Common declarations found (e.g. MRP + Net Qty), default to general commodity
            product_category = "general"
            method = "HEURISTIC_FALLBACK"
            status = "HEURISTIC_FALLBACK"
        else:
            product_category = "CONTEXT_REVIEW_REQUIRED"
            method = "INSUFFICIENT_EVIDENCE"
            status = "UNKNOWN"

        # 2. Market Context
        market_context = "retail"
        if "for institutional use only" in full_text or "not for retail sale" in full_text:
            market_context = "institutional"
        elif "industrial use only" in full_text:
            market_context = "industrial"
        elif "wholesale pack" in full_text:
            market_context = "wholesale"

        # 3. Origin
        origin = "domestic"
        if any(w in full_text for w in ["imported by", "country of origin", "made in china", "made in usa", "made in germany", "import date"]):
            origin = "imported"

        # 4. Package Type
        package_type = "pre_packaged_retail_unit"
        if "multi-pack" in full_text or "multipack" in full_text:
            package_type = "multi_pack"

        # Context confidence
        context_confidence = min(round(best_score, 2), 0.95) if product_category != "CONTEXT_REVIEW_REQUIRED" else 0.40

        return {
            "product_category": product_category,
            "package_type": package_type,
            "origin": origin,
            "market_context": market_context,
            "geometry_supported": True,
            "single_or_multiple": "single",
            "manufacture_period": "post_2022_amendment",
            "context_confidence": context_confidence,
            "classification_method": method,
            "classification_status": status
        }
