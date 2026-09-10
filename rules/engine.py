import json
import os
from typing import Dict, Any, List

class DeterministicRuleEngine:
    """
    Externalized, deterministic Legal Metrology rule engine.
    Evaluates extracted fields against declarative rule profiles.
    Generates auditable decision traces for every check performed.
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
                        pass
        return profiles

    def evaluate(
        self,
        extracted_fields: Dict[str, Any],
        context: Dict[str, Any],
        quality_status: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        traces: List[Dict[str, Any]] = []

        # Select rule profile based on product category context
        category = context.get("product_category", "general")
        profile_key = "LM_FOOD_2026.1" if category in ["food", "beverage"] else "LM_COMMON_2026.1"
        profile = self.loaded_profiles.get(profile_key) or self.loaded_profiles.get("LM_COMMON_2026.1")

        if not profile:
            # Default trace if profile loading fails
            return [{
                "rule_id": "LM000",
                "version": "2026.1",
                "status": "NEEDS_REVIEW",
                "applicable": True,
                "confidence": 0.5,
                "evidence_ids": [],
                "reason": "Rule profile definition file unavailable for evaluation."
            }]

        # Support parent profile inheritance (e.g. food profile inherits common rules)
        rules = list(profile.get("rules", []))
        parent_id = profile.get("parent_profile")
        if parent_id and parent_id in self.loaded_profiles:
            parent_profile = self.loaded_profiles[parent_id]
            parent_rules = parent_profile.get("rules", [])
            child_rule_ids = {r["rule_id"] for r in rules}
            # Append parent rules that are not already overridden by child
            for pr in parent_rules:
                if pr["rule_id"] not in child_rule_ids:
                    rules.append(pr)
        
        for rule in rules:
            rule_id = rule["rule_id"]
            req_fields = rule.get("required_fields", [])
            require_any = rule.get("require_any", False)
            applies_when = rule.get("applies_when", {})

            # Check rule applicability
            applicable = True
            if "origin" in applies_when:
                if context.get("origin") not in applies_when["origin"]:
                    applicable = False

            if not applicable:
                traces.append({
                    "rule_id": rule_id,
                    "rule_name": rule["name"],
                    "version": profile.get("version", "2026.1"),
                    "status": "NOT_APPLICABLE",
                    "applicable": False,
                    "confidence": 1.0,
                    "evidence_ids": [],
                    "reason": f"Rule not applicable for context: {context.get('origin', 'domestic')}."
                })
                continue

            # Evaluate presence of required fields
            present_fields = []
            evidence_ids = []
            for field_key in req_fields:
                # Handle manufacturer or packer combined key check
                if field_key == "manufacturer_or_packer":
                    if "manufacturer_or_packer" in extracted_fields or "manufacturer" in extracted_fields or "packer" in extracted_fields:
                        present_fields.append(field_key)
                        field_data = extracted_fields.get("manufacturer_or_packer") or extracted_fields.get("manufacturer")
                        if field_data:
                            evidence_ids.extend(field_data.get("ocr_evidence_ids", []))
                elif field_key in extracted_fields:
                    present_fields.append(field_key)
                    evidence_ids.extend(extracted_fields[field_key].get("ocr_evidence_ids", []))

            if quality_status.get("status") == "RETAKE_REQUIRED":
                # Insufficient image quality forces NEEDS_REVIEW on rules
                traces.append({
                    "rule_id": rule_id,
                    "rule_name": rule["name"],
                    "version": profile.get("version", "2026.1"),
                    "status": "NEEDS_REVIEW",
                    "applicable": True,
                    "confidence": 0.50,
                    "evidence_ids": [],
                    "reason": "Image quality insufficient for reliable declaration verification."
                })
            elif (require_any and len(present_fields) > 0) or (not require_any and len(present_fields) == len(req_fields)):
                traces.append({
                    "rule_id": rule_id,
                    "rule_name": rule["name"],
                    "version": profile.get("version", "2026.1"),
                    "status": "PASS",
                    "applicable": True,
                    "confidence": 0.94,
                    "evidence_ids": evidence_ids,
                    "reason": f"Required declaration visible and verified ({', '.join(present_fields)})."
                })
            else:
                missing = [f for f in req_fields if f not in present_fields]
                if require_any:
                    req_desc = f"At least one of ({', '.join(req_fields)})"
                else:
                    req_desc = f"Statutory declaration '{', '.join(missing)}'"

                if quality_status.get("status") == "PARTIALLY_USABLE":
                    status = "NEEDS_REVIEW"
                    reason = f"{req_desc} not detected, but image has partial clarity issues."
                else:
                    status = "POTENTIAL_NON_COMPLIANCE"
                    reason = f"Required statutory declaration ({req_desc}) missing from visible label panel."

                traces.append({
                    "rule_id": rule_id,
                    "rule_name": rule["name"],
                    "version": profile.get("version", "2026.1"),
                    "status": status,
                    "applicable": True,
                    "confidence": 0.88,
                    "evidence_ids": evidence_ids,
                    "reason": reason
                })

        return traces
