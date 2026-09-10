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
        product_category = "general"
        food_keywords = [
            "food", "fssai", "ingredients", "nutrition", "biscuit", "snack", "oil", "milk", "beverage",
            "tea", "coffee", "atta", "flour", "wheat", "rice", "dal", "pulse", "cereal", "grain",
            "spice", "masala", "sugar", "salt", "chocolate", "confectionery", "powder", "edible", "bread"
        ]
        if any(w in full_text for w in food_keywords):
            product_category = "food"
        elif any(w in full_text for w in ["cosmetic", "shampoo", "soap", "lotion", "cream", "dermatologically", "face wash"]):
            product_category = "cosmetics"
        elif any(w in full_text for w in ["pharma", "medicine", "tablets", "syrup", "capsule", "dosage"]):
            product_category = "pharmaceutical"

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
        context_confidence = 0.92 if product_category != "general" or market_context != "unknown" else 0.70

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
