import numpy as np
from typing import Dict, Any, Optional

class BarcodeEngine:
    """
    Barcode & Physical Scale Reference Engine for LM-Screen.
    Validates barcode symbology, decode completeness, polygon geometry, and scale reference eligibility.
    States:
    - VALIDATED_SCALE_REFERENCE
    - DECODED_BUT_UNSUITABLE_FOR_SCALE
    - PARTIAL_OR_DISTORTED_BARCODE
    - BARCODE_NOT_FOUND
    - BARCODE_CONFLICT
    """
    def decode_and_validate(self, image_np: np.ndarray, reference_card_width_px: Optional[float] = None) -> Dict[str, Any]:
        if image_np is None or image_np.size == 0:
            return {
                "status": "BARCODE_NOT_FOUND",
                "gtin": None,
                "symbology": None,
                "scale_reference_usable": False,
                "scale_mm_per_pixel": None,
                "measurement_mode": None,
                "reasons": ["No image input provided"]
            }

        try:
            import cv2
            bd = cv2.barcode.BarcodeDetector()
            gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
            
            # Use OpenCV detectAndDecode
            res = bd.detectAndDecode(gray)
            decoded_info, corners, decoded_type = None, None, None
            if len(res) == 3:
                decoded_info, corners, decoded_type = res
            elif len(res) == 4:
                _, decoded_info, decoded_type, corners = res
                
            if not decoded_info or (isinstance(decoded_info, (tuple, list)) and not decoded_info[0]):
                res = bd.detectAndDecode(image_np)
                if len(res) == 3:
                    decoded_info, corners, decoded_type = res
                elif len(res) == 4:
                    _, decoded_info, decoded_type, corners = res

            if decoded_info:
                gtin = decoded_info[0] if isinstance(decoded_info, (tuple, list)) else decoded_info
                if not gtin:
                    raise ValueError("Empty barcode decoded")
                    
                symbology = "EAN13"
                if decoded_type is not None:
                    symb_val = decoded_type[0] if isinstance(decoded_type, (tuple, list)) else decoded_type
                    if symb_val:
                        symbology = str(symb_val)

                if corners is not None and len(corners) > 0:
                    pts = corners[0] if len(corners.shape) == 3 else corners
                    x_coords = [p[0] for p in pts]
                    y_coords = [p[1] for p in pts]
                    width = max(x_coords) - min(x_coords)
                    height = max(y_coords) - min(y_coords)
                    
                    # OpenCV barcode detector often returns a bounding box around a horizontal slice
                    # of the barcode rather than the full height, so aspect ratio can be > 3.0.
                    # We just ensure it's not a vertical sliver and width is sufficient.
                    aspect_ratio = width / height if height > 0 else 0
                    
                    if aspect_ratio > 0.5 and width > 30:
                        measurement_mode = "estimate"
                        scale_mm_per_pixel = None
                        
                        if reference_card_width_px and reference_card_width_px > 0:
                            scale_mm_per_pixel = 85.6 / reference_card_width_px
                            measurement_mode = "certified"
                        else:
                            nominal_width_mm = 37.29 if "EAN13" in symbology.upper() else 25.0
                            scale_mm_per_pixel = nominal_width_mm / width
                            
                        return {
                            "status": "VALIDATED_SCALE_REFERENCE",
                            "gtin": gtin,
                            "symbology": symbology,
                            "scale_reference_usable": True,
                            "scale_mm_per_pixel": round(scale_mm_per_pixel, 4),
                            "measurement_mode": measurement_mode,
                            "barcode_polygon": [[int(pt[0]), int(pt[1])] for pt in pts],
                            "reasons": [f"Decoded {symbology} barcode: {gtin}. Valid scale reference established ({measurement_mode})."]
                        }
                    else:
                        return {
                            "status": "PARTIAL_OR_DISTORTED_BARCODE",
                            "gtin": gtin,
                            "symbology": symbology,
                            "scale_reference_usable": False,
                            "scale_mm_per_pixel": None,
                            "measurement_mode": None,
                            "reasons": ["photo too distorted for reliable measurement"]
                        }
        except Exception as e:
            pass

        return {
            "status": "BARCODE_NOT_FOUND",
            "gtin": None,
            "symbology": None,
            "scale_reference_usable": False,
            "scale_mm_per_pixel": None,
            "measurement_mode": None,
            "reasons": ["No visible barcode detected in current image."]
        }
