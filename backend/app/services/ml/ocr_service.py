from typing import Dict, Any, List
import numpy as np
from ai.ocr_engine import OCREngine
from PIL import Image

class OCRService:
    """
    Standardized service for Optical Character Recognition.
    Supports both full-image OCR and regional OCR based on ML detection bounding boxes.
    """
    def __init__(self):
        self.ocr_engine = OCREngine()

    def extract(self, image_input: Any, detections: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract OCR tokens. If detections are provided, runs regional OCR 
        on detected panels and merges them with full image OCR to preserve relationships.
        """
        # Full Image OCR
        all_tokens = self.ocr_engine.extract_tokens(image_input)
        
        # Tag full image tokens
        for t in all_tokens:
            t["source_region"] = "FULL_IMAGE"

        # Image for cropping
        image_np = None
        if isinstance(image_input, np.ndarray):
            image_np = image_input
        elif hasattr(image_input, "convert"):
            image_np = np.array(image_input.convert("RGB"))

        # Regional OCR based on ML Detections
        if detections and image_np is not None:
            # For each detection, crop and run OCR, then offset coordinates back
            for det in detections:
                if "bbox" not in det:
                    continue
                bbox = det["bbox"]
                x1, y1, x2, y2 = bbox.get("x1"), bbox.get("y1"), bbox.get("x2"), bbox.get("y2")
                if None in (x1, y1, x2, y2):
                    continue
                
                # Crop image safely
                h, w = image_np.shape[:2]
                cx1, cy1 = max(0, x1), max(0, y1)
                cx2, cy2 = min(w, x2), min(h, y2)
                
                if cx2 <= cx1 or cy2 <= cy1:
                    continue
                    
                crop_np = image_np[cy1:cy2, cx1:cx2]
                crop_tokens = self.ocr_engine.extract_tokens(crop_np)
                
                # Offset polygons and append
                for ct in crop_tokens:
                    offset_poly = [[pt[0] + cx1, pt[1] + cy1] for pt in ct["polygon"]]
                    ct["polygon"] = offset_poly
                    ct["source_region"] = det.get("class_name", "UNKNOWN_REGION")
                    # Preserve full ML traceability
                    ct["ml_model_name"] = det.get("model_name")
                    ct["ml_model_version"] = det.get("model_version")
                    
                    # We can either replace overlapping tokens or just add them.
                    # Appending enriches the evidence graph.
                    all_tokens.append(ct)

        summary = self.ocr_engine.get_ocr_summary(all_tokens)
        
        return {
            "status": summary.get("status"),
            "tokens": all_tokens,
            "token_count": summary.get("token_count"),
            "average_confidence": summary.get("average_confidence"),
            "model_version": self.ocr_engine.model_version
        }
