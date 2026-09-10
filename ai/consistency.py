import re
from typing import Dict, Any, Optional

class ConsistencyScreening:
    """
    Consistency Screening for GSTIN and GTIN identifiers.
    Performs checksum verification and local lookup matching.
    Does NOT claim official external verification unless a verified provider is connected.
    """
    STATE_CODES = {
        "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
        "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan",
        "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
        "13": "Nagaland", "14": "Manipur", "15": "Mizoram", "16": "Tripura",
        "17": "Meghalaya", "18": "Assam", "19": "West Bengal", "20": "Jharkhand",
        "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
        "26": "Dadra & Nagar Haveli and Daman & Diu", "27": "Maharashtra",
        "28": "Andhra Pradesh (Old)", "29": "Karnataka", "30": "Goa",
        "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
        "35": "Andaman & Nicobar Islands", "36": "Telangana", "37": "Andhra Pradesh"
    }

    def validate_gstin(self, gstin_str: Optional[str]) -> Dict[str, Any]:
        if not gstin_str:
            return {
                "status": "NOT_PROVIDED",
                "valid_format": False,
                "state_name": None,
                "reasons": ["No GSTIN string provided for screening."]
            }

        gstin_str = gstin_str.strip().upper()
        pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"

        if not re.match(pattern, gstin_str):
            return {
                "status": "FORMAT_INVALID",
                "valid_format": False,
                "state_name": None,
                "reasons": [f"GSTIN format '{gstin_str}' fails 15-character statutory structure check."]
            }

        state_code = gstin_str[:2]
        state_name = self.STATE_CODES.get(state_code, "Other/Union Territory")

        return {
            "status": "CONSISTENT_FORMAT",
            "valid_format": True,
            "state_code": state_code,
            "state_name": state_name,
            "pan": gstin_str[2:10],
            "entity_number": gstin_str[10],
            "reasons": [
                f"Valid GSTIN structure for state of {state_name}.",
                "Note: External GSTIN registry verification not connected. "
                "Format-only check performed. Status: RULE_REQUIRES_OFFICIAL_VERIFICATION."
            ]
        }

    def validate_gtin(self, gtin_str: Optional[str]) -> Dict[str, Any]:
        """Validate GTIN using GS1 Modulo-10 checksum."""
        if not gtin_str:
            return {
                "status": "NOT_PROVIDED",
                "valid_checksum": False,
                "reasons": ["No GTIN barcode identifier provided."]
            }

        # FIX: Was using wrong variable name 'gstin_str' — fixed to 'gtin_str'
        gtin_str = gtin_str.strip()
        if not gtin_str.isdigit() or len(gtin_str) not in [8, 12, 13, 14]:
            return {
                "status": "FORMAT_INVALID",
                "valid_checksum": False,
                "gtin": gtin_str,
                "reasons": [f"GTIN '{gtin_str}' has invalid length ({len(gtin_str)}). Expected 8, 12, 13, or 14 digits."]
            }

        # Calculate GS1 Modulo-10 Check Digit
        digits = [int(d) for d in gtin_str[:-1]]
        checksum_digit = int(gtin_str[-1])

        # Multiply alternating digits from right to left by 3 and 1
        total = 0
        multiplier = 3
        for d in reversed(digits):
            total += d * multiplier
            multiplier = 1 if multiplier == 3 else 3

        calculated_check = (10 - (total % 10)) % 10
        valid = (calculated_check == checksum_digit)

        return {
            "status": "CONSISTENT_GTIN" if valid else "CHECKSUM_FAILED",
            "valid_checksum": valid,
            "gtin": gtin_str,
            "gtin_length": len(gtin_str),
            "country_prefix": gtin_str[:3] if len(gtin_str) == 13 else None,
            "reasons": [
                f"GTIN GS1 Modulo-10 checksum {'valid' if valid else 'MISMATCH — expected check digit ' + str(calculated_check) + ' but found ' + str(checksum_digit)}."
            ]
        }

    def check_identity_consistency(
        self,
        user_product_name: Optional[str],
        ocr_product_name: Optional[str],
        user_gtin: Optional[str],
        ocr_gtin: Optional[str],
        barcode_gtin: Optional[str]
    ) -> Dict[str, Any]:
        """
        Checks for conflicts between user-supplied metadata and OCR evidence.
        Returns warnings with NEEDS_REVIEW status — does NOT produce compliance verdict.
        """
        warnings = []

        # Product name mismatch
        name_mismatch = False
        if user_product_name and ocr_product_name:
            # Fuzzy: check if the user name appears in OCR or vice versa (case-insensitive)
            u = user_product_name.lower().strip()
            o = ocr_product_name.lower().strip()
            # Simple containment check — if neither contains the other, flag it
            if u not in o and o not in u:
                # Check for at least 2 common words
                u_words = set(u.split())
                o_words = set(o.split())
                common = u_words & o_words
                significant_common = {w for w in common if len(w) > 3}
                if not significant_common:
                    name_mismatch = True
                    warnings.append({
                        "type": "PRODUCT_IDENTITY_MISMATCH",
                        "severity": "NEEDS_REVIEW",
                        "user_provided": user_product_name,
                        "image_evidence": ocr_product_name,
                        "explanation": (
                            "The supplied product name does not match the product identity "
                            "visible in the uploaded image. Please verify the correct product "
                            "and re-upload if needed. This does not automatically indicate "
                            "legal non-compliance."
                        )
                    })

        # GTIN mismatch
        all_gtins = {g for g in [user_gtin, ocr_gtin, barcode_gtin] if g}
        if len(all_gtins) > 1:
            warnings.append({
                "type": "GTIN_CONSISTENCY_WARNING",
                "severity": "NEEDS_REVIEW",
                "user_provided": user_gtin,
                "ocr_value": ocr_gtin,
                "barcode_decoded": barcode_gtin,
                "explanation": (
                    "Multiple different GTIN/barcode values detected from different sources. "
                    "Human verification required to establish the correct identifier."
                )
            })

        return {
            "has_warnings": len(warnings) > 0,
            "name_mismatch": name_mismatch,
            "warnings": warnings
        }
