from typing import Dict, Any, List

class ContextClassifier:
    """
    Context Classifier for LM-Screen.
    Determines product category, package type, origin, market context, and geometry support.
    Market Context options: retail, institutional, industrial, wholesale, transport, unknown.
    """
    def classify_context(self, text_tokens: List[Dict[str, Any]], metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        if metadata is None:
            metadata = {}

        full_text = " ".join([t.get("text", "") for t in text_tokens]).lower()

        # 1. Product Category
        product_category = "CONTEXT_REVIEW_REQUIRED"
        category_scores = {
            "food": 0.0,
            "cosmetics": 0.0,
            "pharmaceutical": 0.0,
            "electronics": 0.0,
            "textile": 0.0,
            "cable": 0.0,
            "mattress": 0.0,
            "general": 0.1 # Baseline
        }
        
        food_keywords = ["food", "fssai", "ingredients", "nutrition", "biscuit", "snack", "oil", "milk", "beverage", "tea", "coffee", "atta", "flour", "wheat", "rice", "dal", "pulse", "cereal", "grain", "spice", "masala", "sugar", "salt", "chocolate", "confectionery", "powder", "edible", "bread"]
        for w in food_keywords:
            if w in full_text: category_scores["food"] += 0.2
            
        cosmetic_keywords = ["cosmetic", "shampoo", "soap", "lotion", "cream", "dermatologically", "face wash"]
        for w in cosmetic_keywords:
            if w in full_text: category_scores["cosmetics"] += 0.2
            
        pharma_keywords = ["pharma", "medicine", "tablets", "syrup", "capsule", "dosage"]
        for w in pharma_keywords:
            if w in full_text: category_scores["pharmaceutical"] += 0.2
            
        electronics_keywords = ["electronics", "voltage", "watt", "hz", "plug", "socket", "battery", "charger", "cable", "usb", "screen", "display"]
        for w in electronics_keywords:
            if w in full_text: category_scores["electronics"] += 0.2
            
        textile_keywords = ["textile", "cotton", "polyester", "fabric", "garment", "shirt", "pant", "size", "cm", "thread"]
        for w in textile_keywords:
            if w in full_text: category_scores["textile"] += 0.2
            
        cable_keywords = ["wire", "cable", "conductor", "insulation", "length", "sq mm"]
        for w in cable_keywords:
            if w in full_text: category_scores["cable"] += 0.2
            
        mattress_keywords = ["mattress", "foam", "bedding", "spring", "coir"]
        for w in mattress_keywords:
            if w in full_text: category_scores["mattress"] += 0.2
            
        best_category = max(category_scores, key=category_scores.get)
        best_score = category_scores[best_category]
        
        if best_score > 0.3:
            product_category = best_category
        else:
            product_category = "CONTEXT_REVIEW_REQUIRED"

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
        context_confidence = min(best_score, 1.0) if product_category != "CONTEXT_REVIEW_REQUIRED" else 0.4

        return {
            "product_category": product_category,
            "package_type": package_type,
            "origin": origin,
            "market_context": market_context,
            "geometry_supported": True,
            "single_or_multiple": "single",
            "manufacture_period": "post_2022_amendment",
            "context_confidence": context_confidence
        }
