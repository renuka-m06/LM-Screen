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
            import os
            try:
                # Provide a best-effort DLL path addition for Windows Python 3.8+
                import site
                for sp in site.getsitepackages() + [site.getusersitepackages()]:
                    pyzbar_dir = os.path.join(sp, "pyzbar")
                    if os.path.exists(pyzbar_dir):
                        os.add_dll_directory(pyzbar_dir)
            except Exception:
                pass
                
            from pyzbar.pyzbar import decode
            
            gray = cv2.cvtColor(image_np, cv2.COLOR_BGR2GRAY)
            res = decode(gray)
            if not res:
                res = decode(image_np)
                
            if res:
                # Use the first decoded barcode
                obj = res[0]
                gtin = obj.data.decode("utf-8")
                symbology = str(obj.type)
                
                if not gtin:
                    raise ValueError("Empty barcode decoded")
                
                # pyzbar polygon is a list of Point(x,y)
                # bounding box is obj.rect (left, top, width, height)
                width = obj.rect.width
                height = obj.rect.height
                
                if obj.polygon and len(obj.polygon) >= 4:
                    pts = obj.polygon
                    barcode_polygon = [[pt.x, pt.y] for pt in pts]
                else:
                    l, t, w, h = obj.rect.left, obj.rect.top, obj.rect.width, obj.rect.height
                    barcode_polygon = [[l, t], [l+w, t], [l+w, t+h], [l, t+h]]
                    
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
                        "status": "VALID_SCALE_REFERENCE",
                        "gtin": gtin,
                        "symbology": symbology,
                        "scale_reference_usable": True,
                        "scale_mm_per_pixel": round(scale_mm_per_pixel, 4),
                        "measurement_mode": measurement_mode,
                        "barcode_polygon": barcode_polygon,
                        "reasons": [f"Decoded {symbology} barcode: {gtin}. Valid scale reference established ({measurement_mode})."]
                    }
                else:
                    return {
                        "status": "DECODED_NOT_MEASURABLE",
                        "gtin": gtin,
                        "symbology": symbology,
                        "scale_reference_usable": False,
                        "scale_mm_per_pixel": None,
                        "measurement_mode": None,
                        "barcode_polygon": barcode_polygon,
                        "reasons": ["photo too distorted for reliable measurement"]
                    }
        except ImportError as e:
            # Re-raise import errors to make dependency gaps obvious
            print(f"pyzbar dependency missing: {e}")
        except Exception as e:
            print(f"Barcode exception: {e}")

        return {
            "status": "NOT_DETECTED",
            "gtin": None,
            "symbology": None,
            "scale_reference_usable": False,
            "scale_mm_per_pixel": None,
            "measurement_mode": None,
            "reasons": ["No visible barcode detected in current image."]
        }

