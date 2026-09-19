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
        if status in ["VALID_GTIN", "INVALID_CHECKSUM", "NON_GTIN_BARCODE"]:
            return {
                "value": result.get("gtin") or result.get("raw_text"),
                "format": result.get("barcode_type", "UNKNOWN"),
                "confidence": 0.99, # Decoder confidence is generally absolute if decoded
                "status": "DETECTED",
                "validation_status": status,
                "raw_metrics": result
            }
        
        return {
            "value": None,
            "status": "NOT_DETECTED",
            "raw_metrics": result
        }
