from typing import List, Dict, Any

class VerdictAggregator:
    """
    Verdict Aggregator for LM-Screen.
    Aggregates rule traces, image quality gate, identity warnings, and confidence
    metrics into the three official platform states:

    1. PASS_SCREENING          — "No issue detected in the checks performed"
    2. POTENTIAL_NON_COMPLIANCE — "Potential non-compliance detected"
    3. NEEDS_REVIEW            — "More evidence or human review required"

    Important rules:
    - Identity mismatch alone → NEEDS_REVIEW (never POTENTIAL_NON_COMPLIANCE)
    - Technical failures → NEEDS_REVIEW (never POTENTIAL_NON_COMPLIANCE)
    - POTENTIAL_NON_COMPLIANCE only when: rule known + evidence sufficient + field absent
    """
    MANDATORY_DISCLAIMER = (
        "This platform performs image-based Legal Metrology compliance screening for selected visible "
        "declarations. It does not replace inspection by an authorized officer, legal interpretation, "
        "laboratory testing, physical package measurement, or official enforcement procedures. Results "
        "depend on image quality, available declarations, product classification, rule version, and "
        "evidence confidence. This is a decision-support screening tool only."
    )

    STATUS_LABELS = {
        "PASS_SCREENING": "No issue detected in the checks performed",
        "POTENTIAL_NON_COMPLIANCE": "Potential non-compliance detected",
        "NEEDS_REVIEW": "More evidence or human review required"
    }

    def aggregate(
        self,
        rule_traces: List[Dict[str, Any]],
        quality_status: Dict[str, Any],
        barcode_status: Dict[str, Any],
        context: Dict[str, Any],
        identity_warnings: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:

        if identity_warnings is None:
            identity_warnings = []

        review_reasons = []
        checks_performed = []
        checks_not_performed = []

        # ── Gate 1: Image quality ──────────────────────────────────────────────
        if quality_status.get("status") == "RETAKE_REQUIRED":
            review_reasons.extend(quality_status.get("reasons", ["Image quality insufficient."]))
            return {
                "status": "NEEDS_REVIEW",
                "public_label": self.STATUS_LABELS["NEEDS_REVIEW"],
                "screening_confidence": 0.50,
                "checks_performed": [],
                "checks_not_performed": [{"check": "declaration_screening", "reason": "Retake required due to blur/glare/resolution"}],
                "evidence": [],
                "rule_version": "2026.1",
                "review_reasons": review_reasons,
                "disclaimer": self.MANDATORY_DISCLAIMER
            }

        # ── Gate 2: Identity warnings (NEEDS_REVIEW, never non-compliance) ─────
        has_identity_warning = len(identity_warnings) > 0
        for w in identity_warnings:
            review_reasons.append(f"{w['type']}: {w.get('explanation', '')}")

        # ── Gate 3: Scale reference check ─────────────────────────────────────
        if not barcode_status.get("scale_reference_usable", False):
            checks_not_performed.append({
                "check": "font_scale_screening",
                "reason": barcode_status.get("reasons", ["No suitable barcode scale reference detected."])[0]
            })
            # Note: missing barcode is NOT a legal failure, just a limitation
            review_reasons.append("Font size physical measurement not performed — no suitable scale reference.")

        # ── Gate 4: Rule Traces ────────────────────────────────────────────────
        has_potential_non_compliance = False
        has_needs_review = False

        for trace in rule_traces:
            if not trace.get("applicable", True):
                continue

            st = trace.get("status")
            checks_performed.append({
                "rule_id": trace.get("rule_id"),
                "rule_name": trace.get("rule_name"),
                "status": st,
                "reason": trace.get("reason")
            })

            if st == "POTENTIAL_NON_COMPLIANCE":
                has_potential_non_compliance = True
                review_reasons.append(f"Rule {trace.get('rule_id')}: {trace.get('reason')}")
            elif st == "NEEDS_REVIEW":
                has_needs_review = True
                review_reasons.append(f"Rule {trace.get('rule_id')} uncertain: {trace.get('reason')}")

        # ── Final Aggregation ──────────────────────────────────────────────────
        pass_count = sum(1 for c in checks_performed if c.get("status") == "PASS")

        # Identity mismatch forces NEEDS_REVIEW (but not POTENTIAL_NON_COMPLIANCE)
        if has_identity_warning and has_potential_non_compliance:
            # Downgrade to NEEDS_REVIEW when identity is uncertain
            final_status = "NEEDS_REVIEW"
            confidence = 0.65
            review_reasons.insert(0, "Verdict downgraded to NEEDS_REVIEW due to unresolved identity conflict.")
        elif has_identity_warning:
            final_status = "NEEDS_REVIEW"
            confidence = 0.65
        elif has_potential_non_compliance:
            final_status = "POTENTIAL_NON_COMPLIANCE"
            confidence = 0.88
        elif has_needs_review:
            final_status = "NEEDS_REVIEW"
            confidence = 0.70
        elif pass_count == 0:
            final_status = "NEEDS_REVIEW"
            confidence = 0.55
            review_reasons.append("No statutory declarations were verified from the provided image.")
        else:
            final_status = "PASS_SCREENING"
            confidence = 0.95 if quality_status.get("status") == "ACCEPTABLE" else 0.88

        return {
            "status": final_status,
            "public_label": self.STATUS_LABELS[final_status],
            "screening_confidence": confidence,
            "checks_performed": checks_performed,
            "checks_not_performed": checks_not_performed,
            "rule_version": "2026.1",
            "review_reasons": review_reasons,
            "disclaimer": self.MANDATORY_DISCLAIMER
        }
