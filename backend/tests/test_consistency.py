import pytest
from ai.consistency_engine import ConsistencyEngine

def test_mrp_qty_usp_consistent():
    engine = ConsistencyEngine()
    
    extracted_fields = [
        {"field": "mrp", "value": "₹120", "ocr_evidence_ids": ["1"]},
        {"field": "net_quantity", "value": "500 g", "ocr_evidence_ids": ["2"]},
        {"field": "unit_sale_price", "value": "₹240/kg", "ocr_evidence_ids": ["3"]}
    ]
    
    checks = engine.evaluate(extracted_fields, {}, {})
    mrp_check = next((c for c in checks if c["check_type"] == "MRP_QTY_USP_CONSISTENCY"), None)
    
    assert mrp_check is not None
    assert mrp_check["status"] == "CONSISTENT"
    assert "₹240.00/kg" in mrp_check["calculated_value"]

def test_mrp_qty_usp_inconsistent():
    engine = ConsistencyEngine()
    
    extracted_fields = [
        {"field": "mrp", "value": "₹120", "ocr_evidence_ids": ["1"]},
        {"field": "net_quantity", "value": "500 g", "ocr_evidence_ids": ["2"]},
        {"field": "unit_sale_price", "value": "₹260/kg", "ocr_evidence_ids": ["3"]}
    ]
    
    checks = engine.evaluate(extracted_fields, {}, {})
    mrp_check = next((c for c in checks if c["check_type"] == "MRP_QTY_USP_CONSISTENCY"), None)
    
    assert mrp_check is not None
    assert mrp_check["status"] == "REVIEW_REQUIRED"

def test_barcode_ocr_gtin_consistent():
    engine = ConsistencyEngine()
    
    extracted_fields = [
        {"field": "gtin", "value": "8901234567890", "ocr_evidence_ids": ["1"]}
    ]
    barcode_result = {"decoded_data": "8901234567890"}
    
    checks = engine.evaluate(extracted_fields, barcode_result, {})
    barcode_check = next((c for c in checks if c["check_type"] == "BARCODE_OCR_CONSISTENCY"), None)
    
    assert barcode_check is not None
    assert barcode_check["status"] == "CONSISTENT"

def test_barcode_ocr_gtin_inconsistent():
    engine = ConsistencyEngine()
    
    extracted_fields = [
        {"field": "gtin", "value": "8901234567890", "ocr_evidence_ids": ["1"]}
    ]
    barcode_result = {"decoded_data": "8901234567891"}
    
    checks = engine.evaluate(extracted_fields, barcode_result, {})
    barcode_check = next((c for c in checks if c["check_type"] == "BARCODE_OCR_CONSISTENCY"), None)
    
    assert barcode_check is not None
    assert barcode_check["status"] == "REVIEW_REQUIRED"

def test_field_duplicates_conflict():
    engine = ConsistencyEngine()
    
    extracted_fields = [
        {"field": "mrp", "value": "₹120", "ocr_evidence_ids": ["1"]},
        {"field": "mrp", "value": "₹150", "ocr_evidence_ids": ["2"]}
    ]
    
    checks = engine.evaluate(extracted_fields, {}, {})
    conflict_check = next((c for c in checks if c["check_type"] == "DUPLICATE_FIELD_CONFLICT"), None)
    
    assert conflict_check is not None
    assert conflict_check["status"] == "REVIEW_REQUIRED"
    assert "mrp" in conflict_check["observed_values"]["Conflicting Fields"]

def test_insufficient_evidence():
    engine = ConsistencyEngine()
    
    extracted_fields = [
        {"field": "mrp", "value": "₹120", "ocr_evidence_ids": ["1"]}
    ]
    
    checks = engine.evaluate(extracted_fields, {}, {})
    mrp_check = next((c for c in checks if c["check_type"] == "MRP_QTY_USP_CONSISTENCY"), None)
    
    assert mrp_check is not None
    assert mrp_check["status"] == "INSUFFICIENT_EVIDENCE"
