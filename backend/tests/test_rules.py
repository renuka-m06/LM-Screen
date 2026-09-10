import pytest
from rules.engine import DeterministicRuleEngine
from rules.verdict import VerdictAggregator

def test_rule_engine_pass():
    engine = DeterministicRuleEngine()
    extracted_fields = {
        "mrp": {"field_name": "mrp", "raw_value": "20", "normalized_value": "₹ 20.00", "ocr_evidence_ids": ["t1"]},
        "net_quantity": {"field_name": "net_quantity", "raw_value": "100g", "normalized_value": "100 g", "ocr_evidence_ids": ["t2"]},
        "manufacture_date": {"field_name": "manufacture_date", "raw_value": "01/2026", "normalized_value": "01/2026", "ocr_evidence_ids": ["t3"]}
    }
    context = {"product_category": "general", "origin": "domestic"}
    quality_status = {"status": "ACCEPTABLE", "blur_score": 120.0}

    traces = engine.evaluate(extracted_fields, context, quality_status)
    assert len(traces) > 0
    mrp_trace = next(t for t in traces if t["rule_id"] == "LM001")
    assert mrp_trace["status"] == "PASS"

def test_rule_engine_potential_non_compliance():
    engine = DeterministicRuleEngine()
    extracted_fields = {
        "net_quantity": {"field_name": "net_quantity", "raw_value": "100g", "normalized_value": "100 g"}
    }
    context = {"product_category": "general", "origin": "domestic"}
    quality_status = {"status": "ACCEPTABLE", "blur_score": 120.0}

    traces = engine.evaluate(extracted_fields, context, quality_status)
    mrp_trace = next(t for t in traces if t["rule_id"] == "LM001")
    assert mrp_trace["status"] == "POTENTIAL_NON_COMPLIANCE"

def test_verdict_aggregator_three_states():
    aggregator = VerdictAggregator()
    quality = {"status": "ACCEPTABLE"}
    barcode = {"scale_reference_usable": True}
    context = {"context_confidence": 0.95}

    # Pass
    res_pass = aggregator.aggregate([{"rule_id": "LM001", "status": "PASS", "applicable": True}], quality, barcode, context)
    assert res_pass["status"] == "PASS_SCREENING"
    assert res_pass["public_label"] == "No issue detected in the checks performed"

    # Potential non-compliance
    res_pot = aggregator.aggregate([{"rule_id": "LM001", "status": "POTENTIAL_NON_COMPLIANCE", "reason": "MRP missing", "applicable": True}], quality, barcode, context)
    assert res_pot["status"] == "POTENTIAL_NON_COMPLIANCE"
    assert res_pot["public_label"] == "Potential non-compliance detected"

    # Retake required / Needs review
    quality_blurry = {"status": "RETAKE_REQUIRED", "reasons": ["Image blurry"]}
    res_review = aggregator.aggregate([], quality_blurry, barcode, context)
    assert res_review["status"] == "NEEDS_REVIEW"
    assert res_review["public_label"] == "More evidence or human review required"
