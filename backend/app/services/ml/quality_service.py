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
        Returns standardized state: HIGH_QUALITY, READABLE, REVIEW_QUALITY, UNUSABLE.
        """
        raw_result = self.quality_gate.assess_quality(image_np)
        
        # Standardize output
        usable = raw_result.get("usable", raw_result.get("state") != "UNUSABLE")
        
        # Normalize score (0-1)
        blur = raw_result.get("blur_score", 0.0)
        score = min(blur / (self.quality_gate.blur_threshold * 2), 1.0)
        
        return {
            "usable": usable,
            "state": raw_result.get("state", "READABLE"),
            "status": raw_result.get("status", "ACCEPTABLE"),
            "quality_label": raw_result.get("quality_label", "Readable"),
            "quality_score": round(score, 2),
            "issues": raw_result.get("reasons", []),
            "blur_score": raw_result.get("blur_score", 0.0),
            "brightness_score": raw_result.get("brightness_score", 0.0),
            "contrast_score": raw_result.get("contrast_score", 0.0),
            "glare_ratio": raw_result.get("glare_ratio", 0.0),
            "width": raw_result.get("width"),
            "height": raw_result.get("height"),
            "raw_metrics": raw_result
        }
        
    def refine_with_ocr(self, quality_result: Dict[str, Any], ocr_tokens: list) -> Dict[str, Any]:
        if "raw_metrics" not in quality_result:
            return quality_result
            
        upgraded_raw = self.quality_gate.upgrade_with_ocr(quality_result["raw_metrics"], ocr_tokens)
        usable = upgraded_raw.get("usable", upgraded_raw.get("state") != "UNUSABLE")
        
        return {
            "usable": usable,
            "state": upgraded_raw.get("state", "READABLE"),
            "status": upgraded_raw.get("status", "ACCEPTABLE"),
            "quality_label": upgraded_raw.get("quality_label", "Readable"),
            "quality_score": quality_result.get("quality_score", 1.0),
            "issues": upgraded_raw.get("reasons", []),
            "blur_score": upgraded_raw.get("blur_score", 0.0),
            "brightness_score": upgraded_raw.get("brightness_score", 0.0),
            "contrast_score": upgraded_raw.get("contrast_score", 0.0),
            "glare_ratio": upgraded_raw.get("glare_ratio", 0.0),
            "width": upgraded_raw.get("width"),
            "height": upgraded_raw.get("height"),
            "raw_metrics": upgraded_raw
        }
