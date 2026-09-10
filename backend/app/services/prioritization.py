class PrioritizationEngine:
    """
    Operational Prioritization Scoring Engine for LM-Screen.
    Formula:
      priority = 
          0.25 * normalized_unique_citizen_reports
        + 0.20 * normalized_ai_flags
        + 0.20 * confirmed_case_signal
        + 0.15 * evidence_quality
        + 0.10 * severity_weight
        + 0.10 * recency
        - rejected_signal_penalty

    Label: Operational Prioritization Score (Never 'Probability of Guilt')
    """
    def __init__(
        self,
        w_reports: float = 0.25,
        w_ai: float = 0.20,
        w_confirmed: float = 0.20,
        w_quality: float = 0.15,
        w_severity: float = 0.10,
        w_recency: float = 0.10
    ):
        self.w_reports = w_reports
        self.w_ai = w_ai
        self.w_confirmed = w_confirmed
        self.w_quality = w_quality
        self.w_severity = w_severity
        self.w_recency = w_recency

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
        # Normalize report count (cap at 20)
        norm_reports = min(report_count / 20.0, 1.0)
        norm_ai = min(ai_flag_count / 10.0, 1.0)
        norm_confirmed = min(confirmed_cases / 5.0, 1.0)

        raw_score = (
            (self.w_reports * norm_reports) +
            (self.w_ai * norm_ai) +
            (self.w_confirmed * norm_confirmed) +
            (self.w_quality * evidence_quality_score) +
            (self.w_severity * severity_weight) +
            (self.w_recency * recency_score)
        )

        penalty = min(rejected_count * 0.10, 0.40)
        final_score = max(round(raw_score - penalty, 2), 0.0)

        return {
            "operational_prioritization_score": final_score,
            "components": {
                "citizen_reports_factor": round(self.w_reports * norm_reports, 3),
                "ai_flags_factor": round(self.w_ai * norm_ai, 3),
                "confirmed_signal_factor": round(self.w_confirmed * norm_confirmed, 3),
                "evidence_quality_factor": round(self.w_quality * evidence_quality_score, 3),
                "severity_factor": round(self.w_severity * severity_weight, 3),
                "recency_factor": round(self.w_recency * recency_score, 3),
                "rejected_penalty": round(penalty, 3)
            }
        }
