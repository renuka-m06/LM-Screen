import os
import cv2
import re
import warnings
import threading
import numpy as np
from typing import List, Dict, Any, Optional

warnings.filterwarnings("ignore", category=UserWarning)

# Maximum image dimension fed to EasyOCR.
# Larger images give ~linear runtime increase on CPU; 1200px is a good balance for package labels.
OCR_MAX_DIM = 1200
# EasyOCR canvas_size: reduce from default 2560 → 1280 for CPU performance
OCR_CANVAS_SIZE = 1280
# EasyOCR batch_size: 4 is safe for CPU, raises throughput vs default 1
OCR_BATCH_SIZE = 4

# ── Eager background pre-warm ───────────────────────────────────────────────
# EasyOCR CPU model load takes 60-120 s on first use. Pre-loading in a daemon
# thread at import time means the reader is ready before the first HTTP request.
_reader_ready = threading.Event()
_prewarmed_reader = None
_prewarm_error: Optional[str] = None

def _prewarm_reader():
    global _prewarmed_reader, _prewarm_error
    try:
        import easyocr
        print("[OCREngine] Pre-warming EasyOCR reader (CPU) …")
        _prewarmed_reader = easyocr.Reader(['en'], gpu=False, download_enabled=False)
        print("[OCREngine] EasyOCR reader ready.")
    except Exception as exc:
        _prewarm_error = str(exc)
        print(f"[OCREngine] Pre-warm failed: {exc}")
    finally:
        _reader_ready.set()

_prewarm_thread = threading.Thread(target=_prewarm_reader, daemon=True, name="ocr-prewarm")
_prewarm_thread.start()


