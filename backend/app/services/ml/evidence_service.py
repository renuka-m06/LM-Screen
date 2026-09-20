from typing import Dict, Any, List
from ai.field_extractor import FieldExtractor

class EvidenceService:
    """
    Standardized service for Evidence Extraction.
    Transforms raw extractions into the standard evidence schema.
    """
    def __init__(self):
        self.extractor = FieldExtractor()

    def extract(self, ocr_tokens: List[Dict[str, Any]], scale_mm_per_pixel: float = None) -> List[Dict[str, Any]]:
        """
        Extract structured fields and return as standard evidence list.
        """
        raw_fields = self.extractor.extract_fields(ocr_tokens, scale_mm_per_pixel=scale_mm_per_pixel)
        
        evidence_list = []
        for field_name, f_val in raw_fields.items():
            evidence = {
                # Human-readable display value — preserved for UI and DB.
                "field": f_val.get("field_name", field_name),
                "value": f_val.get("normalized_value"),
                "found": f_val.get("evidence_state", "PRESENT") != "ABSENT_FROM_EVIDENCE",
                "confidence": f_val.get("confidence", 0.0),
                "source": {
                    "type": "OCR",
                    "panel": "declaration_label",
                    "bbox": [],
                    "raw_text": f_val.get("raw_value")
                },
                "method": f_val.get("extraction_method", "REGEX"),

                # ── Fields required by the rule engine ────────────────────────
                # evidence_state: LM008 checks for "UNCERTAIN" before arithmetic.
                "evidence_state": f_val.get("evidence_state", "PRESENT"),
                # numeric_value: LM008 reads this for MRP, net_quantity, USP.
                "numeric_value": f_val.get("numeric_value"),
                # unit: LM008 uses this for base-unit normalisation.
                "unit": f_val.get("unit"),
                # raw_unit: LM009 reads this to check for non-standard abbreviations.
                "raw_unit": f_val.get("raw_unit"),
                # font_height_mm: LM007 reads this when scale is available.
                "font_height_mm": f_val.get("font_height_mm"),
                # ocr_evidence_ids: engine appends these to audit traces.
                "ocr_evidence_ids": f_val.get("ocr_evidence_ids", []),
            }
            evidence_list.append(evidence)
            
        return evidence_list
