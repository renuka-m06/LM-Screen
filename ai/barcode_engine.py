import cv2
import numpy as np
from typing import Dict, Any, Optional

class BarcodeEngine:
    """
    Barcode & Physical Scale Reference Engine for LM-Screen.
    Validates barcode symbology, decode completeness, polygon geometry, and scale reference eligibility.
    States:
    - VALID_SCALE_REFERENCE
    - DECODED_NOT_MEASURABLE
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
            # Provide a best-effort DLL path addition for Windows Python 3.8+
            try:
                import site
                dirs = []
                try:
                    dirs.extend(site.getsitepackages())
                except Exception:
                    pass
                try:
                    dirs.append(site.getusersitepackages())
                except Exception:
                    pass
                for sp in dirs:
                    pyzbar_dir = os.path.join(sp, "pyzbar")
                    if os.path.exists(pyzbar_dir):
                        try:
                            os.add_dll_directory(pyzbar_dir)
                        except Exception:
                            pass
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
            print(f"[LM-SCREEN] pyzbar dependency unavailable: {e}")
        except OSError as e:
            # Windows DLL loading failure — silent fallback, do not block pipeline
            print(f"[LM-SCREEN] pyzbar DLL unavailable (Windows): {e}")
        except Exception as e:
            print(f"[LM-SCREEN] Barcode detection error: {e}")

        # Fallback to OpenCV native barcode detector if pyzbar did not decode
        try:
            if hasattr(cv2, 'barcode') and hasattr(cv2.barcode, 'BarcodeDetector'):
                detector = cv2.barcode.BarcodeDetector()
                ret = detector.detectAndDecode(image_np)
                if len(ret) == 4:
                    retval, decoded_info, decoded_type, points = ret
                elif len(ret) == 3:
                    decoded_info, decoded_type, points = ret
                    retval = bool(decoded_info and (isinstance(decoded_info, (list, tuple)) and len(decoded_info) > 0 and decoded_info[0] or isinstance(decoded_info, str) and decoded_info))
                else:
                    retval = False

                if retval:
                    info_val = decoded_info[0] if isinstance(decoded_info, (list, tuple)) else decoded_info
                    gtin = str(info_val).strip()
                    if gtin:
                        symbology = str(decoded_type[0]) if (isinstance(decoded_type, (list, tuple)) and len(decoded_type) > 0) else "BARCODE"
                        poly = points[0].tolist() if points is not None and len(points) > 0 else []
                        return {
                            "status": "VALID_SCALE_REFERENCE",
                            "gtin": gtin,
                            "symbology": symbology,
                            "scale_reference_usable": False,
                            "scale_mm_per_pixel": None,
                            "measurement_mode": None,
                            "barcode_polygon": poly,
                            "reasons": [f"Decoded {symbology} barcode: {gtin} via OpenCV BarcodeDetector."]
                        }
        except Exception as e:
            print(f"[LM-SCREEN] cv2.barcode detector fallback error: {e}")

        return {
            "status": "NOT_DECODED",
            "gtin": None,
            "value": None,
            "symbology": None,
            "scale_reference_usable": False,
            "scale_mm_per_pixel": None,
            "measurement_mode": None,
            "reasons": ["No visible barcode decoded in current image."]
        }

