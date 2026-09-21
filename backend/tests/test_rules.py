import pytest
from rules.engine import DeterministicRuleEngine
from rules.verdict import VerdictAggregator

def test_rule_engine_common_profile():
    engine = DeterministicRuleEngine()
    extracted_fields = {
        "product_name": {"field_name": "product_name"},
        "manufacturer": {"field_name": "manufacturer"},
        "address": {"field_name": "address"},
        "net_quantity": {"field_name": "net_quantity"},
        "mrp": {"field_name": "mrp"},
        "consumer_care": {"field_name": "consumer_care"},
    }
    context = {"product_category": "general", "origin": "domestic"}
    quality_status = {"status": "ACCEPTABLE"}

    traces = engine.evaluate(extracted_fields, context, quality_status)
    assert len(traces) == 6
    for t in traces:
        assert t["status"] == "PASS"

def test_rule_engine_food_profile():
    engine = DeterministicRuleEngine()
    extracted_fields = {
        "product_name": {"field_name": "product_name"},
        "batch_number": {"field_name": "batch_number"}
    }
    context = {"product_category": "food", "origin": "domestic"}
    quality_status = {"status": "ACCEPTABLE"}

    traces = engine.evaluate(extracted_fields, context, quality_status)
    assert len(traces) > 6 # common + food
    
    batch_trace = next(t for t in traces if t["field"] == "batch_number")
    assert batch_trace["status"] == "PASS"
    assert batch_trace["applicability"] == "REQUIRED"

    mrp_trace = next(t for t in traces if t["field"] == "mrp")
    assert mrp_trace["status"] == "MISSING"

def test_rule_engine_imported_product():
    engine = DeterministicRuleEngine()
    extracted_fields = {}
    context = {"product_category": "general", "origin": "imported"}
    quality_status = {"status": "ACCEPTABLE"}

    traces = engine.evaluate(extracted_fields, context, quality_status)
    
    coo_trace = next(t for t in traces if t["field"] == "country_of_origin")
    assert coo_trace["status"] == "MISSING"

def test_rule_engine_textile_dimensions():
    engine = DeterministicRuleEngine()
    extracted_fields = {}
    context = {"product_category": "textile", "origin": "domestic"}
    quality_status = {"status": "ACCEPTABLE"}

    traces = engine.evaluate(extracted_fields, context, quality_status)
    
    dim_trace = next(t for t in traces if t["field"] == "dimensions")
    assert dim_trace["status"] == "MISSING"

def test_rule_engine_poor_image_quality():
    engine = DeterministicRuleEngine()
    extracted_fields = {}
    context = {"product_category": "general", "origin": "domestic"}
    quality_status = {"status": "RETAKE_REQUIRED"}

    traces = engine.evaluate(extracted_fields, context, quality_status)
    
    mrp_trace = next(t for t in traces if t["field"] == "mrp")
    assert mrp_trace["status"] == "REVIEW_REQUIRED" # No false positives when quality is poor

def test_rule_engine_unknown_category():
    engine = DeterministicRuleEngine()
    extracted_fields = {}
    context = {"product_category": "CONTEXT_REVIEW_REQUIRED", "origin": "domestic"}
    quality_status = {"status": "ACCEPTABLE"}

    traces = engine.evaluate(extracted_fields, context, quality_status)
    assert len(traces) == 1
    assert traces[0]["status"] == "REVIEW_REQUIRED"
    assert traces[0]["field"] == "context"
