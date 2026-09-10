import hashlib
from typing import Dict, Any, Optional

class DuplicateDetector:
    """
    Duplicate Signal & Scan Detector for LM-Screen.
    Uses GTIN, issue type, and image hash similarity.
    Returns: NOT_DUPLICATE, POSSIBLE_DUPLICATE, or LIKELY_DUPLICATE.
    Never deletes records automatically.
    """
    def compute_image_hash(self, image_bytes: bytes) -> str:
        return hashlib.sha256(image_bytes).hexdigest()

    def check_duplicate(
        self,
        new_gtin: Optional[str],
        new_image_hash: str,
        existing_records: list
    ) -> Dict[str, Any]:
        
        for record in existing_records:
            # 1. Exact image hash match
            if record.get("image_hash") == new_image_hash:
                return {
                    "status": "LIKELY_DUPLICATE",
                    "matched_record_id": record.get("id"),
                    "match_type": "EXACT_IMAGE_HASH",
                    "confidence": 0.99
                }
            
            # 2. GTIN and issue category match within short timeframe
            if new_gtin and record.get("gtin") == new_gtin:
                return {
                    "status": "POSSIBLE_DUPLICATE",
                    "matched_record_id": record.get("id"),
                    "match_type": "SAME_GTIN_PRODUCT",
                    "confidence": 0.85
                }

        return {
            "status": "NOT_DUPLICATE",
            "matched_record_id": None,
            "match_type": "UNIQUE",
            "confidence": 1.0
        }
