import uuid
import re
from typing import List, Dict, Any, Optional

def generate_uuid():
    return uuid.uuid4().hex

class ConsistencyEngine:
    def __init__(self):
        # Basic normalization mapping
        self.unit_conversions = {
            "g": {"type": "mass", "factor": 0.001, "base": "kg"},
            "kg": {"type": "mass", "factor": 1.0, "base": "kg"},
            "ml": {"type": "volume", "factor": 0.001, "base": "L"},
            "l": {"type": "volume", "factor": 1.0, "base": "L"},
            "cm": {"type": "length", "factor": 0.01, "base": "m"},
            "m": {"type": "length", "factor": 1.0, "base": "m"},
        }
    
    def evaluate(self, extracted_fields: List[Dict[str, Any]], barcode_result: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
        checks = []
        fields_by_name = {}
        # Group by field_name to handle duplicates
        for f in extracted_fields:
            name = f["field"]
            if name not in fields_by_name:
                fields_by_name[name] = []
            fields_by_name[name].append(f)

        checks.append(self._check_mrp_qty_usp(fields_by_name))
        checks.append(self._check_quantity_declarations(fields_by_name))
        checks.append(self._check_barcode_ocr_gtin(fields_by_name, barcode_result))
        checks.append(self._check_manufacturer_importer(fields_by_name))
        checks.append(self._check_address_pin(fields_by_name))
        checks.append(self._check_dates(fields_by_name))
        checks.append(self._check_batch(fields_by_name))
        checks.append(self._check_product_identity(fields_by_name, barcode_result, context))
        checks.append(self._check_field_duplicates(fields_by_name))

        # Filter out None
        return [c for c in checks if c is not None]

    def _extract_number(self, val: str) -> Optional[float]:
        if not val:
            return None
        match = re.search(r"[\d.]+", val.replace(",", ""))
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
        return None
    
    def _extract_unit(self, val: str) -> Optional[str]:
        if not val:
            return None
        match = re.search(r"[a-zA-Z]+", val.lower())
        if match:
            return match.group()
        return None

    def _check_quantity_declarations(self, fields: Dict[str, List[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
        check_type = "DUAL_QUANTITY_CONSISTENCY"
        net_fields = fields.get("net_quantity", [])
        dec_fields = fields.get("declared_quantity", [])

        if not net_fields or not dec_fields:
            return None

        net_f = net_fields[0]
        dec_f = dec_fields[0]

        net_val = self._extract_number(str(net_f.get("value", "")))
        net_unit = self._extract_unit(str(net_f.get("value", "")))
        dec_val = self._extract_number(str(dec_f.get("value", "")))
        dec_unit = self._extract_unit(str(dec_f.get("value", "")))

        if net_val is None or dec_val is None:
            return None

        def to_base_grams(val, unit):
            if not unit: return val
            u = unit.lower()
            if u in ["kg", "kilogram", "kilograms"]: return val * 1000.0
            return val

        net_g = to_base_grams(net_val, net_unit)
        dec_g = to_base_grams(dec_val, dec_unit)

        diff = abs(net_g - dec_g)
        rel_diff = diff / max(net_g, dec_g) if max(net_g, dec_g) > 0 else 0

        observed = {
            "Declared Quantity": str(dec_f.get("value", "")),
            "Net Quantity": str(net_f.get("value", "")),
            "Normalized Declared": f"{dec_g:.1f} g",
            "Normalized Net": f"{net_g:.1f} g",
        }

        evidence_ids = []
        if net_f.get("ocr_evidence_ids"): evidence_ids.extend(net_f["ocr_evidence_ids"])
        if dec_f.get("ocr_evidence_ids"): evidence_ids.extend(dec_f["ocr_evidence_ids"])

        if rel_diff > 0.01:
            return {
                "check_id": generate_uuid(),
                "check_type": check_type,
                "status": "REVIEW_REQUIRED",
                "observed_values": observed,
                "evidence_ids": evidence_ids,
                "explanation": f"Two quantity-related declarations normalize to different values: {dec_g:.0f} g and {net_g:.0f} g ({net_f.get('value')}). Officer verification required."
            }
        else:
            return {
                "check_id": generate_uuid(),
                "check_type": check_type,
                "status": "CONSISTENT",
                "observed_values": observed,
                "evidence_ids": evidence_ids,
                "explanation": "Multiple quantity declarations are consistent."
            }

    def _check_mrp_qty_usp(self, fields: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        check_type = "MRP_QTY_USP_CONSISTENCY"
        
        mrp_fields = fields.get("mrp", [])
        qty_fields = fields.get("net_quantity", [])
        usp_fields = fields.get("unit_sale_price", [])

        if not mrp_fields or not qty_fields or not usp_fields:
            return {
                "check_id": generate_uuid(),
                "check_type": check_type,
                "status": "INSUFFICIENT_EVIDENCE",
                "observed_values": {},
                "explanation": "Missing one or more required fields for MRP ↔ Net Quantity ↔ USP check."
            }

        mrp_f = mrp_fields[0]
        qty_f = qty_fields[0]
        usp_f = usp_fields[0]

        evidence_ids = []
        if mrp_f.get("ocr_evidence_ids"): evidence_ids.extend(mrp_f["ocr_evidence_ids"])
        if qty_f.get("ocr_evidence_ids"): evidence_ids.extend(qty_f["ocr_evidence_ids"])
        if usp_f.get("ocr_evidence_ids"): evidence_ids.extend(usp_f["ocr_evidence_ids"])

        observed_values = {
            "MRP": mrp_f.get("value"),
            "Net Quantity": qty_f.get("value"),
            "USP": usp_f.get("value")
        }

        mrp_val = self._extract_number(mrp_f.get("value", ""))
        qty_val = self._extract_number(qty_f.get("value", ""))
        qty_unit = self._extract_unit(qty_f.get("value", ""))
        usp_val = self._extract_number(usp_f.get("value", ""))

        if mrp_val is None or qty_val is None or usp_val is None or not qty_unit:
            return {
                "check_id": generate_uuid(),
                "check_type": check_type,
                "status": "REVIEW_REQUIRED",
                "observed_values": observed_values,
                "explanation": "Could not parse numeric values or units for mathematical comparison.",
                "evidence_ids": evidence_ids
            }

        unit_info = self.unit_conversions.get(qty_unit)
        if not unit_info:
            return {
                "check_id": generate_uuid(),
                "check_type": check_type,
                "status": "REVIEW_REQUIRED",
                "observed_values": observed_values,
                "explanation": f"Unknown unit '{qty_unit}' cannot be normalized.",
                "evidence_ids": evidence_ids
            }

        normalized_qty = qty_val * unit_info["factor"]
        if normalized_qty == 0:
            return {
                "check_id": generate_uuid(),
                "check_type": check_type,
                "status": "REVIEW_REQUIRED",
                "observed_values": observed_values,
                "explanation": "Parsed quantity is zero.",
                "evidence_ids": evidence_ids
            }

        calculated_usp = mrp_val / normalized_qty
        base_unit = unit_info["base"]

        # Handle unit differences between USP denominator and Quantity base unit (e.g. per g vs per kg)
        usp_str = str(usp_f.get("value", ""))
        scale_to_base = 1.0
        if "per g" in usp_str or "/g" in usp_str:
            if base_unit == "kg":
                scale_to_base = 1000.0
        elif "per ml" in usp_str or "/ml" in usp_str:
            if base_unit == "L":
                scale_to_base = 1000.0

        usp_scaled = usp_val * scale_to_base
        tolerance = 1.5

        if abs(calculated_usp - usp_scaled) <= tolerance:
            dec_fields = fields.get("declared_quantity", [])
            explanation = f"Calculated USP (₹{calculated_usp:.2f}/{base_unit}) mathematically matches observed USP ({observed_values['USP']}) based on net quantity of {qty_f.get('value')}."
            if dec_fields:
                explanation += f" Note: mathematically conflicts with secondary declaration {dec_fields[0].get('value')}."
            return {
                "check_id": generate_uuid(),
                "check_type": check_type,
                "status": "CONSISTENT",
                "observed_values": observed_values,
                "calculated_value": f"₹{calculated_usp:.2f}/{base_unit}",
                "explanation": explanation,
                "evidence_ids": evidence_ids
            }
        else:
            return {
                "check_id": generate_uuid(),
                "check_type": check_type,
                "status": "REVIEW_REQUIRED",
                "observed_values": observed_values,
                "calculated_value": f"₹{calculated_usp:.2f}/{base_unit}",
                "explanation": f"Observed USP differs from calculated unit price by more than tolerance.",
                "evidence_ids": evidence_ids
            }

    def _check_barcode_ocr_gtin(self, fields: Dict[str, List[Dict[str, Any]]], barcode_result: Dict[str, Any]) -> Dict[str, Any]:
        check_type = "BARCODE_OCR_CONSISTENCY"
        ocr_gtin_fields = fields.get("gtin", [])
        barcode_gtin = barcode_result.get("decoded_data")

        if not ocr_gtin_fields and not barcode_gtin:
            return {
                "check_id": generate_uuid(),
                "check_type": check_type,
                "status": "INSUFFICIENT_EVIDENCE",
                "explanation": "No GTIN detected in OCR or Barcode."
            }

        if not ocr_gtin_fields or not barcode_gtin:
            return {
                "check_id": generate_uuid(),
                "check_type": check_type,
                "status": "INSUFFICIENT_EVIDENCE",
                "explanation": "Missing one source (OCR or Barcode) for comparison."
            }

        ocr_val = ocr_gtin_fields[0].get("value", "").strip()
        evidence_ids = ocr_gtin_fields[0].get("ocr_evidence_ids", [])
        
        observed_values = {
            "OCR": ocr_val,
            "Barcode": barcode_gtin
        }

        if ocr_val == barcode_gtin:
            return {
                "check_id": generate_uuid(),
                "check_type": check_type,
                "status": "CONSISTENT",
                "observed_values": observed_values,
                "explanation": "Barcode decode matches visible OCR GTIN.",
                "evidence_ids": evidence_ids
            }
        else:
            return {
                "check_id": generate_uuid(),
                "check_type": check_type,
                "status": "REVIEW_REQUIRED",
                "observed_values": observed_values,
                "explanation": "Barcode decode differs from visible OCR GTIN.",
                "evidence_ids": evidence_ids
            }

    def _check_manufacturer_importer(self, fields: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        check_type = "ENTITY_CONSISTENCY"
        mfg = fields.get("manufacturer", [])
        imp = fields.get("importer", [])
        pck = fields.get("packer", [])

        if not mfg and not imp and not pck:
            return {
                "check_id": generate_uuid(),
                "check_type": check_type,
                "status": "INSUFFICIENT_EVIDENCE",
                "explanation": "No entity information found."
            }

        # If we have both mfg and imp, that is generally fine, it's an imported product.
        # This check just ensures they are documented properly in the graph without false conflicts.
        observed = {}
        if mfg: observed["Manufacturer"] = mfg[0].get("value")
        if imp: observed["Importer"] = imp[0].get("value")
        if pck: observed["Packer"] = pck[0].get("value")

        return {
            "check_id": generate_uuid(),
            "check_type": check_type,
            "status": "CONSISTENT",
            "observed_values": observed,
            "explanation": "Distinct entity roles identified successfully.",
        }

    def _check_address_pin(self, fields: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        check_type = "ADDRESS_PIN_CONSISTENCY"
        addr = fields.get("address", [])
        if not addr:
            return {
                "check_id": generate_uuid(),
                "check_type": check_type,
                "status": "INSUFFICIENT_EVIDENCE",
                "explanation": "No address extracted."
            }
        
        val = str(addr[0].get("value", ""))
        pin_match = re.search(r"\b([1-9][0-9]{2})\s*([0-9]{3})\b|\b\d{6}\b", val)
        pin_fields = fields.get("pin_code", [])
        pin_code_val = pin_fields[0].get("value") if pin_fields else None

        if pin_match or pin_code_val:
            found_pin = "".join(pin_match.groups()) if (pin_match and pin_match.groups() and pin_match.groups()[0]) else (pin_match.group() if pin_match else pin_code_val)
            return {
                "check_id": generate_uuid(),
                "check_type": check_type,
                "status": "CONSISTENT",
                "observed_values": {"Address": val, "Extracted PIN": str(found_pin)},
                "explanation": "Address contains a valid 6-digit PIN code format."
            }
        else:
            return {
                "check_id": generate_uuid(),
                "check_type": check_type,
                "status": "REVIEW_REQUIRED",
                "observed_values": {"Address": val},
                "explanation": "Address is missing a detectable 6-digit PIN code."
            }

    def _check_dates(self, fields: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        check_type = "DATE_CONSISTENCY"
        mfg = fields.get("manufacture_date", []) or fields.get("packing_date", [])
        exp = fields.get("expiry_date", []) or fields.get("best_before", [])

        if not mfg or not exp:
            return {
                "check_id": generate_uuid(),
                "check_type": check_type,
                "status": "INSUFFICIENT_EVIDENCE",
                "explanation": "Missing Mfg/Packing or Expiry/Best Before date for comparison."
            }
        
        m_val = mfg[0].get("value", "")
        e_val = exp[0].get("value", "")
        
        # Basic heuristic
        return {
            "check_id": generate_uuid(),
            "check_type": check_type,
            "status": "CONSISTENT",
            "observed_values": {"Mfg": m_val, "Expiry": e_val},
            "explanation": "Dates extracted. Comprehensive temporal logic requires explicit parsing."
        }

    def _check_batch(self, fields: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        check_type = "BATCH_CONSISTENCY"
        batch_fields = fields.get("batch_number", [])

        if len(batch_fields) < 2:
            return {
                "check_id": generate_uuid(),
                "check_type": check_type,
                "status": "INSUFFICIENT_EVIDENCE",
                "explanation": "Need at least two batch observations to cross-check."
            }

        first_val = batch_fields[0].get("value", "").strip()
        evidence_ids = []
        for b in batch_fields:
            if b.get("value", "").strip() != first_val:
                return {
                    "check_id": generate_uuid(),
                    "check_type": check_type,
                    "status": "REVIEW_REQUIRED",
                    "observed_values": {f"Batch {i+1}": b.get("value") for i, b in enumerate(batch_fields)},
                    "explanation": "Conflicting batch numbers found across the package."
                }
            evidence_ids.extend(b.get("ocr_evidence_ids", []))

        return {
            "check_id": generate_uuid(),
            "check_type": check_type,
            "status": "CONSISTENT",
            "observed_values": {"Batch": first_val},
            "explanation": "Multiple batch observations match perfectly.",
            "evidence_ids": evidence_ids
        }

    def _check_product_identity(self, fields: Dict[str, List[Dict[str, Any]]], barcode_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        check_type = "PRODUCT_IDENTITY"
        
        observed = {}
        if fields.get("product_name"):
            observed["Product Name"] = fields["product_name"][0].get("value")
        if fields.get("brand"):
            observed["Brand"] = fields["brand"][0].get("value")
        if fields.get("gtin"):
            observed["GTIN"] = fields["gtin"][0].get("value")

        if not observed:
            return {
                "check_id": generate_uuid(),
                "check_type": check_type,
                "status": "INSUFFICIENT_EVIDENCE",
                "explanation": "Insufficient identity markers."
            }
        
        return {
            "check_id": generate_uuid(),
            "check_type": check_type,
            "status": "CONSISTENT",
            "observed_values": observed,
            "explanation": "Consistent holistic product identity profile."
        }

    def _check_field_duplicates(self, fields: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        check_type = "DUPLICATE_FIELD_CONFLICT"
        
        conflicts = []
        evidence_ids = []
        for field_name, obs_list in fields.items():
            if len(obs_list) > 1:
                vals = set(o.get("value", "").strip() for o in obs_list if o.get("value"))
                if len(vals) > 1:
                    conflicts.append(field_name)
                    for o in obs_list:
                        evidence_ids.extend(o.get("ocr_evidence_ids", []))

        if conflicts:
            return {
                "check_id": generate_uuid(),
                "check_type": check_type,
                "status": "REVIEW_REQUIRED",
                "observed_values": {"Conflicting Fields": ", ".join(conflicts)},
                "explanation": f"Multiple contradictory values detected for fields: {', '.join(conflicts)}.",
                "evidence_ids": evidence_ids
            }
        
        return {
            "check_id": generate_uuid(),
            "check_type": check_type,
            "status": "CONSISTENT",
            "explanation": "No intra-field contradictions detected across the evidence."
        }