class OCREngine:
    """
    Production-grade OCR Engine wrapper for LM-Screen.
    Persists every OCR token with text, polygon, confidence, language, model_version.
    Uses EasyOCR with automatic contrast inversion and multi-pass preprocessing.
    Never returns hardcoded mock tokens for missing detections.

    Performance optimization: input image is resized to OCR_MAX_DIM before inference,
    and all polygon coordinates are scaled back to original image dimensions so that
    evidence overlays remain pixel-accurate.
    """
    def __init__(self):
        self.model_version = "EasyOCR-v1.7 / CRAFT"

    def _get_reader(self):
        """Return the pre-warmed EasyOCR reader, waiting up to 180 s for it to load."""
        ready = _reader_ready.wait(timeout=180)
        if not ready or _prewarmed_reader is None:
            print(f"[OCREngine] Reader not available (prewarm error: {_prewarm_error})")
            return None
        return _prewarmed_reader

    def _resize_for_ocr(self, image_np: np.ndarray):
        """
        Resize image so max dimension <= OCR_MAX_DIM.
        Returns (resized_image, scale_factor) where scale_factor = original / resized.
        If image is already small enough, returns original with scale=1.0.
        """
        h, w = image_np.shape[:2]
        max_dim = max(h, w)
        if max_dim <= OCR_MAX_DIM:
            return image_np, 1.0
        scale = OCR_MAX_DIM / max_dim
        new_w = int(w * scale)
        new_h = int(h * scale)
        resized = cv2.resize(image_np, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized, 1.0 / scale  # return inverse scale to project back

    def extract_tokens(
        self,
        image_input: Any,
        panel_box: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract OCR tokens with bounding boxes and confidence scores.
        Applies local polarity checking and high-resolution ROI OCR on detected declaration panels with CLAHE.
        Token polygons are always in the coordinate space of the ORIGINAL input image.
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

        # 2. Resize full image for OCR performance
        ocr_input, coord_scale = self._resize_for_ocr(image_np)

        # 3. Local polarity checking: check if the primary region is dark or light
        if len(ocr_input.shape) == 3:
            gray = (0.299 * ocr_input[:, :, 0] + 0.587 * ocr_input[:, :, 1] + 0.114 * ocr_input[:, :, 2]).astype(np.uint8)
        else:
            gray = ocr_input

        mean_brightness = float(np.mean(gray))

        # 4. First pass: run on natural polarity (standard for printed labels and white stickers)
        primary_input = ocr_input
        try:
            results = reader.readtext(
                primary_input,
                paragraph=False,
                canvas_size=OCR_CANVAS_SIZE,
                batch_size=OCR_BATCH_SIZE,
                workers=0,
            )
        except Exception as e:
            print(f"[OCREngine] EasyOCR pass 1 error: {e}")
            results = []

        # 5. Targeted fallback pass: ONLY if natural pass yielded very few tokens (<5)
        # AND local background is genuinely dark (<80) without a light sticker, test inverted polarity
        if len(results) < 5 and mean_brightness < 80.0 and not panel_box:
            alternate_input = (255 - ocr_input)
            try:
                alt_results = reader.readtext(
                    alternate_input,
                    paragraph=False,
                    canvas_size=OCR_CANVAS_SIZE,
                    batch_size=OCR_BATCH_SIZE,
                    workers=0,
                )
                if len(alt_results) > len(results):
                    results = alt_results
            except Exception as e:
                print(f"[OCREngine] EasyOCR pass 2 error: {e}")

        # 6. Convert full-image OCR detections into structured tokens
        for i, (bbox, text, prob) in enumerate(results):
            text_str = str(text).strip()
            if not text_str:
                continue
            polygon = [[int(pt[0] * coord_scale), int(pt[1] * coord_scale)] for pt in bbox]
            xs = [p[0] for p in polygon]
            ys = [p[1] for p in polygon]
            tokens.append({
                "id": f"tok_{i + 1}",
                "text": text_str,
                "polygon": polygon,
                "bbox": {"x1": min(xs), "y1": min(ys), "x2": max(xs), "y2": max(ys)},
                "confidence": round(float(prob), 3),
                "language": "en",
                "engine": "EasyOCR",
                "ocr_version": self.model_version,
                "model_version": self.model_version,
                "source_region": "FULL_IMAGE"
            })

        # 7. High-Resolution Panel ROI OCR (if an information panel is detected)
        if panel_box and len(panel_box) == 4:
            px, py, pw, ph = [int(v) for v in panel_box]
            h_orig, w_orig = image_np.shape[:2]
            px = max(0, min(px, w_orig - 10))
            py = max(0, min(py, h_orig - 10))
            pw = min(pw, w_orig - px)
            ph = min(ph, h_orig - py)

            if pw > 80 and ph > 80:
                panel_crop = image_np[py:py+ph, px:px+pw]
                # Apply CLAHE contrast enhancement for fine text (e.g. USP, dates, license)
                try:
                    if len(panel_crop.shape) == 3:
                        lab = cv2.cvtColor(panel_crop, cv2.COLOR_RGB2LAB)
                        l_ch, a_ch, b_ch = cv2.split(lab)
                        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                        enhanced_l = clahe.apply(l_ch)
                        enhanced_panel = cv2.cvtColor(cv2.merge((enhanced_l, a_ch, b_ch)), cv2.COLOR_LAB2RGB)
                    else:
                        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                        enhanced_panel = clahe.apply(panel_crop)

                    # Resize ROI if necessary to avoid excessive compute while keeping high resolution
                    roi_input, roi_scale = self._resize_for_ocr(enhanced_panel)
                    roi_results = reader.readtext(
                        roi_input,
                        paragraph=False,
                        canvas_size=OCR_CANVAS_SIZE,
                        batch_size=OCR_BATCH_SIZE,
                        workers=0
                    )

                    # Deduplicate & merge ROI tokens into token list
                    # An ROI token is added if it isn't an exact duplicate or has better resolution
                    tok_offset = len(tokens)
                    for r_idx, (r_bbox, r_text, r_prob) in enumerate(roi_results):
                        r_text_str = str(r_text).strip()
                        if not r_text_str:
                            continue
                        # Project coordinates: ROI-resized -> ROI original -> Full image
                        roi_poly = [
                            [int(pt[0] * roi_scale + px), int(pt[1] * roi_scale + py)]
                            for pt in r_bbox
                        ]
                        r_xs = [p[0] for p in roi_poly]
                        r_ys = [p[1] for p in roi_poly]
                        
                        # Check if a token with essentially identical text & bounding box already exists
                        existing = any(
                            t.get("text", "").lower() == r_text_str.lower() and
                            abs(t["bbox"]["x1"] - min(r_xs)) < 25 and
                            abs(t["bbox"]["y1"] - min(r_ys)) < 25
                            for t in tokens
                        )
                        if not existing:
                            tokens.append({
                                "id": f"tok_roi_{tok_offset + r_idx + 1}",
                                "text": r_text_str,
                                "polygon": roi_poly,
                                "bbox": {"x1": min(r_xs), "y1": min(r_ys), "x2": max(r_xs), "y2": max(r_ys)},
                                "confidence": round(float(r_prob), 3),
                                "language": "en",
                                "engine": "EasyOCR",
                                "ocr_version": self.model_version,
                                "model_version": self.model_version,
                                "source_region": "INFORMATION_PANEL"
                            })
                except Exception as ex:
                    print(f"[OCREngine] Panel ROI OCR error: {ex}")

        print(f"[OCREngine] Extracted {len(tokens)} tokens (mean_brightness={mean_brightness:.1f}, "
              f"ocr_input_size={ocr_input.shape[1]}x{ocr_input.shape[0]}, coord_scale={coord_scale:.2f})")
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
