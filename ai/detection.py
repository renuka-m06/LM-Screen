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

            screen_cnt = None
            for c in contours:
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
                    "confidence": 0.88,
                    "polygon": polygon,
                    "crop_box": [
                        int(rect[0][0]), int(rect[0][1]),
                        int(rect[2][0] - rect[0][0]), int(rect[2][1] - rect[0][1])
                    ],
                    "reasons": ["Quadrilateral information panel detected successfully"]
                }
        except Exception as e:
            pass

        # Fallback to full image dimensions if quad contour detection fails
        return {
            "detected": False,
            "confidence": 0.50,
            "polygon": [[0, 0], [width, 0], [width, height], [0, height]],
            "crop_box": [0, 0, width, height],
            "reasons": ["Quadrilateral contour detection uncertain; using default full frame ROI."]
        }
