from typing import Dict, Any, List
import numpy as np
from ai.ocr_engine import OCREngine

class OCRService:
    """
    Standardized service for Optical Character Recognition.
    """
    def __init__(self):
        self.ocr_engine = OCREngine()

    def extract(self, image_input: Any) -> Dict[str, Any]:
        """
        Extract OCR tokens.
        """
        tokens = self.ocr_engine.extract_tokens(image_input)
        summary = self.ocr_engine.get_ocr_summary(tokens)
        
        return {
            "status": summary.get("status"),
            "tokens": tokens,
            "token_count": summary.get("token_count"),
            "average_confidence": summary.get("average_confidence"),
            "model_version": self.ocr_engine.model_version
        }
