import pytest
from ai.consistency import ConsistencyScreening
from ai.contradiction_engine import ContradictionEngine

def test_critical_regression_identity_mismatch():
    """
    Mandatory regression test (Spec §9):
    User declares 'PureHarvest Atta 5kg', image contains 'Premium Choco-Chip Biscuits'.
    System must derive biscuit metadata, detect PRODUCT_IDENTITY_CONFLICT, and produce NEEDS_REVIEW.
    """
    user_declared_product = "PureHarvest Atta 5kg"
    ocr_product_name = "Premium Choco-Chip Biscuits"
    ocr_gtin = "8901234567890"

    engine = ContradictionEngine()
    report = engine.analyze_contradictions(
        scan_id="test_scan_001",
        user_product_name=user_declared_product,
        ocr_product_name=ocr_product_name,
        user_gtin=None,
        ocr_gtin=ocr_gtin,
        barcode_gtin=ocr_gtin
    )

    assert report.has_contradictions is True
    assert len(report.contradictions) == 1

    c_obj = report.contradictions[0]
    assert c_obj.type == "PRODUCT_IDENTITY_CONFLICT"
    assert c_obj.severity == "HIGH"

    # Verdict must be NEEDS_REVIEW
    assert report.suggested_verdict_override == "NEEDS_REVIEW"
    assert report.suggested_verdict_override != "POTENTIAL_NON_COMPLIANCE"
    assert report.suggested_verdict_override != "COMPLIANT"
    assert report.suggested_verdict_override != "NON-COMPLIANT"

def test_full_pipeline_regression_section_6():
    """
    Section 6 Mandatory Regression Test:
    User: PureHarvest Atta 5kg
    Image tokens contain:
      - Premium Choco-Chip Biscuits
      - Net Quantity: 250 g
      - MRP: Rs. 150.00
      - Mfg. Date: 09/2026
      - Manufactured & Packed by: ABC Foods Pvt Ltd.
      - Consumer Care: 1800-123-4567
      - GTIN: 8901234567890
      - 123 Industrial Area, Andheri East, Mumbai 400025

    Expected:
      - product_name = Premium Choco-Chip Biscuits (NOT address!)
      - net_quantity = 250 g
      - mrp = ₹150.00
      - manufacture_date = 09/2026
      - manufacturer/packer = ABC Foods Pvt Ltd.
      - consumer_care = 1800-123-4567
      - gtin = 8901234567890
      - Contradiction: PRODUCT_IDENTITY_MISMATCH / PRODUCT_IDENTITY_CONFLICT
      - Final verdict = NEEDS_REVIEW
    """
    from ai.field_extractor import FieldExtractor
    from ai.consistency import ConsistencyScreening
    from rules.engine import DeterministicRuleEngine
    from rules.verdict import VerdictAggregator

    ocr_tokens = [
        {"id": 1, "text": "Premium Choco-Chip Biscuits", "confidence": 0.96, "polygon": [[10, 10], [200, 10], [200, 40], [10, 40]]},
        {"id": 2, "text": "Net Quantity: 250 g", "confidence": 0.94, "polygon": [[10, 50], [150, 50], [150, 70], [10, 70]]},
        {"id": 3, "text": "MRP: Rs. 150.00", "confidence": 0.96, "polygon": [[10, 80], [140, 80], [140, 100], [10, 100]]},
        {"id": 4, "text": "Mfg. Date: 09/2026", "confidence": 0.92, "polygon": [[10, 110], [160, 110], [160, 130], [10, 130]]},
        {"id": 5, "text": "Manufactured & Packed by: ABC Foods Pvt Ltd.", "confidence": 0.90, "polygon": [[10, 140], [300, 140], [300, 160], [10, 160]]},
        {"id": 6, "text": "Consumer Care: 1800-123-4567", "confidence": 0.93, "polygon": [[10, 170], [250, 170], [250, 190], [10, 190]]},
        {"id": 7, "text": "GTIN: 8901234567890", "confidence": 0.97, "polygon": [[10, 200], [180, 200], [180, 220], [10, 220]]},
        {"id": 8, "text": "123 Industrial Area, Andheri East, Mumbai 400025", "confidence": 0.88, "polygon": [[10, 230], [350, 230], [350, 250], [10, 250]]}
    ]

    extractor = FieldExtractor()
    extracted = extractor.extract_fields(ocr_tokens)

    # 1. Field Extraction Verification
    assert "product_name" in extracted
    assert extracted["product_name"]["normalized_value"] == "Premium Choco-Chip Biscuits"
    assert "123 Industrial Area" not in extracted["product_name"]["normalized_value"]

    assert extracted["net_quantity"]["normalized_value"] == "250.0 g" or "250 g" in extracted["net_quantity"]["normalized_value"]
    assert extracted["mrp"]["normalized_value"] == "₹150.00"
    assert extracted["manufacture_date"]["normalized_value"] == "09/2026"
    assert extracted["manufacturer_or_packer"]["normalized_value"] == "ABC Foods Pvt Ltd."
    assert extracted["consumer_care"]["normalized_value"] == "1800-123-4567"
    assert extracted["gtin"]["normalized_value"] == "8901234567890"

    # 2. Identity Check Verification
    user_declared = "PureHarvest Atta 5kg"
    consistency = ConsistencyScreening()
    id_check = consistency.check_identity_consistency(
        user_product_name=user_declared,
        ocr_product_name=extracted["product_name"]["normalized_value"],
        user_gtin=None,
        ocr_gtin=extracted["gtin"]["normalized_value"],
        barcode_gtin=extracted["gtin"]["normalized_value"]
    )

    assert id_check["has_warnings"] is True
    assert len(id_check["warnings"]) > 0
    warning = id_check["warnings"][0]
    assert warning["type"] == "PRODUCT_IDENTITY_MISMATCH"
    assert warning["user_provided"] == "PureHarvest Atta 5kg"
    assert warning["image_evidence"] == "Premium Choco-Chip Biscuits"
    assert "123 Industrial Area" not in warning["image_evidence"]

    # 3. Rule Evaluation Verification (LM003 must PASS)
    context = {"product_category": "food", "origin": "domestic", "market_context": "retail"}
    q_status = {"status": "ACCEPTABLE"}
    rule_engine = DeterministicRuleEngine()
    traces = rule_engine.evaluate(extracted, context, q_status)

    lm003_trace = next((t for t in traces if t["rule_id"] == "LM003"), None)
    assert lm003_trace is not None
    assert lm003_trace["status"] == "PASS"

    # 4. Verdict Aggregation Verification
    aggregator = VerdictAggregator()
    verdict = aggregator.aggregate(
        rule_traces=traces,
        quality_status=q_status,
        barcode_status={"scale_reference_usable": False},
        context=context,
        identity_warnings=id_check["warnings"]
    )

    assert verdict["status"] == "NEEDS_REVIEW"
    assert verdict["public_label"] == "More evidence or human review required"
    assert verdict["status"] != "POTENTIAL_NON_COMPLIANCE"
    assert verdict["status"] != "COMPLIANT"
    assert verdict["status"] != "NON-COMPLIANT"

