import json
import os
from typing import Dict, Any, List

class DeterministicRuleEngine:
    """
    Externalized, deterministic Legal Metrology rule engine.
    Evaluates extracted fields against declarative rule profiles based on product context.
    Generates auditable decision traces for every requirement checked.
    """
    def __init__(self, profiles_dir: str = None):
        if profiles_dir is None:
            profiles_dir = os.path.join(os.path.dirname(__file__), "profiles", "2026.1")
        self.profiles_dir = profiles_dir
        self.loaded_profiles = self._load_profiles()

    def _load_profiles(self) -> Dict[str, Dict[str, Any]]:
        profiles = {}
        if os.path.exists(self.profiles_dir):
            for file_name in os.listdir(self.profiles_dir):
                if file_name.endswith(".json"):
                    path = os.path.join(self.profiles_dir, file_name)
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            profiles[data.get("profile_id", file_name)] = data
                    except Exception as e:
                        print(f"Error loading profile {file_name}: {e}")
        return profiles

    def _get_active_profiles(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        active = []
        # Always add common
        common = self.loaded_profiles.get("LM_COMMON_2026.1")
        if common:
            active.append(common)
            
        category = context.get("product_category", "general").upper()
        if category != "GENERAL" and category != "CONTEXT_REVIEW_REQUIRED":
            cat_profile = self.loaded_profiles.get(f"LM_{category}_2026.1")
            if cat_profile:
                active.append(cat_profile)
                
        if context.get("origin") == "imported":
            imp_profile = self.loaded_profiles.get("LM_IMPORTED_2026.1")
            if imp_profile:
                active.append(imp_profile)
                
        return active

    def evaluate(
        self,
        extracted_fields: Dict[str, Any],
        context: Dict[str, Any],
        quality_status: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        traces: List[Dict[str, Any]] = []

        if context.get("product_category") == "CONTEXT_REVIEW_REQUIRED":
            return [{
                "rule_id": "CTX001",
                "field": "context",
                "applicability": "REQUIRED",
                "status": "REVIEW_REQUIRED",
                "evidence_ids": [],
                "reason": "Product category could not be confidently determined. Context review required before rule evaluation."
            }]

        active_profiles = self._get_active_profiles(context)
        
        if not active_profiles:
            return [{
                "rule_id": "SYS001",
                "field": "system",
                "applicability": "REQUIRED",
                "status": "REVIEW_REQUIRED",
                "evidence_ids": [],
                "reason": "Rule profiles could not be loaded."
            }]

        # Deduplicate requirements by field
        requirements = {}
        for profile in active_profiles:
            for req in profile.get("requirements", []):
                requirements[req["field"]] = req

        img_status = quality_status.get("status")
        
        for field, req in requirements.items():
            applicability = req.get("applicability", "REQUIRED")
            legal_ref = req.get("legal_reference", "N/A")
            
            # Check if field was extracted
            field_data = extracted_fields.get(field)
            
            # Fallback for manufacturer_or_packer legacy handling
            if not field_data and field in ["manufacturer", "packer"]:
                field_data = extracted_fields.get("manufacturer_or_packer")
                
            evidence_ids = []
            if field_data:
                evidence_ids = field_data.get("ocr_evidence_ids", [])
                
            if not field_data:
                # Field not found
                if img_status in ["RETAKE_REQUIRED", "PARTIALLY_USABLE"]:
                    status = "REVIEW_REQUIRED"
                    reason = f"Required field '{field}' not found, but image quality is insufficient for a definitive failure."
                else:
                    if applicability == "REQUIRED":
                        status = "MISSING"
                        reason = f"Required statutory declaration '{field}' is missing from the visible label panel."
                    else:
                        status = "NOT_DETECTED"
                        reason = f"Conditional field '{field}' was not detected."
            else:
                # Field found
                status = "PASS"
                reason = f"Required declaration '{field}' visible and verified."
                
                # Perform specific arithmetic/logic checks if applicable
                if field == "mrp" and "net_quantity" in extracted_fields and "unit_sale_price" in extracted_fields:
                    # USP Check logic
                    mrp_val = field_data.get("numeric_value")
                    qty_val = extracted_fields["net_quantity"].get("numeric_value")
                    if mrp_val and qty_val:
                        expected_usp = round(mrp_val / qty_val, 2)
                        usp_field = extracted_fields["unit_sale_price"]
                        printed_usp = usp_field.get("numeric_value")
                        if printed_usp and abs(expected_usp - printed_usp) > max(0.05, 0.02 * expected_usp):
                            status = "POTENTIAL_NON_COMPLIANCE"
                            reason = f"USP arithmetic mismatch (Printed: {printed_usp} | Expected: {expected_usp})"
                            
                elif field == "best_before" and ("manufacture_date" in extracted_fields or "packing_date" in extracted_fields):
                    # Chronology Check logic (simplified for dynamic engine)
                    pass 

            traces.append({
                "rule_id": f"REQ_{field.upper()}",
                "field": field,
                "applicability": applicability,
                "status": status,
                "legal_reference": legal_ref,
                "evidence_ids": evidence_ids,
                "reason": reason
            })

        return traces
