import pytest
from ai.evidence_graph import EvidenceGraphBuilder
from ai.evidence_passport import EvidencePassportGenerator
from ai.copilot import OfficerEvidenceCopilot, CopilotRequest

def test_evidence_graph_builder():
    builder = EvidenceGraphBuilder()
    mock_scan_data = {
        "scan_id": "SCAN_1001",
        "status": "PASS_SCREENING",
        "public_label": "No issue detected in the checks performed",
        "screening_confidence": 0.95,
        "rule_version": "2026.1",
        "quality": {"status": "ACCEPTABLE", "blur_score": 140.0},
        "ocr_tokens": [
            {"token_id": "1", "text": "MRP Rs. 150.00", "confidence": 0.96, "polygon": [[10, 10], [100, 10], [100, 30], [10, 30]]}
        ],
        "extracted_fields": {
            "mrp": {"raw_value": "MRP Rs. 150.00", "normalized_value": "₹150.00", "confidence": 0.96, "ocr_evidence_ids": ["1"], "extraction_method": "REGEX_PATTERN"}
        },
        "checks_performed": [
            {"rule_id": "LM001", "rule_name": "MRP Declaration Screening", "status": "PASS", "confidence": 0.96, "reason": "MRP declaration present"}
        ]
    }

    graph = builder.build_graph(mock_scan_data)
    assert graph.scan_id == "SCAN_1001"
    assert len(graph.nodes) >= 5
    assert len(graph.edges) >= 4
    node_types = {n.type for n in graph.nodes}
    assert "IMAGE_QUALITY" in node_types
    assert "OCR_TOKEN" in node_types
    assert "FIELD" in node_types
    assert "RULE" in node_types
    assert "VERDICT" in node_types

def test_evidence_passport_generator():
    gen = EvidencePassportGenerator()
    mock_scan_data = {
        "scan_id": "SCAN_2002",
        "image_hash": "a" * 64,
        "status": "NEEDS_REVIEW",
        "public_label": "More evidence or human review required",
        "screening_confidence": 0.60,
        "rule_version": "2026.1",
        "quality": {"status": "RETAKE_REQUIRED"},
        "extracted_fields": {},
        "contradictions": []
    }

    passport = gen.generate_passport(mock_scan_data)
    assert passport.scan_id == "SCAN_2002"
    assert passport.passport_id.startswith("PASS-")
    assert len(passport.passport_signature_hash) == 64
    assert passport.provenance_versions["rule_profile_version"] == "2026.1"

def test_officer_copilot():
    copilot = OfficerEvidenceCopilot()
    req = CopilotRequest(scan_id="SCAN_3003", question="Why is this case prioritized?")
    res = copilot.answer_question(req)

    assert "prioritized" in res.answer.lower() or "score" in res.answer.lower()
    assert len(res.grounded_evidence) > 0
    assert "does not issue legal verdicts" in res.disclaimer.lower()
