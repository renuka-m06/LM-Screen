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
            if rule_id in ("LM003", "LM008"):
                print(f"\\n--- DEBUG {rule_id} INPUT ---")
                if rule_id == "LM003":
                    print(json.dumps({
                        "manufacture_date": extracted_fields.get("manufacture_date"),
                        "packing_date": extracted_fields.get("packing_date"),
                        "import_date": extracted_fields.get("import_date")
                    }, indent=2))
                elif rule_id == "LM008":
                    print(json.dumps({
                        "mrp": extracted_fields.get("mrp"),
                        "net_quantity": extracted_fields.get("net_quantity"),
                        "unit_sale_price": extracted_fields.get("unit_sale_price")
                    }, indent=2))
                print("---------------------------")

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

            if rule_id == "LM007":
                scale = context.get("scale_mm_per_pixel")
                pdp_box = context.get("pdp_crop_box")
                if not scale or not pdp_box:
                    traces.append({
                        "rule_id": rule_id,
                        "rule_name": rule["name"],
                        "version": profile.get("version", "2026.1"),
                        "status": "NEEDS_REVIEW",
                        "applicable": True,
                        "confidence": 0.5,
                        "evidence_ids": evidence_ids,
                        "reason": "Physical scale or panel area could not be determined. Cannot measure font heights."
                    })
                    continue
                
                pdp_area_cm2 = ((pdp_box[2] * scale) * (pdp_box[3] * scale)) / 100.0
                
                min_height_mm = 1.0
                if pdp_area_cm2 > 2500: min_height_mm = 6.0
                elif pdp_area_cm2 > 500: min_height_mm = 4.0
                elif pdp_area_cm2 > 100: min_height_mm = 2.5
                elif pdp_area_cm2 > 50: min_height_mm = 1.5
                
                fails = []
                for field_key in req_fields:
                    if field_key in extracted_fields:
                        measured = extracted_fields[field_key].get("font_height_mm")
                        if measured is not None and measured < min_height_mm:
                            fails.append(f"{field_key} ({measured}mm < {min_height_mm}mm)")
                
                if fails:
                    traces.append({
                        "rule_id": rule_id,
                        "rule_name": rule["name"],
                        "version": profile.get("version", "2026.1"),
                        "status": "POTENTIAL_NON_COMPLIANCE",
                        "applicable": True,
                        "confidence": 0.90,
                        "evidence_ids": evidence_ids,
                        "reason": f"Measured numerals fail Schedule II minimums (PDP Area {pdp_area_cm2:.1f} cm² requires ≥ {min_height_mm}mm): {', '.join(fails)}"
                    })
                else:
                    traces.append({
                        "rule_id": rule_id,
                        "rule_name": rule["name"],
                        "version": profile.get("version", "2026.1"),
                        "status": "PASS",
                        "applicable": True,
                        "confidence": 0.90,
                        "evidence_ids": evidence_ids,
                        "reason": f"Measured numerals meet Schedule II minimums (PDP Area {pdp_area_cm2:.1f} cm² requires ≥ {min_height_mm}mm)."
                    })
                continue

            if rule_id == "LM008":
                mrp_field = extracted_fields.get("mrp")
                qty_field = extracted_fields.get("net_quantity")
                usp_field = extracted_fields.get("unit_sale_price")
                
                if not mrp_field or not qty_field:
                    traces.append({
                        "rule_id": rule_id,
                        "rule_name": rule["name"],
                        "version": profile.get("version", "2026.1"),
                        "status": "NEEDS_REVIEW",
                        "applicable": True,
                        "confidence": 0.5,
                        "evidence_ids": evidence_ids,
                        "reason": "cannot verify — required fields missing"
                    })
                    continue

                if mrp_field.get("evidence_state") == "UNCERTAIN" or qty_field.get("evidence_state") == "UNCERTAIN":
                    traces.append({
                        "rule_id": rule_id,
                        "rule_name": rule["name"],
                        "version": profile.get("version", "2026.1"),
                        "status": "NEEDS_REVIEW",
                        "applicable": True,
                        "confidence": 0.5,
                        "evidence_ids": evidence_ids,
                        "reason": "cannot verify — MRP or Net Quantity is uncertain"
                    })
                    continue

                mrp_val = mrp_field.get("numeric_value")
                qty_val = qty_field.get("numeric_value")
                qty_unit = qty_field.get("unit", "").lower()

                if mrp_val is None or qty_val is None or not qty_unit:
                    traces.append({
                        "rule_id": rule_id,
                        "rule_name": rule["name"],
                        "version": profile.get("version", "2026.1"),
                        "status": "NEEDS_REVIEW",
                        "applicable": True,
                        "confidence": 0.5,
                        "evidence_ids": evidence_ids,
                        "reason": "cannot verify — numeric values missing"
                    })
                    continue

                # Normalize qty based on Rule 6(11) magnitude thresholds
                norm_qty_val = qty_val
                base_unit = qty_unit
                if qty_unit == "g" and qty_val >= 1000:
                    norm_qty_val = qty_val / 1000.0
                    base_unit = "kg"
                elif qty_unit == "kg" and qty_val < 1:
                    norm_qty_val = qty_val * 1000.0
                    base_unit = "g"
                elif qty_unit == "ml" and qty_val >= 1000:
                    norm_qty_val = qty_val / 1000.0
                    base_unit = "L"
                elif qty_unit in ["l", "litre", "liters"] and qty_val < 1:
                    norm_qty_val = qty_val * 1000.0
                    base_unit = "mL"
                
                # Special normalisation for unit matching (L vs mL)
                if base_unit.lower() == "l": base_unit = "L"
                if base_unit.lower() == "ml": base_unit = "mL"

                expected_usp = round(mrp_val / norm_qty_val, 2)
                
                if not usp_field:
                    traces.append({
                        "rule_id": rule_id,
                        "rule_name": rule["name"],
                        "version": profile.get("version", "2026.1"),
                        "status": "NEEDS_REVIEW",
                        "applicable": True,
                        "confidence": 0.50,
                        "evidence_ids": evidence_ids,
                        "reason": f"Unit Sale Price declaration missing (Expected: Rs {expected_usp}/{base_unit}). Needs manual review to confirm if rule is applicable or if OCR failed to extract it."
                    })
                    continue

                printed_usp = usp_field.get("numeric_value")
                printed_unit = usp_field.get("unit")
                
                if printed_unit.lower() != base_unit.lower():
                    # Handle mismatch in unit printed vs expected base unit
                    traces.append({
                        "rule_id": rule_id,
                        "rule_name": rule["name"],
                        "version": profile.get("version", "2026.1"),
                        "status": "POTENTIAL_NON_COMPLIANCE",
                        "applicable": True,
                        "confidence": 0.90,
                        "evidence_ids": evidence_ids + usp_field.get("ocr_evidence_ids", []),
                        "reason": f"USP unit mismatch (Printed: {printed_unit} | Expected base: {base_unit})"
                    })
                    continue

                diff = abs(expected_usp - printed_usp)
                tol = max(0.05, 0.02 * expected_usp)
                
                if diff > tol:
                    traces.append({
                        "rule_id": rule_id,
                        "rule_name": rule["name"],
                        "version": profile.get("version", "2026.1"),
                        "status": "POTENTIAL_NON_COMPLIANCE",
                        "applicable": True,
                        "confidence": 0.90,
                        "evidence_ids": evidence_ids + usp_field.get("ocr_evidence_ids", []),
                        "reason": f"USP arithmetic mismatch (Printed USP: Rs {printed_usp}/{printed_unit} | Expected: Rs {expected_usp}/{base_unit})"
                    })
                else:
                    traces.append({
                        "rule_id": rule_id,
                        "rule_name": rule["name"],
                        "version": profile.get("version", "2026.1"),
                        "status": "PASS",
                        "applicable": True,
                        "confidence": 0.90,
                        "evidence_ids": evidence_ids + usp_field.get("ocr_evidence_ids", []),
                        "reason": f"USP verified (Printed USP: Rs {printed_usp}/{printed_unit} matches Expected: Rs {expected_usp}/{base_unit})"
                    })
                continue

            if rule_id == "LM009":
                qty_field = extracted_fields.get("net_quantity")
                if not qty_field:
                    traces.append({
                        "rule_id": rule_id,
                        "rule_name": rule["name"],
                        "version": profile.get("version", "2026.1"),
                        "status": "NEEDS_REVIEW",
                        "applicable": True,
                        "confidence": 0.5,
                        "evidence_ids": evidence_ids,
                        "reason": "cannot verify — required field (net_quantity) missing"
                    })
                    continue
                
                raw_unit = qty_field.get("raw_unit", "")
                raw_unit_lower = raw_unit.lower()
                
                correct = None
                if raw_unit_lower in ["gms", "grms", "gm"]:
                    correct = "g"
                elif raw_unit_lower in ["kilos", "kgs"]:
                    correct = "kg"
                elif raw_unit_lower in ["ltrs", "lts", "liters", "litres"]:
                    correct = "L"
                elif raw_unit_lower in ["mts", "mtrs"]:
                    correct = "m"
                elif raw_unit == "ML":
                    correct = "mL"
                
                if correct:
                    traces.append({
                        "rule_id": rule_id,
                        "rule_name": rule["name"],
                        "version": profile.get("version", "2026.1"),
                        "status": "POTENTIAL_NON_COMPLIANCE",
                        "applicable": True,
                        "confidence": 0.90,
                        "evidence_ids": evidence_ids + qty_field.get("ocr_evidence_ids", []),
                        "reason": f"Non-standard unit abbreviation used (found '{raw_unit}', should be '{correct}')"
                    })
                else:
                    traces.append({
                        "rule_id": rule_id,
                        "rule_name": rule["name"],
                        "version": profile.get("version", "2026.1"),
                        "status": "PASS",
                        "applicable": True,
                        "confidence": 0.90,
                        "evidence_ids": evidence_ids + qty_field.get("ocr_evidence_ids", []),
                        "reason": f"Standard unit abbreviation used ('{raw_unit}')"
                    })
                continue
            if rule_id == "LM011":
                exp_field = extracted_fields.get("best_before")
                mfg_field = extracted_fields.get("manufacture_date") or extracted_fields.get("packing_date") or extracted_fields.get("import_date")
                
                if not exp_field or not mfg_field:
                    traces.append({
                        "rule_id": rule_id,
                        "rule_name": rule["name"],
                        "version": profile.get("version", "2026.1"),
                        "status": "NEEDS_REVIEW",
                        "applicable": True,
                        "confidence": 0.5,
                        "evidence_ids": evidence_ids,
                        "reason": "cannot verify — both Expiry and Mfg/Pkd dates are required"
                    })
                    continue

                exp_val = exp_field.get("normalized_value", "")
                mfg_val = mfg_field.get("normalized_value", "")
                
                import re
                from datetime import datetime
                
                def parse_date(d_str):
                    d_str = re.sub(r'[^0-9/.\-]', '', d_str).replace('.', '/').replace('-', '/')
                    parts = [int(p) for p in d_str.split('/') if p]
                    if len(parts) == 2:
                        m, y = parts
                        if y < 100: y += 2000
                        return datetime(y, m, 1)
                    elif len(parts) == 3:
                        d, m, y = parts
                        if y < 100: y += 2000
                        return datetime(y, m, d)
                    return None

                try:
                    exp_date = parse_date(exp_val)
                    mfg_date = parse_date(mfg_val)
                    if exp_date and mfg_date:
                        if exp_date >= mfg_date:
                            traces.append({
                                "rule_id": rule_id,
                                "rule_name": rule["name"],
                                "version": profile.get("version", "2026.1"),
                                "status": "PASS",
                                "applicable": True,
                                "confidence": 0.90,
                                "evidence_ids": evidence_ids,
                                "reason": f"Chronology valid: Expiry ({exp_val}) is after/on Mfg ({mfg_val})"
                            })
                        else:
                            traces.append({
                                "rule_id": rule_id,
                                "rule_name": rule["name"],
                                "version": profile.get("version", "2026.1"),
                                "status": "POTENTIAL_NON_COMPLIANCE",
                                "applicable": True,
                                "confidence": 0.90,
                                "evidence_ids": evidence_ids,
                                "reason": f"Chronology invalid: Expiry ({exp_val}) is before Mfg ({mfg_val})"
                            })
                    else:
                        raise ValueError("Unparseable")
                except Exception:
                    traces.append({
                        "rule_id": rule_id,
                        "rule_name": rule["name"],
                        "version": profile.get("version", "2026.1"),
                        "status": "NEEDS_REVIEW",
                        "applicable": True,
                        "confidence": 0.5,
                        "evidence_ids": evidence_ids,
                        "reason": f"Could not strictly parse dates (Exp: {exp_val}, Mfg: {mfg_val}) to verify chronology."
                    })
                continue

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
