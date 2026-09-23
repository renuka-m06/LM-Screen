import numpy as np
from typing import Dict, Any, Optional, Tuple

class PackageDetector:
    """
    OpenCV-based quadrilateral package & information panel detector.
    Performs contour detection, polygon approximation, and perspective transformation.
    """
    def order_points(self, pts: np.ndarray) -> np.ndarray:
        # Order points: top-left, top-right, bottom-right, bottom-left
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]

        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    def detect_panel(self, image_np: np.ndarray) -> Dict[str, Any]:
        if image_np is None or image_np.size == 0:
            return {
                "detected": False,
                "confidence": 0.0,
                "polygon": None,
                "reasons": ["Empty image"]
            }

        height, width = image_np.shape[:2]

        try:
            import cv2
            gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edged = cv2.Canny(blurred, 50, 200)

            contours, _ = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:5]

            # 1. Try Canny edge-based quadrilateral detection
            screen_cnt = None
            for c in contours:
                area = cv2.contourArea(c)
                if area < 0.04 * (width * height):
                    continue
                peri = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(c, 0.02 * peri, True)
                if len(approx) == 4:
                    screen_cnt = approx
                    break

            if screen_cnt is not None:
                pts = screen_cnt.reshape(4, 2)
                rect = self.order_points(pts)
                polygon = [[int(x), int(y)] for x, y in rect]
                
                return {
                    "detected": True,
                    "confidence": 0.90,
                    "polygon": polygon,
                    "crop_box": [
                        max(0, int(rect[0][0])), max(0, int(rect[0][1])),
                        min(width, int(rect[2][0] - rect[0][0])), min(height, int(rect[2][1] - rect[0][1]))
                    ],
                    "reasons": ["Quadrilateral information panel detected successfully"]
                }

            # 2. Try high-contrast label / panel segmentation (e.g. white/light sticker on package)
            # Combine Otsu + fixed high threshold to isolate white declaration sticker
            _, thresh_fixed = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
            _, thresh_otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Adaptive threshold for complex, uneven lighting
            thresh_adapt = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 2
            )

            # Test threshold maps with morphological closing to fuse text lines into a panel
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (25, 25))
            for thresh_map in [thresh_fixed, thresh_otsu, thresh_adapt]:
                closed = cv2.morphologyEx(thresh_map, cv2.MORPH_CLOSE, kernel)
                lbl_contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                lbl_contours = sorted(lbl_contours, key=cv2.contourArea, reverse=True)

                for c in lbl_contours:
                    area = cv2.contourArea(c)
                    if 0.03 * (width * height) <= area <= 0.95 * (width * height):
                        x, y, w, h = cv2.boundingRect(c)
                        aspect = w / h if h > 0 else 0
                        if 0.25 <= aspect <= 4.0:
                            polygon = [[x, y], [x + w, y], [x + w, y + h], [x, y + h]]
                            return {
                                "detected": True,
                                "confidence": 0.88,
                                "polygon": polygon,
                                "crop_box": [max(0, int(x)), max(0, int(y)), min(width - x, int(w)), min(height - y, int(h))],
                                "reasons": ["High-contrast declaration panel detected successfully"]
                            }
        except Exception:
            pass

        # Fallback to full image dimensions if quad contour detection fails
        return {
            "detected": False,
            "confidence": 0.50,
            "polygon": [[0, 0], [width, 0], [width, height], [0, height]],
            "crop_box": [0, 0, width, height],
            "reasons": ["Quadrilateral contour detection uncertain; using default full frame ROI."]
        }
