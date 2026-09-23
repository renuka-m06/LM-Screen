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
            
            # Statutory Requirement Aliases
            if not field_data and field in ["manufacturer", "packer"]:
                field_data = (
                    extracted_fields.get("manufacturer_or_packer")
                    or extracted_fields.get("packer_name")
                    or extracted_fields.get("marketer_name")
                    or extracted_fields.get("manufacturer_name")
                )
            elif not field_data and field == "manufacture_date":
                field_data = extracted_fields.get("packing_date") or extracted_fields.get("import_date")
            elif not field_data and field == "fssai_license":
                field_data = extracted_fields.get("certifications")
            elif not field_data and field == "consumer_care":
                field_data = extracted_fields.get("email") or extracted_fields.get("consumer_care_phone")
            elif not field_data and field == "net_quantity":
                field_data = extracted_fields.get("declared_quantity")
            elif not field_data and field in ["best_before", "expiry_date"]:
                field_data = extracted_fields.get("best_before") or extracted_fields.get("expiry_date")
            elif not field_data and field == "batch_number":
                field_data = extracted_fields.get("batch_number")
                if not field_data and extracted_fields.get("packing_date"):
                    field_data = extracted_fields.get("packing_date")
            elif not field_data and field == "ingredients":
                p_name = str(extracted_fields.get("product_name", {}).get("normalized_value") or "").lower()
                if any(w in p_name for w in ["coriander", "leaf", "leaves", "fresh", "spinach", "mint", "herb", "vegetable"]):
                    field_data = {
                        "normalized_value": "Exempt (Fresh single-ingredient produce)",
                        "evidence_state": "SUPPORTED",
                        "ocr_evidence_ids": extracted_fields.get("product_name", {}).get("ocr_evidence_ids", [])
                    }
                
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
                # Field found, but what is its evidence state?
                ev_state = field_data.get("evidence_state", "SUPPORTED")
                
                if ev_state == "UNCERTAIN":
                    status = "REVIEW_REQUIRED"
                    reason = f"Required field '{field}' was extracted but evidence is uncertain (e.g. poor image quality or low OCR confidence)."
                elif ev_state == "CONFLICTING":
                    status = "REVIEW_REQUIRED"
                    reason = f"Required field '{field}' was extracted but cross-evidence checks found conflicts."
                elif ev_state == "UNREADABLE":
                    status = "REVIEW_REQUIRED"
                    reason = f"Required field '{field}' evidence region is unreadable."
                else:
                    # VERIFIED, SUPPORTED, MANUALLY_VERIFIED
                    status = "PASS"
                    reason = f"Required declaration '{field}' visible and supported by evidence."

            canonical_rule_ids = {
                "mrp": "LM001",
                "net_quantity": "LM002",
                "manufacture_date": "LM003",
                "packing_date": "LM003",
                "manufacturer": "LM004",
                "packer": "LM004",
                "address": "LM004_ADDR",
                "consumer_care": "LM005",
                "country_of_origin": "LM006",
                "batch_number": "LM012",
                "fssai_license": "LM013",
                "ingredients": "LM014",
                "best_before": "LM011",
                "product_name": "LM000_PROD",
            }
            assigned_rule_id = req.get("rule_id") or canonical_rule_ids.get(field, f"REQ_{field.upper()}")
            assigned_rule_name = req.get("name") or f"{field.replace('_', ' ').title()} Declaration"

            evidence_status = "SUPPORTED" if status == "PASS" else ("NOT_DETECTED" if status in ["MISSING", "NOT_DETECTED"] else "REVIEW_REQUIRED")

            traces.append({
                "rule_id": assigned_rule_id,
                "rule_name": assigned_rule_name,
                "field": field,
                "applicability": applicability,
                "status": status,
                "evidence_status": evidence_status,
                "legal_reference": legal_ref,
                "evidence_ids": evidence_ids,
                "reason": reason
            })

        return traces
