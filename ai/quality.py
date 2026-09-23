import numpy as np
from typing import Dict, Any

class ImageQualityGate:
    """
    Image Quality Gate for LM-Screen.
    Evaluates:
    1. Resolution (min width/height)
    2. Blur (Variance of Laplacian)
    3. Brightness (Mean grayscale value)
    4. Glare (Ratio of saturated pixels)
    Returns status: ACCEPTABLE, PARTIALLY_USABLE, or RETAKE_REQUIRED
    """
    def __init__(
        self,
        min_width: int = 400,
        min_height: int = 400,
        blur_threshold: float = 80.0,
        min_brightness: float = 0.15,
        max_brightness: float = 0.85,
        max_glare_ratio: float = 0.15
    ):
        self.min_width = min_width
        self.min_height = min_height
        self.blur_threshold = blur_threshold
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.max_glare_ratio = max_glare_ratio

    def assess_quality(self, image_np: np.ndarray) -> Dict[str, Any]:
        if image_np is None or image_np.size == 0:
            return {
                "status": "RETAKE_REQUIRED",
                "resolution_ok": False,
                "blur_score": 0.0,
                "brightness_score": 0.0,
                "glare_ratio": 1.0,
                "reasons": ["Invalid or empty image file"]
            }

        # Check resolution
        height, width = image_np.shape[:2]
        resolution_ok = (width >= self.min_width) and (height >= self.min_height)

        # Convert to Grayscale if RGB/BGR
        if len(image_np.shape) == 3 and image_np.shape[2] in [3, 4]:
            # Simple weighted RGB to grayscale calculation
            gray = (0.299 * image_np[:, :, 0] + 0.587 * image_np[:, :, 1] + 0.114 * image_np[:, :, 2]).astype(np.uint8)
        else:
            gray = image_np

        # Calculate Blur Score (Variance of Laplacian)
        # Using 2D spatial gradient magnitude approximation if opencv not available
        try:
            import cv2
            blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        except Exception:
            # Fallback 2D gradient variance estimation
            gy, gx = np.gradient(gray.astype(float))
            blur_score = float(np.var(gx) + np.var(gy))

        # Calculate Brightness Score (0.0 to 1.0)
        brightness_score = float(np.mean(gray) / 255.0)

        # Calculate Contrast Score (standard deviation normalized, 0.0 to 1.0)
        contrast_score = float(np.std(gray) / 128.0)

        # Calculate Glare Ratio (fraction of pixels > 245)
        glare_ratio = float(np.sum(gray > 245) / gray.size)

        reasons = []
        if not resolution_ok:
            reasons.append(f"Image resolution too low ({width}x{height}, required min {self.min_width}x{self.min_height})")
        if blur_score < self.blur_threshold:
            reasons.append(f"Image too blurry (score: {blur_score:.1f}, required >= {self.blur_threshold:.1f})")
        
        # Only flag dark if contrast is also poor (dark background with sharp white text is high contrast and legible)
        if brightness_score < self.min_brightness and contrast_score < 0.25:
            reasons.append(f"Image too dark (brightness: {brightness_score:.2f}, contrast: {contrast_score:.2f})")
        elif brightness_score > self.max_brightness and blur_score < 500.0:
            reasons.append(f"Image overexposed (brightness: {brightness_score:.2f})")
        if glare_ratio > self.max_glare_ratio and blur_score < 500.0:
            reasons.append(f"Excessive glare detected (glare ratio: {glare_ratio:.2f})")

        # Determine overall state and status:
        # Standardized States: HIGH_QUALITY, READABLE, REVIEW_QUALITY, UNUSABLE
        # Operational Statuses: ACCEPTABLE, PARTIALLY_USABLE, RETAKE_REQUIRED
        if not resolution_ok or blur_score < (self.blur_threshold * 0.35):
            state = "UNUSABLE"
            status = "RETAKE_REQUIRED"
            quality_label = "Unusable (Retake Needed)"
        elif glare_ratio > (self.max_glare_ratio * 2.5) and blur_score < 300.0:
            state = "UNUSABLE"
            status = "RETAKE_REQUIRED"
            quality_label = "Unusable (Excessive Glare)"
        elif len(reasons) > 0 or blur_score < self.blur_threshold:
            state = "REVIEW_QUALITY"
            status = "PARTIALLY_USABLE"
            quality_label = "Review Quality (Partially Clear)"
        elif blur_score > (self.blur_threshold * 1.5) and 0.20 <= brightness_score <= 0.80 and glare_ratio < 0.05:
            state = "HIGH_QUALITY"
            status = "ACCEPTABLE"
            quality_label = "High Quality (Clear & Legible)"
        else:
            state = "READABLE"
            status = "ACCEPTABLE"
            quality_label = "Readable (Declaration Panel Legible)"

        return {
            "status": status,
            "state": state,
            "quality_label": quality_label,
            "usable": state != "UNUSABLE",
            "resolution_ok": resolution_ok,
            "blur_score": round(blur_score, 2),
            "brightness_score": round(brightness_score, 2),
            "contrast_score": round(contrast_score, 2),
            "glare_ratio": round(glare_ratio, 2),
            "width": width,
            "height": height,
            "reasons": reasons
        }

    def upgrade_with_ocr(self, quality_result: Dict[str, Any], ocr_tokens: list) -> Dict[str, Any]:
        """
        If OCR successfully extracted readable tokens, upgrade quality state.
        Image quality must never stop screening or declare UNUSABLE when useful evidence is present.
        """
        if not ocr_tokens:
            return quality_result

        high_conf_tokens = [t for t in ocr_tokens if t.get("confidence", 0) >= 0.50]
        if len(high_conf_tokens) >= 3:
            updated = dict(quality_result)
            current_state = updated.get("state", updated.get("status"))
            if current_state in ["UNUSABLE", "REVIEW_QUALITY", "PARTIALLY_USABLE", "RETAKE_REQUIRED"]:
                if len(high_conf_tokens) >= 10:
                    updated["state"] = "HIGH_QUALITY"
                    updated["status"] = "ACCEPTABLE"
                    updated["quality_label"] = "High Quality (Verified by Evidence)"
                else:
                    updated["state"] = "READABLE"
                    updated["status"] = "ACCEPTABLE"
                    updated["quality_label"] = "Readable (Verified by Evidence)"
                updated["usable"] = True
                updated["reasons"] = [r for r in updated.get("reasons", []) if "dark" not in r.lower() and "blurry" not in r.lower()]
                return updated

        return quality_result
