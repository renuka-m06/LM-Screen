import numpy as np
from typing import Dict, Any
from ai.barcode_engine import BarcodeEngine

class BarcodeService:
    """
    Standardized service for Barcode Detection.
    """
    def __init__(self):
        self.barcode_engine = BarcodeEngine()

    def detect(self, image_np: np.ndarray) -> Dict[str, Any]:
        """
        Detect barcode.
        Returns format: { "value": str|null, "format": str, "confidence": float, "status": str }
        """
        if image_np is None or image_np.size == 0:
            return {"value": None, "status": "NOT_DETECTED"}
            
        result = self.barcode_engine.decode_and_validate(image_np)
        
        status = result.get("status")
        
        if status in ["VALID_SCALE_REFERENCE", "DECODED_NOT_MEASURABLE"]:
            return {
                "value": result.get("gtin"),
                "format": result.get("symbology", "UNKNOWN"),
                "confidence": 0.99,
                "status": "DETECTED",
                "validation_status": status,
                "raw_metrics": result
            }
        
        return {
            "value": None,
            "status": "NOT_DETECTED",
            "raw_metrics": result
        }
