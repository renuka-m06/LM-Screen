import numpy as np
from typing import Dict, Any
from ai.detection import PackageDetector
from ml.inference.detector import MLPackageDetector
from backend.app.services.ml.registry import ModelStatus

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
        
        if ml_result.get("status") in [ModelStatus.MODEL_NOT_FOUND, ModelStatus.MODEL_LOAD_ERROR]:
            # Use CV fallback
            cv_result = self.cv_detector.detect_panel(image_np)
            detections = []
            if cv_result.get("detected"):
                crop_box = cv_result.get("crop_box", [0, 0, 0, 0])
                # Format: x, y, w, h -> x1, y1, x2, y2
                detections.append({
                    "class_name": "information_panel",
                    "bbox": {
                        "x1": crop_box[0],
                        "y1": crop_box[1],
                        "x2": crop_box[0] + crop_box[2],
                        "y2": crop_box[1] + crop_box[3]
                    },
                    "confidence": "UNKNOWN", # Heuristics don't have true statistical confidence
                    "model_name": "opencv-heuristic",
                    "model_version": "v1",
                    "source": "HEURISTIC"
                })
                
            return {
                "detected": len(detections) > 0,
                "detections": detections,
                "status": ml_result.get("status"),
                "method": "COMPUTER_VISION_HEURISTIC"
            }
            
        # Ensure we attach source="YOLO" to ML detections
        detections = ml_result.get("detections", [])
        for d in detections:
            d["source"] = "YOLO"
            
        return {
            "detected": len(detections) > 0,
            "detections": detections,
            "status": "SUCCESS",
            "method": "ML_MODEL"
        }
