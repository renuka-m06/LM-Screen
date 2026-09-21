from typing import List, Dict, Any

class EvidenceQualityEvaluator:
    """
    Evaluates extracted evidence against image quality, OCR confidence, 
    and cross-evidence consistency to assign a transparent trust state.
    """
    def __init__(self):
        pass

    def evaluate_evidence(
        self, 
        evidence_list: List[Dict[str, Any]], 
        ocr_tokens: List[Dict[str, Any]], 
        image_quality: Dict[str, Any], 
        consistency_checks: List[Dict[str, Any]],
        barcode_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Assigns an evidence_state and quality_reasons to each piece of evidence.
        States: SUPPORTED, UNCERTAIN, CONFLICTING, UNREADABLE, NOT_DETECTED, MANUALLY_VERIFIED
        """
        # Create a lookup for OCR tokens by ID for fast confidence checking
        token_map = {str(t.get("token_id", t.get("id", ""))): t for t in ocr_tokens}
        
        for evidence in evidence_list:
            reasons = []
            state = "SUPPORTED"
            
            # 1. Not Detected
            if not evidence.get("found"):
                evidence["evidence_state"] = "NOT_DETECTED"
                evidence["quality_reasons"] = ["Field not found in available evidence."]
                continue

            # 2. Check Image Quality
            if not image_quality.get("usable", True) or image_quality.get("status") == "RETAKE_REQUIRED":
                state = "UNREADABLE"
                reasons.append("Overall image quality is too poor (e.g. high blur/glare) to reliably trust this region.")
            elif image_quality.get("status") == "PARTIALLY_USABLE":
                # If it's partially usable, we might demote to UNCERTAIN unless other signals are strong.
                state = "UNCERTAIN"
                reasons.append("Image is partially usable; visual clarity may be degraded.")

            # 3. Check OCR Confidence (if from OCR)
            ocr_ids = evidence.get("ocr_evidence_ids", [])
            if ocr_ids:
                confidences = []
                for tid in ocr_ids:
                    tok = token_map.get(str(tid))
                    if tok and "confidence" in tok:
                        confidences.append(tok["confidence"])
                
                if confidences:
                    avg_conf = sum(confidences) / len(confidences)
                    # Use actual model confidence to modulate the state
                    if avg_conf < 0.6:
                        state = "UNCERTAIN" if state != "UNREADABLE" else "UNREADABLE"
                        reasons.append(f"Low OCR model confidence ({avg_conf:.2f}).")
                    else:
                        reasons.append("OCR token confidence is acceptable.")
                else:
                    reasons.append("OCR confidence data unavailable.")
            elif evidence.get("source", {}).get("type") == "BARCODE":
                reasons.append("Evidence derived directly from barcode decoding.")
            
            # 4. Cross-Evidence Consistency
            # Check if this field was involved in any consistency check that requires review
            field_name = evidence.get("field")
            conflict_found = False
            for check in consistency_checks:
                if check.get("status") in ["REVIEW_REQUIRED", "INCONSISTENT"]:
                    # Is our field involved in this check?
                    # E.g. DUPLICATE_FIELD_CONFLICT or MRP_QTY_USP_CONSISTENCY
                    observed = check.get("observed_values", {})
                    if field_name in observed or field_name.lower() in [k.lower() for k in observed.keys()]:
                        conflict_found = True
                        reasons.append(f"Conflict detected in {check.get('check_type')}: {check.get('explanation')}")
                elif check.get("status") == "CONSISTENT":
                    observed = check.get("observed_values", {})
                    if field_name in observed or field_name.lower() in [k.lower() for k in observed.keys()]:
                        reasons.append(f"Corroborated by {check.get('check_type')}.")

            if conflict_found:
                state = "CONFLICTING"

            # 5. Check if it's manually verified (if we have that info)
            # Typically this happens in the API layer, but if passed in, we handle it.
            if evidence.get("evidence_state") == "MANUALLY_VERIFIED":
                state = "MANUALLY_VERIFIED"
                reasons = ["Officer manually verified and corrected this evidence."]

            # Finalize
            if not reasons and state == "SUPPORTED":
                reasons.append("Sufficient evidence to support this extraction.")

            evidence["evidence_state"] = state
            evidence["quality_reasons"] = reasons

        return evidence_list
