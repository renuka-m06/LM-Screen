import numpy as np
from typing import Dict, Any
from ai.detection import PackageDetector
from ml.inference.detector import MLPackageDetector

class DetectionService:
    """
    Standardized service for package and panel detection.
    Combines true ML inference with OpenCV heuristics as fallback.
    """
    def __init__(self):
        self.ml_detector = MLPackageDetector()
        self.cv_detector = PackageDetector()

    def detect(self, image_np: np.ndarray) -> Dict[str, Any]:
        """
        Detect panels. Tries ML first, falls back to CV heuristic if ML is not trained.
        """
        if image_np is None or image_np.size == 0:
            return {"detected": False, "detections": [], "status": "FAILED"}
            
        ml_result = self.ml_detector.detect(image_np)
        
        if ml_result.get("status") == "MODEL_NOT_TRAINED":
            # Use CV fallback
            cv_result = self.cv_detector.detect_panel(image_np)
            return {
                "detected": cv_result.get("detected", False),
                "detections": [{
                    "class": "information_panel",
                    "polygon": cv_result.get("polygon"),
                    "confidence": cv_result.get("confidence", 0.0),
                    "crop_box": cv_result.get("crop_box")
                }] if cv_result.get("detected") else [],
                "status": "MODEL_NOT_TRAINED",
                "method": "COMPUTER_VISION_HEURISTIC"
            }
            
        return {
            "detected": len(ml_result.get("detections", [])) > 0,
            "detections": ml_result.get("detections", []),
            "status": "SUCCESS",
            "method": "ML_MODEL"
        }
