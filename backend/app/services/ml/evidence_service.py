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
                "field": f_val.get("field_name", field_name),
                "value": f_val.get("normalized_value"),
                "found": f_val.get("evidence_state", "PRESENT") != "ABSENT_FROM_EVIDENCE",
                "confidence": f_val.get("confidence", 0.0),
                "source": {
                    "type": "OCR",
                    "panel": "declaration_label",
                    "bbox": [], # Can be enhanced by tracking token bboxes
                    "raw_text": f_val.get("raw_value")
                },
                "method": f_val.get("extraction_method", "REGEX")
            }
            evidence_list.append(evidence)
            
        return evidence_list
