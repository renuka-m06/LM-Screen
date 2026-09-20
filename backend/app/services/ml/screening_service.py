import time
import numpy as np
from typing import Dict, Any, List

from .quality_service import QualityService
from .detection_service import DetectionService
from .ocr_service import OCRService
from .barcode_service import BarcodeService
from .classification_service import ClassificationService
from .evidence_service import EvidenceService

from rules.engine import DeterministicRuleEngine
from rules.verdict import VerdictAggregator

class ScreeningService:
    """
    High-level orchestrator for the LM-Screen ML/CV pipeline.
    """
    def __init__(self):
        self.quality = QualityService()
        self.detection = DetectionService()
        self.ocr = OCRService()
        self.barcode = BarcodeService()
        self.classification = ClassificationService()
        self.evidence = EvidenceService()
        
        self.rule_engine = DeterministicRuleEngine()
        self.verdict_aggregator = VerdictAggregator()

    def process_image(self, image_np: np.ndarray, user_hints: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Run the full evidence-first screening pipeline.
        """
        start_time = time.time()
        trace = []
        user_hints = user_hints or {}

        # 1. Quality
        q_result = self.quality.assess(image_np)
        trace.append({"stage": "IMAGE_QUALITY", "status": "OK" if q_result["usable"] else "RETAKE_REQUIRED", "detail": f"Score: {q_result['quality_score']}"})

        # 2. Detection
        det_result = self.detection.detect(image_np)
        trace.append({"stage": "PANEL_DETECTION", "status": det_result["status"], "detail": f"Method: {det_result['method']}"})

        # 3. OCR
        ocr_result = self.ocr.extract(image_np)
        trace.append({"stage": "OCR", "status": ocr_result["status"], "detail": f"Tokens: {ocr_result['token_count']}"})
        
        # OCR Quality Refinement
        q_result = self.quality.refine_with_ocr(q_result, ocr_result["tokens"])

        # 4. Barcode
        barcode_result = self.barcode.detect(image_np)
        trace.append({"stage": "BARCODE", "status": barcode_result["status"], "detail": f"Format: {barcode_result.get('format', 'N/A')}"})

        # 5. Evidence Extraction
        # Get scale if available from barcode
        scale = barcode_result.get("raw_metrics", {}).get("scale_mm_per_pixel")
        evidence_list = self.evidence.extract(ocr_result["tokens"], scale_mm_per_pixel=scale)
        trace.append({"stage": "EVIDENCE_EXTRACTION", "status": "OK", "detail": f"Extracted {len(evidence_list)} fields"})

        # 6. Classification
        class_result = self.classification.classify(ocr_result["tokens"], image_np=image_np)
        trace.append({"stage": "PRODUCT_CLASSIFICATION", "status": class_result["status"], "detail": f"Category: {class_result['category']}"})

        # 7. Rule Engine Evaluation
        # Convert evidence_list back to dict format temporarily if rules.engine hasn't been updated, 
        # or pass directly if rules.engine expects list. We assume it expects dict until we update it.
        # But wait, we are updating rules.engine.py to accept list.
        # So we pass evidence_list directly!
        context = {
            "product_category": class_result["category"],
            "scale_mm_per_pixel": scale,
        }
        if det_result["detected"] and det_result["detections"]:
            context["pdp_crop_box"] = det_result["detections"][0].get("crop_box")

        # Let's pass the raw dict to rules engine for now, wait we will update rules engine next.
        # The prompt says: Connect structured evidence to the EXISTING LM-Screen rule system.
        # Let's assume rules engine evaluate takes evidence_list.
        
        # Build extracted_fields dict for the rule engine.
        # Must include numeric_value, unit, raw_unit, evidence_state, and
        # ocr_evidence_ids — the engine reads all of these for LM007-LM009.
        # evidence_service now forwards all of these; map by field name.
        extracted_fields_legacy = {
            e["field"]: {
                "normalized_value":  e["value"],
                "confidence":        e["confidence"],
                "evidence_state":    e.get("evidence_state", "PRESENT"),
                "numeric_value":     e.get("numeric_value"),
                "unit":              e.get("unit"),
                "raw_unit":          e.get("raw_unit"),
                "font_height_mm":    e.get("font_height_mm"),
                "ocr_evidence_ids":  e.get("ocr_evidence_ids", []),
            }
            for e in evidence_list if e["found"]
        }
        
        rule_traces = self.rule_engine.evaluate(extracted_fields_legacy, context, q_result.get("raw_metrics", {}))
        trace.append({"stage": "RULE_EVALUATION", "status": "OK", "detail": f"Evaluated {len(rule_traces)} rules"})

        # 8. Verdict Aggregation
        verdict = self.verdict_aggregator.aggregate(rule_traces, q_result.get("raw_metrics", {}), barcode_result.get("raw_metrics", {}), context, [])
        trace.append({"stage": "VERDICT", "status": verdict.get("status"), "detail": f"Confidence: {verdict.get('screening_confidence')}"})

        duration_ms = (time.time() - start_time) * 1000
        
        return {
            "image_quality": q_result,
            "detections": det_result["detections"],
            "ocr": ocr_result["tokens"],
            "barcode": barcode_result,
            "product_context": class_result,
            "evidence": evidence_list,
            "rule_results": rule_traces,
            "verdict": verdict,
            "decision_trace": trace,
            "processing_time_ms": duration_ms
        }
