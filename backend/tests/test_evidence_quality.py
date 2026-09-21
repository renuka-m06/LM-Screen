import pytest
from ai.evidence_quality import EvidenceQualityEvaluator

def test_evidence_quality_unreadable():
    evaluator = EvidenceQualityEvaluator()
    
    evidence_list = [
        {"field": "mrp", "value": 150.0, "found": True, "ocr_evidence_ids": [1]}
    ]
    ocr_tokens = [{"id": 1, "confidence": 0.9}]
    image_quality = {"usable": False, "status": "RETAKE_REQUIRED"}
    
    result = evaluator.evaluate_evidence(evidence_list, ocr_tokens, image_quality, [], {})
    assert result[0]["evidence_state"] == "UNREADABLE"
    assert "Overall image quality is too poor" in result[0]["quality_reasons"][0]

def test_evidence_quality_uncertain_ocr():
    evaluator = EvidenceQualityEvaluator()
    
    evidence_list = [
        {"field": "net_quantity", "value": "500g", "found": True, "ocr_evidence_ids": [1]}
    ]
    ocr_tokens = [{"id": 1, "confidence": 0.4}] # Low confidence
    image_quality = {"usable": True, "status": "ACCEPTABLE"}
    
    result = evaluator.evaluate_evidence(evidence_list, ocr_tokens, image_quality, [], {})
    assert result[0]["evidence_state"] == "UNCERTAIN"
    assert "Low OCR model confidence" in result[0]["quality_reasons"][0]

def test_evidence_quality_conflicting():
    evaluator = EvidenceQualityEvaluator()
    
    evidence_list = [
        {"field": "mrp", "value": 150.0, "found": True, "ocr_evidence_ids": [1]},
        {"field": "net_quantity", "value": "500g", "found": True, "ocr_evidence_ids": [2]},
        {"field": "unit_sale_price", "value": 500.0, "found": True, "ocr_evidence_ids": [3]}
    ]
    ocr_tokens = [{"id": 1, "confidence": 0.9}, {"id": 2, "confidence": 0.9}, {"id": 3, "confidence": 0.9}]
    image_quality = {"usable": True, "status": "ACCEPTABLE"}
    
    consistency_checks = [
        {
            "check_type": "MRP_QTY_USP_CONSISTENCY",
            "status": "INCONSISTENT",
            "explanation": "Arithmetic mismatch.",
            "observed_values": {"mrp": 150, "net_quantity": "500g", "unit_sale_price": 500}
        }
    ]
    
    result = evaluator.evaluate_evidence(evidence_list, ocr_tokens, image_quality, consistency_checks, {})
    assert result[0]["evidence_state"] == "CONFLICTING"
    assert result[1]["evidence_state"] == "CONFLICTING"
    assert result[2]["evidence_state"] == "CONFLICTING"

def test_evidence_quality_supported():
    evaluator = EvidenceQualityEvaluator()
    
    evidence_list = [
        {"field": "product_name", "value": "Test Product", "found": True, "ocr_evidence_ids": [1]}
    ]
    ocr_tokens = [{"id": 1, "confidence": 0.95}]
    image_quality = {"usable": True, "status": "ACCEPTABLE"}
    
    result = evaluator.evaluate_evidence(evidence_list, ocr_tokens, image_quality, [], {})
    assert result[0]["evidence_state"] == "SUPPORTED"
    assert "OCR token confidence is acceptable." in result[0]["quality_reasons"]
