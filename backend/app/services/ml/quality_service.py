import numpy as np
from typing import Dict, Any
from ai.quality import ImageQualityGate

class QualityService:
    """
    Standardized service for image quality assessment.
    """
    def __init__(self):
        self.quality_gate = ImageQualityGate()

    def assess(self, image_np: np.ndarray) -> Dict[str, Any]:
        """
        Assess image quality.
        Returns: { usable: bool, quality_score: float, issues: list[str] }
        """
        raw_result = self.quality_gate.assess_quality(image_np)
        
        # Standardize output
        usable = raw_result.get("status") in ["ACCEPTABLE", "PARTIALLY_USABLE"]
        
        # Normalize score (0-1) - arbitrary weighting for heuristic fallback
        blur = raw_result.get("blur_score", 0.0)
        score = min(blur / (self.quality_gate.blur_threshold * 2), 1.0)
        
        return {
            "usable": usable,
            "quality_score": round(score, 2),
            "issues": raw_result.get("reasons", []),
            "raw_metrics": raw_result  # Keep raw data for trace
        }
        
    def refine_with_ocr(self, quality_result: Dict[str, Any], ocr_tokens: list) -> Dict[str, Any]:
        # Updates the raw metrics if OCR found text, then re-standardize
        if "raw_metrics" not in quality_result:
            return quality_result
            
        upgraded_raw = self.quality_gate.upgrade_with_ocr(quality_result["raw_metrics"], ocr_tokens)
        
        usable = upgraded_raw.get("status") in ["ACCEPTABLE", "PARTIALLY_USABLE"]
        return {
            "usable": usable,
            "quality_score": quality_result["quality_score"],
            "issues": upgraded_raw.get("reasons", []),
            "raw_metrics": upgraded_raw
        }
