import os
import numpy as np
from typing import Dict, Any, List
from backend.app.services.ml.registry import ModelRegistry, ModelStatus

class MLPackageDetector:
    """
    ML Interface for YOLO-based Package and Panel Detection.
    Falls back to MODEL_NOT_FOUND state if weights are not available.
    Supports classes defined in ModelRegistry.
    """
    def __init__(self, model_name: str = "yolov8-panel-detector"):
        self.model_name = model_name
        self.model = None
        
        self.config = ModelRegistry.get_model(model_name)
        if not self.config:
            raise ValueError(f"Model {model_name} not found in registry.")
            
        self.is_trained = self.config["status"] == ModelStatus.MODEL_READY
        
        if self.is_trained:
            self._load_model()

    def _load_model(self):
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.config["file_path"])
        except Exception as e:
            print(f"Failed to load detector model: {e}")
            self.is_trained = False
            self.config["status"] = ModelStatus.MODEL_LOAD_ERROR

    def _validate_bbox(self, xyxy: List[float], img_shape: tuple) -> bool:
        """
        Validates bounding box coordinates.
        Checks numeric constraints, width > 0, height > 0, and image boundaries.
        """
        try:
            x1, y1, x2, y2 = xyxy
            if not all(isinstance(v, (int, float)) for v in xyxy):
                return False
                
            # Width and height must be positive
            if x2 <= x1 or y2 <= y1:
                return False
                
            # Must intersect with image bounds (or we could strictly require them to be completely inside)
            # For robustness, we allow them to be slightly outside, but we clip them during extraction.
            # But the prompt says "coordinates remain inside image bounds".
            h, w = img_shape[:2]
            if x1 < 0 or y1 < 0 or x2 > w or y2 > h:
                # We can either reject or clip. The prompt says "Invalid model outputs should be rejected or marked invalid."
                # We will reject out-of-bounds boxes to strictly follow the prompt.
                return False
                
            return True
        except Exception:
            return False

    def detect(self, image_np: np.ndarray) -> Dict[str, Any]:
        """
        Detect panels in the image.
        Returns explicit state about model readiness. Never fakes detections.
        """
        if not self.is_trained:
            return {
                "status": self.config["status"],
                "model_name": self.config["model_name"],
                "model_version": self.config["model_version"],
                "detections": [],
                "message": "Weights not found or failed to load. Please train the model."
            }

        # Actual inference logic
        try:
            results = self.model(image_np)
            detections = []
            img_shape = image_np.shape
            
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    xyxy = box.xyxy[0].cpu().numpy().tolist()
                    
                    if not self._validate_bbox(xyxy, img_shape):
                        continue # Reject invalid bboxes
                        
                    if cls_id < len(self.config["classes"]):
                        # Normalized structure
                        detections.append({
                            "class_name": self.config["classes"][cls_id],
                            "bbox": {
                                "x1": int(xyxy[0]),
                                "y1": int(xyxy[1]),
                                "x2": int(xyxy[2]),
                                "y2": int(xyxy[3])
                            },
                            "confidence": round(conf, 3),
                            "model_name": self.config["model_name"],
                            "model_version": self.config["model_version"]
                        })
            
            return {
                "status": "SUCCESS",
                "model_name": self.config["model_name"],
                "model_version": self.config["model_version"],
                "detections": detections
            }
        except Exception as e:
            print(f"Inference error: {e}")
            return {
                "status": "ERROR",
                "model_name": self.config["model_name"],
                "model_version": self.config["model_version"],
                "detections": [],
                "message": f"Inference failed: {e}"
            }
