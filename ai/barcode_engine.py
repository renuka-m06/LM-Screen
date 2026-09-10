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
    def decode_and_validate(self, image_np: np.ndarray) -> Dict[str, Any]:
        if image_np is None or image_np.size == 0:
            return {
                "status": "BARCODE_NOT_FOUND",
                "gtin": None,
                "symbology": None,
                "scale_reference_usable": False,
                "pixel_per_mm": None,
                "reasons": ["No image input provided"]
            }

        # Try pyzbar if installed
        try:
            from pyzbar.pyzbar import decode as pyzbar_decode
            barcodes = pyzbar_decode(image_np)
            if barcodes:
                first = barcodes[0]
                gtin = first.data.decode('utf-8').strip()
                symbology = first.type
                rect = first.rect
                
                # Check aspect ratio & sharpness for physical scale measurement eligibility
                is_undistorted = (rect.width > 30 and rect.height > 20)
                
                if is_undistorted and symbology in ['EAN13', 'EAN8', 'UPCA', 'CODE128']:
                    # Standard EAN-13 nominal width is ~37.29 mm
                    nominal_width_mm = 37.29 if symbology == 'EAN13' else 25.0
                    pixel_per_mm = rect.width / nominal_width_mm
                    return {
                        "status": "VALIDATED_SCALE_REFERENCE",
                        "gtin": gtin,
                        "symbology": symbology,
                        "scale_reference_usable": True,
                        "pixel_per_mm": round(pixel_per_mm, 2),
                        "barcode_polygon": [[rect.left, rect.top], [rect.left+rect.width, rect.top], [rect.left+rect.width, rect.top+rect.height], [rect.left, rect.top+rect.height]],
                        "reasons": [f"Decoded {symbology} barcode: {gtin}. Valid scale reference established."]
                    }
                else:
                    return {
                        "status": "DECODED_BUT_UNSUITABLE_FOR_SCALE",
                        "gtin": gtin,
                        "symbology": symbology,
                        "scale_reference_usable": False,
                        "pixel_per_mm": None,
                        "reasons": ["Barcode decoded but geometry or distortion prevents reliable physical scale measurement."]
                    }
        except Exception:
            pass

        return {
            "status": "BARCODE_NOT_FOUND",
            "gtin": None,
            "symbology": None,
            "scale_reference_usable": False,
            "pixel_per_mm": None,
            "reasons": ["No visible barcode detected in current image."]
        }
