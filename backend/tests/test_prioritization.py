import pytest
from backend.app.services.prioritization import EvidencePrioritizationEngine
from backend.app.models.models import ProductCluster, Scan, CitizenReport, RuleResult, ConsistencyCheck, ExtractedField

def test_insufficient_evidence():
    engine = EvidencePrioritizationEngine()
    cluster = ProductCluster(id="C1")
    scan = Scan(id="S1", quality_status="POOR") # Unreadable
    
    result = engine.evaluate_cluster(
        cluster, [scan], [], [], [], []
    )
    
    assert result["actionability_state"] == "INSUFFICIENT_EVIDENCE"
    assert result["evidence_strength"] == "WEAK"
    assert result["priority_class"] == "EVIDENCE_INSUFFICIENT"
    assert any(r["code"] == "UNREADABLE_EVIDENCE" for r in result["priority_reasons"])

def test_standard_review():
    engine = EvidencePrioritizationEngine()
    cluster = ProductCluster(id="C1")
    scan = Scan(id="S1", quality_status="GOOD")
    rule = RuleResult(status="PASS", applicability="REQUIRED")
    
    result = engine.evaluate_cluster(
        cluster, [scan], [], [rule], [], []
    )
    
    assert result["actionability_state"] == "ACTIONABLE"
    assert result["priority_class"] == "STANDARD_REVIEW"
    assert any(r["code"] == "APPLICABLE_REQUIREMENT_IDENTIFIED" for r in result["priority_reasons"])

def test_priority_review_from_conflict():
    engine = EvidencePrioritizationEngine()
    cluster = ProductCluster(id="C1")
    scan = Scan(id="S1", quality_status="GOOD")
    check = ConsistencyCheck(status="REVIEW_REQUIRED", explanation="MRP Conflict")
    
    result = engine.evaluate_cluster(
        cluster, [scan], [], [], [check], []
    )
    
    assert result["priority_class"] == "PRIORITY_REVIEW"
    assert any(r["code"] == "CROSS_EVIDENCE_CONFLICT" for r in result["priority_reasons"])

def test_priority_review_from_recurrence():
    engine = EvidencePrioritizationEngine()
    cluster = ProductCluster(id="C1")
    scan = Scan(id="S1", quality_status="GOOD")
    report1 = CitizenReport(id="R1")
    report2 = CitizenReport(id="R2")
    report3 = CitizenReport(id="R3")
    
    result = engine.evaluate_cluster(
        cluster, [scan], [report1, report2, report3], [], [], []
    )
    
    assert result["priority_class"] == "PRIORITY_REVIEW"
    assert any(r["code"] == "REPEATED_OBSERVATION" for r in result["priority_reasons"])
