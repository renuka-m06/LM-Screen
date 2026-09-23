from typing import List, Dict, Any
from backend.app.models.models import ProductCluster, Scan, CitizenReport, RuleResult, ConsistencyCheck, ExtractedField

class EvidencePrioritizationEngine:
    """
    Evidence-Based Prioritization & Enforcement Intelligence Engine.
    Evaluates actual system evidence to generate explainable prioritization classifications.
    Never relies on arbitrary probabilistic risk scores.
    """
    
    VERSION = "v2.0"

    def __init__(self):
        pass

    def evaluate_cluster(
        self,
        cluster: ProductCluster,
        scans: List[Scan],
        reports: List[CitizenReport],
        rule_results: List[RuleResult],
        consistency_checks: List[ConsistencyCheck],
        evidence: List[ExtractedField]
    ) -> Dict[str, Any]:
        """
        Evaluate all evidence attached to a product cluster to determine prioritization.
        """
        reasons = []
        
        # 1. Actionability & Evidence Completeness
        actionability_state = "ACTIONABLE"
        evidence_strength = "STANDARD"
        
        # Check if we have readable images
        has_readable_evidence = any(s.quality_status in ["PASS", "GOOD", "USABLE", "UNKNOWN"] for s in scans) # UNKNOWN means we don't know it's bad
        if not has_readable_evidence and scans:
            # wait, if quality_status isn't explicitly bad, we shouldn't necessarily fail. Let's just say if all scans are POOR or UNREADABLE.
            all_bad = all(s.quality_status in ["POOR", "UNREADABLE", "BLURRY", "FAIL"] for s in scans)
            if all_bad and scans:
                actionability_state = "INSUFFICIENT_EVIDENCE"
                evidence_strength = "WEAK"
                reasons.append({
                    "code": "UNREADABLE_EVIDENCE",
                    "description": "Image quality is too poor to reliably verify identity or requirements."
                })
            
        # Check if applicable requirements were identified
        has_applicable_reqs = any(r.applicability == "REQUIRED" for r in rule_results)
        if not has_applicable_reqs and rule_results:
            reasons.append({
                "code": "NO_APPLICABLE_REQUIREMENT",
                "description": "No specific statutory requirements were confidently applied to this product."
            })
            if actionability_state != "INSUFFICIENT_EVIDENCE":
                actionability_state = "REVIEW_REQUIRED"
        elif has_applicable_reqs:
            reasons.append({
                "code": "APPLICABLE_REQUIREMENT_IDENTIFIED",
                "description": "Applicable requirements successfully identified based on product context."
            })

        # 2. Recurrence (Citizen Observations)
        report_count = len(reports)
        if report_count > 1:
            reasons.append({
                "code": "REPEATED_OBSERVATION",
                "description": f"Product referenced in {report_count} independent citizen observations."
            })
            evidence_strength = "STRONG"

        # 3. Evidence Conflict
        has_conflicts = False
        for check in consistency_checks:
            if check.status == "REVIEW_REQUIRED":
                has_conflicts = True
                reasons.append({
                    "code": "CROSS_EVIDENCE_CONFLICT",
                    "description": f"Conflict detected: {check.explanation}"
                })
                
        # Identity conflicts from scans
        has_identity_conflict = False
        for s in scans:
            if s.decision_traces:
                for t in s.decision_traces:
                    if t.stage == "IDENTITY_CHECK" and t.output_summary and t.output_summary.get("status") == "MISMATCH_DETECTED":
                        has_identity_conflict = True
                        break
        
        if has_identity_conflict:
            has_conflicts = True
            reasons.append({
                "code": "CONFLICTING_PRODUCT_IDENTITY",
                "description": "Reported product name does not match image-derived identity."
            })

        # 4. Confirmed Issues (Rule Results)
        potential_issues = [r for r in rule_results if r.status in ["POTENTIAL_NON_COMPLIANCE", "NEEDS_REVIEW"]]
        if potential_issues:
            reasons.append({
                "code": "POTENTIAL_ISSUE_DETECTED",
                "description": f"{len(potential_issues)} potential compliance issue(s) flagged by rule engine."
            })

        # 5. Officer Verified
        # Assuming manual corrections mean an officer checked it
        has_officer_corrections = any(len(e.corrections) > 0 for e in evidence) if evidence else False
        if has_officer_corrections:
            reasons.append({
                "code": "OFFICER_VERIFIED_EVIDENCE",
                "description": "Evidence contains manual officer verifications/corrections."
            })
            evidence_strength = "STRONG"

        # 6. Product Identity Confirmed
        if cluster.match_method in ["GTIN_MATCH", "DETERMINISTIC_IDENTITY_MATCH"] or cluster.match_strength == "STRONG_MATCH":
            reasons.append({
                "code": "PRODUCT_IDENTITY_CONFIRMED",
                "description": f"Product identity established via {cluster.match_method or 'known patterns'}."
            })

        # Determine Priority Class
        priority_class = "STANDARD_REVIEW"
        
        if actionability_state == "INSUFFICIENT_EVIDENCE":
            priority_class = "EVIDENCE_INSUFFICIENT"
        elif has_conflicts or len(potential_issues) > 0 or report_count >= 3 or has_officer_corrections:
            priority_class = "PRIORITY_REVIEW"

        return {
            "priority_class": priority_class,
            "priority_reasons": reasons,
            "evidence_strength": evidence_strength,
            "actionability_state": actionability_state,
            "prioritization_version": self.VERSION
        }

    def calculate_score(
        self,
        report_count: int,
        ai_flag_count: int,
        confirmed_cases: int = 0,
        evidence_quality_score: float = 0.90,
        severity_weight: float = 0.80,
        recency_score: float = 1.0,
        rejected_count: int = 0
    ) -> dict:
        """
        Calculate Operational Prioritization Score for a product cluster.
        """
        norm_reports = min(report_count / 20.0, 1.0)
        norm_ai = min(ai_flag_count / 10.0, 1.0)
        norm_confirmed = min(confirmed_cases / 5.0, 1.0)

        raw_score = (
            (0.25 * norm_reports) +
            (0.20 * norm_ai) +
            (0.20 * norm_confirmed) +
            (0.15 * evidence_quality_score) +
            (0.10 * severity_weight) +
            (0.10 * recency_score)
        )

        penalty = min(rejected_count * 0.10, 0.40)
        final_score = max(round(raw_score - penalty, 2), 0.0)

        return {
            "operational_prioritization_score": final_score,
            "components": {
                "citizen_reports_factor": round(0.25 * norm_reports, 3),
                "ai_flags_factor": round(0.20 * norm_ai, 3),
                "confirmed_signal_factor": round(0.20 * norm_confirmed, 3),
                "evidence_quality_factor": round(0.15 * evidence_quality_score, 3),
                "severity_factor": round(0.10 * severity_weight, 3),
                "recency_factor": round(0.10 * recency_score, 3),
                "rejected_penalty": round(penalty, 3)
            }
        }
