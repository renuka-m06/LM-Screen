import os
import re
import warnings
import numpy as np
from typing import List, Dict, Any, Optional

warnings.filterwarnings("ignore", category=UserWarning)

class OCREngine:
    """
    Production-grade OCR Engine wrapper for LM-Screen.
    Persists every OCR token with text, polygon, confidence, language, model_version.
    Uses EasyOCR with automatic contrast inversion and multi-pass preprocessing.
    Never returns hardcoded mock tokens for missing detections.
    """
    def __init__(self):
        self.model_version = "EasyOCR-v1.7 / CRAFT"
        self._reader = None

    def _get_reader(self):
        if self._reader is None:
            try:
                import easyocr
                # Weights are stored in ~/.EasyOCR/model/
                self._reader = easyocr.Reader(['en'], gpu=False, download_enabled=False)
            except Exception as e:
                print(f"[OCREngine] Warning: EasyOCR reader initialization failed: {e}")
                self._reader = False
        return self._reader

    def extract_tokens(self, image_input: Any) -> List[Dict[str, Any]]:
        """
        Extract OCR tokens with bounding boxes and confidence scores.
        Applies image preprocessing (e.g. inversion for dark packaging) when appropriate.
        """
        tokens: List[Dict[str, Any]] = []

        # 1. Normalize image to numpy RGB array
        image_np = None
        if isinstance(image_input, np.ndarray):
            image_np = image_input
        elif hasattr(image_input, "convert"):  # PIL Image
            image_np = np.array(image_input.convert("RGB"))
        elif isinstance(image_input, str) and os.path.exists(image_input):
            from PIL import Image
            image_np = np.array(Image.open(image_input).convert("RGB"))

        if image_np is None or image_np.size == 0:
            print("[OCREngine] Error: Invalid or empty image input.")
            return tokens

        reader = self._get_reader()
        if not reader:
            print("[OCREngine] OCR reader unavailable.")
            return tokens

        # 2. Check if packaging has dark background (low average brightness)
        # CRAFT text detector works significantly better on dark text on light background.
        if len(image_np.shape) == 3:
            gray = (0.299 * image_np[:, :, 0] + 0.587 * image_np[:, :, 1] + 0.114 * image_np[:, :, 2]).astype(np.uint8)
        else:
            gray = image_np

        mean_brightness = float(np.mean(gray))
        is_dark_background = mean_brightness < 110.0

        # 3. First pass: run on preferred polarity
        primary_input = (255 - image_np) if is_dark_background else image_np
        try:
            results = reader.readtext(primary_input, paragraph=False)
        except Exception as e:
            print(f"[OCREngine] EasyOCR pass 1 error: {e}")
            results = []

        # 4. Fallback pass: if primary yielded no tokens, try the alternate polarity
        if not results:
            alternate_input = image_np if is_dark_background else (255 - image_np)
            try:
                results = reader.readtext(alternate_input, paragraph=False)
            except Exception as e:
                print(f"[OCREngine] EasyOCR pass 2 error: {e}")
                results = []

        # 5. Convert OCR detections into structured tokens
        for i, (bbox, text, prob) in enumerate(results):
            text_str = str(text).strip()
            if not text_str:
                continue
            polygon = [[int(pt[0]), int(pt[1])] for pt in bbox]
            tokens.append({
                "id": f"tok_{i + 1}",
                "text": text_str,
                "polygon": polygon,
                "confidence": round(float(prob), 3),
                "language": "en",
                "model_version": self.model_version
            })

        print(f"[OCREngine] Extracted {len(tokens)} tokens (dark_background={is_dark_background})")
        return tokens

    def get_ocr_summary(self, tokens: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Returns structured metadata regarding OCR execution quality.
        """
        if not tokens:
            return {
                "status": "NO_TEXT_DETECTED",
                "token_count": 0,
                "average_confidence": 0.0
            }
        avg_conf = sum(t.get("confidence", 0.0) for t in tokens) / len(tokens)
        return {
            "status": "TEXT_DETECTED",
            "token_count": len(tokens),
            "average_confidence": round(avg_conf, 3)
        }
