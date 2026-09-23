from typing import Dict, Any, List
import numpy as np
from ai.ocr_engine import OCREngine
from PIL import Image

class OCRService:
    """
    Standardized service for Optical Character Recognition.

    Performance-critical design: OCR inference runs exactly ONCE on the full image
    (already scaled to OCR_MAX_DIM by OCREngine). Detected panel regions are
    attributed by bounding-box intersection of the full-image tokens — no redundant
    crop-level EasyOCR re-inference.

    Fallback: if full-image OCR returned zero tokens (rare, e.g. white-on-white),
    a single crop-level pass is attempted for the primary detection only.
    """
    def __init__(self):
        self.ocr_engine = OCREngine()

    def _token_center_in_bbox(self, token: Dict[str, Any], x1: int, y1: int, x2: int, y2: int) -> bool:
        """Return True if the token's bbox center falls inside the given region bbox."""
        bbox = token.get("bbox")
        if not bbox:
            # Fallback: compute from polygon
            poly = token.get("polygon", [])
            if not poly:
                return False
            cx = sum(p[0] for p in poly) / len(poly)
            cy = sum(p[1] for p in poly) / len(poly)
        else:
            cx = (bbox.get("x1", 0) + bbox.get("x2", 0)) / 2
            cy = (bbox.get("y1", 0) + bbox.get("y2", 0)) / 2
        return x1 <= cx <= x2 and y1 <= cy <= y2

    def extract(self, image_input: Any, detections: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Extract OCR tokens. Full-image inference is run exactly once.
        Detection region attribution is assigned by bounding-box intersection,
        not by re-running EasyOCR on each crop.
        """
        # ── High-resolution panel detection & OCR ──────────────────────────────
        panel_box = None
        if detections:
            for d in detections:
                if d.get("crop_box"):
                    panel_box = d["crop_box"]
                    break
                elif "bbox" in d:
                    b = d["bbox"]
                    panel_box = [b["x1"], b["y1"], b["x2"] - b["x1"], b["y2"] - b["y1"]]
                    break

        all_tokens = self.ocr_engine.extract_tokens(image_input, panel_box=panel_box)

        # Tag all tokens as coming from full image initially unless already tagged as panel
        for t in all_tokens:
            if "source_region" not in t:
                t["source_region"] = "FULL_IMAGE"

        # ── Region attribution via intersection (zero extra inference) ──────────
        if detections and all_tokens:
            # Resolve numpy array once
            image_np: np.ndarray | None = None
            if isinstance(image_input, np.ndarray):
                image_np = image_input
            elif hasattr(image_input, "convert"):
                image_np = np.array(image_input.convert("RGB"))

            for det in detections:
                if "bbox" not in det:
                    continue
                bbox = det["bbox"]
                x1 = bbox.get("x1")
                y1 = bbox.get("y1")
                x2 = bbox.get("x2")
                y2 = bbox.get("y2")
                if None in (x1, y1, x2, y2):
                    continue

                region_label = det.get("class_name", "DETECTED_REGION")
                model_name   = det.get("model_name")
                model_version = det.get("model_version")

                for tok in all_tokens:
                    if self._token_center_in_bbox(tok, x1, y1, x2, y2):
                        # Override source_region only if still tagged as FULL_IMAGE
                        # (first matching detection wins; preserves priority ordering)
                        if tok["source_region"] == "FULL_IMAGE":
                            tok["source_region"] = region_label
                        if model_name:
                            tok["ml_model_name"] = model_name
                        if model_version:
                            tok["ml_model_version"] = model_version

        # ── Fallback: crop OCR only when full-image found nothing ─────────────
        # This guards against edge cases (white-on-white labels, extreme glare).
        # We only try the PRIMARY (first) detection to avoid multiple passes.
        elif detections and not all_tokens:
            image_np: np.ndarray | None = None
            if isinstance(image_input, np.ndarray):
                image_np = image_input
            elif hasattr(image_input, "convert"):
                image_np = np.array(image_input.convert("RGB"))

            if image_np is not None:
                primary_det = next(
                    (d for d in detections if "bbox" in d), None
                )
                if primary_det:
                    bbox = primary_det["bbox"]
                    x1, y1 = bbox.get("x1", 0), bbox.get("y1", 0)
                    x2, y2 = bbox.get("x2", image_np.shape[1]), bbox.get("y2", image_np.shape[0])
                    h, w = image_np.shape[:2]
                    cx1, cy1 = max(0, int(x1)), max(0, int(y1))
                    cx2, cy2 = min(w, int(x2)), min(h, int(y2))

                    if cx2 > cx1 and cy2 > cy1:
                        crop_np = image_np[cy1:cy2, cx1:cx2]
                        print(f"[LM-SCREEN] Full-image OCR returned 0 tokens — running fallback crop OCR on primary detection")
                        crop_tokens = self.ocr_engine.extract_tokens(crop_np)
                        for ct in crop_tokens:
                            # Translate crop-space polygons back to full-image space
                            if "polygon" in ct:
                                ct["polygon"] = [[pt[0] + cx1, pt[1] + cy1] for pt in ct["polygon"]]
                            if "bbox" in ct and ct["bbox"]:
                                b = ct["bbox"]
                                ct["bbox"] = {
                                    "x1": b["x1"] + cx1, "y1": b["y1"] + cy1,
                                    "x2": b["x2"] + cx1, "y2": b["y2"] + cy1,
                                }
                            ct["source_region"] = primary_det.get("class_name", "DETECTED_REGION")
                            ct["ml_model_name"] = primary_det.get("model_name")
                            ct["ml_model_version"] = primary_det.get("model_version")
                        all_tokens.extend(crop_tokens)

        summary = self.ocr_engine.get_ocr_summary(all_tokens)

        return {
            "status": summary.get("status"),
            "tokens": all_tokens,
            "token_count": summary.get("token_count"),
            "average_confidence": summary.get("average_confidence"),
            "model_version": self.ocr_engine.model_version
        }

