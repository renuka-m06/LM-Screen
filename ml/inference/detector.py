import os
import numpy as np
from typing import Dict, Any, List

class MLPackageDetector:
    """
    ML Interface for YOLO-based Package and Panel Detection.
    Falls back to MODEL_NOT_TRAINED state if weights are not available.
    Supports classes: package, front_panel, back_panel, nutrition_panel, ingredients_panel, barcode, declaration_label, warning_area
    """
    def __init__(self, weights_path: str = "models/detector.pt"):
        self.weights_path = weights_path
        self.is_trained = os.path.exists(weights_path)
        self.model = None
        self.model_version = "yolov8-panel-detector-v1"
        self.classes = [
            "package", "front_panel", "back_panel", "nutrition_panel", 
            "ingredients_panel", "barcode", "declaration_label", "warning_area"
        ]
        
        if self.is_trained:
            self._load_model()

    def _load_model(self):
        try:
            from ultralytics import YOLO
            self.model = YOLO(self.weights_path)
        except Exception as e:
            print(f"Failed to load detector model: {e}")
            self.is_trained = False

    def detect(self, image_np: np.ndarray) -> Dict[str, Any]:
        """
        Detect panels in the image.
        Returns explicit state about model readiness. Never fakes detections.
        """
        if not self.is_trained:
            return {
                "status": "MODEL_NOT_TRAINED",
                "model_version": self.model_version,
                "detections": [],
                "message": "Weights not found. Please train the model."
            }

        # Actual inference logic
        try:
            results = self.model(image_np)
            detections = []
            
            for result in results:
                boxes = result.boxes
                for box in boxes:
                    cls_id = int(box.cls[0])
                    conf = float(box.conf[0])
                    xyxy = box.xyxy[0].cpu().numpy().tolist()
                    
                    if cls_id < len(self.classes):
                        detections.append({
                            "class": self.classes[cls_id],
                            "confidence": round(conf, 3),
                            "crop_box": [int(xyxy[0]), int(xyxy[1]), int(xyxy[2] - xyxy[0]), int(xyxy[3] - xyxy[1])],
                            "polygon": [[int(xyxy[0]), int(xyxy[1])], [int(xyxy[2]), int(xyxy[1])], [int(xyxy[2]), int(xyxy[3])], [int(xyxy[0]), int(xyxy[3])]]
                        })
            
            return {
                "status": "SUCCESS",
                "model_version": self.model_version,
                "detections": detections
            }
        except Exception as e:
            print(f"Inference error: {e}")
            return {
                "status": "ERROR",
                "model_version": self.model_version,
                "detections": [],
                "message": f"Inference failed: {e}"
            }
