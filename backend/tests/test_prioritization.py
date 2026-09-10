import pytest
from backend.app.services.prioritization import PrioritizationEngine

def test_prioritization_score():
    engine = PrioritizationEngine()
    res = engine.calculate_score(report_count=10, ai_flag_count=5)
    score = res["operational_prioritization_score"]
    assert 0.0 <= score <= 1.0
    assert "citizen_reports_factor" in res["components"]
