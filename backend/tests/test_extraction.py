"""
Comprehensive regression tests for LM-Screen evidence pipeline.
Tests cover: field extraction, identity mismatch, rule evaluation, verdict aggregation.
"""
import pytest
from ai.field_extractor import FieldExtractor
from ai.consistency import ConsistencyScreening
from rules.engine import DeterministicRuleEngine
from rules.verdict import VerdictAggregator


def make_token(id_, text, confidence=0.95):
    return {"id": id_, "text": text, "polygon": [], "confidence": confidence}


# ─── FieldExtractor Tests ──────────────────────────────────────────────────────

class TestMRPExtraction:
    def setup_method(self):
        self.extractor = FieldExtractor()

    def test_mrp_standard(self):
        tokens = [make_token("t1", "MRP Rs. 150.00 (Incl. of all taxes)")]
        fields = self.extractor.extract_fields(tokens)
        assert "mrp" in fields
        assert fields["mrp"]["normalized_value"] == "₹150.00"
        assert fields["mrp"]["numeric_value"] == 150.0
        assert fields["mrp"]["evidence_state"] == "PRESENT"

    def test_mrp_with_dot_notation(self):
        tokens = [make_token("t1", "M.R.P. Rs. 260.00")]
        fields = self.extractor.extract_fields(tokens)
        assert "mrp" in fields
        assert fields["mrp"]["numeric_value"] == 260.0

    def test_mrp_maximum_retail_price(self):
        tokens = [make_token("t1", "Maximum Retail Price: Rs. 99.50")]
        fields = self.extractor.extract_fields(tokens)
        assert "mrp" in fields


class TestNetQuantityExtraction:
    def setup_method(self):
        self.extractor = FieldExtractor()

    def test_net_quantity_grams(self):
        tokens = [make_token("t1", "Net Quantity: 250 g")]
        fields = self.extractor.extract_fields(tokens)
        assert "net_quantity" in fields
        assert fields["net_quantity"]["normalized_value"] == "250.0 g"
        assert fields["net_quantity"]["unit"] == "g"

    def test_net_quantity_kg(self):
        tokens = [make_token("t1", "Net Qty: 5.0 kg")]
        fields = self.extractor.extract_fields(tokens)
        assert "net_quantity" in fields
        assert fields["net_quantity"]["normalized_value"] == "5.0 kg"

    def test_net_quantity_liters(self):
        tokens = [make_token("t1", "Net Volume: 1.5 L")]
        fields = self.extractor.extract_fields(tokens)
        assert "net_quantity" in fields

    def test_net_quantity_ml(self):
        tokens = [make_token("t1", "Net Quantity: 500 ml")]
        fields = self.extractor.extract_fields(tokens)
        assert "net_quantity" in fields
        assert fields["net_quantity"]["unit"] == "mL"


class TestManufactureDateExtraction:
    """CRITICAL: Mfg Date must be detected for 'Mfg. Date: 09/2026' (with period)."""
    def setup_method(self):
        self.extractor = FieldExtractor()

    def test_mfg_date_with_period_notation(self):
        """BUG-01 regression: 'Mfg. Date: 09/2026' was not matched."""
        tokens = [make_token("t1", "Mfg. Date: 09/2026")]
        fields = self.extractor.extract_fields(tokens)
        assert "manufacture_date" in fields, "Mfg. Date with period must be extracted"
        assert fields["manufacture_date"]["normalized_value"] == "09/2026"
        assert fields["manufacture_date"]["evidence_state"] == "PRESENT"

    def test_mfd_no_period(self):
        tokens = [make_token("t1", "MFD 01/2026")]
        fields = self.extractor.extract_fields(tokens)
        assert "manufacture_date" in fields
        assert fields["manufacture_date"]["normalized_value"] == "01/2026"

    def test_mfg_by_no_period(self):
        """'MFG DATE' (no period) should still match."""
        tokens = [make_token("t1", "MFG DATE: 03/2026")]
        fields = self.extractor.extract_fields(tokens)
        assert "manufacture_date" in fields

    def test_manufactured_on(self):
        tokens = [make_token("t1", "Manufactured on: Feb 2026")]
        fields = self.extractor.extract_fields(tokens)
        assert "manufacture_date" in fields

    def test_mfg_date_month_year(self):
        tokens = [make_token("t1", "Mfg. Date: January 2026")]
        fields = self.extractor.extract_fields(tokens)
        assert "manufacture_date" in fields

    def test_no_mfg_date(self):
        """When no mfg date present, field should be absent."""
        tokens = [make_token("t1", "MRP Rs. 50.00")]
        fields = self.extractor.extract_fields(tokens)
        assert "manufacture_date" not in fields


class TestManufacturerExtraction:
    def setup_method(self):
        self.extractor = FieldExtractor()

    def test_manufactured_and_packed_by(self):
        tokens = [
            make_token("t1", "Manufactured & Packed by:"),
            make_token("t2", "ABC Foods Pvt Ltd.")
        ]
        fields = self.extractor.extract_fields(tokens)
        assert "manufacturer_or_packer" in fields
        # Must NOT be hardcoded "PureHarvest Agro" (BUG-02 regression)
        assert "PureHarvest" not in fields["manufacturer_or_packer"]["normalized_value"], \
            "BUG-02: Hardcoded fallback must not appear for non-PureHarvest images"

    def test_mfg_by_keyword(self):
        tokens = [make_token("t1", "Mfg by: XYZ Industries Noida UP")]
        fields = self.extractor.extract_fields(tokens)
        assert "manufacturer_or_packer" in fields

    def test_no_manufacturer_no_hardcode(self):
        """When no manufacturer keyword, field should be absent — no hardcoded fallback."""
        tokens = [make_token("t1", "MRP Rs. 99.00"), make_token("t2", "Net Qty 500g")]
        fields = self.extractor.extract_fields(tokens)
        # If manufacturer_or_packer appears, it MUST NOT be hardcoded
        if "manufacturer_or_packer" in fields:
            assert "PureHarvest" not in fields["manufacturer_or_packer"]["normalized_value"]


class TestConsumerCareExtraction:
    def setup_method(self):
        self.extractor = FieldExtractor()

    def test_consumer_care_phone(self):
        tokens = [make_token("t1", "Consumer Care: 1800-123-4567")]
        fields = self.extractor.extract_fields(tokens)
        assert "consumer_care" in fields
        assert "1800" in fields["consumer_care"]["normalized_value"]

    def test_call_toll_free(self):
        tokens = [make_token("t1", "Call: 1800-11-2233")]
        fields = self.extractor.extract_fields(tokens)
        assert "consumer_care" in fields

    def test_helpline_number(self):
        tokens = [make_token("t1", "Helpline: 9876543210")]
        fields = self.extractor.extract_fields(tokens)
        assert "consumer_care" in fields


class TestGSTINExtraction:
    def setup_method(self):
        self.extractor = FieldExtractor()

    def test_valid_gstin(self):
        tokens = [make_token("t1", "GSTIN: 09AAAAA1234A1Z5")]
        fields = self.extractor.extract_fields(tokens)
        assert "gstin" in fields
        assert fields["gstin"]["normalized_value"] == "09AAAAA1234A1Z5"

    def test_gstin_maharashtra(self):
        tokens = [make_token("t1", "GSTIN: 27AAABC5678D1Z4")]
        fields = self.extractor.extract_fields(tokens)
        assert "gstin" in fields


class TestGTINExtraction:
    def setup_method(self):
        self.extractor = FieldExtractor()

    def test_gtin_13_digit(self):
        tokens = [make_token("t1", "8901234567890")]
        fields = self.extractor.extract_fields(tokens)
        assert "gtin" in fields
        assert fields["gtin"]["normalized_value"] == "8901234567890"

    def test_gtin_8_digit(self):
        tokens = [make_token("t1", "12345678")]
        fields = self.extractor.extract_fields(tokens)
        assert "gtin" in fields


class TestProductNameExtraction:
    def setup_method(self):
        self.extractor = FieldExtractor()

    def test_product_name_extracted(self):
        tokens = [
            make_token("t1", "Premium Choco-Chip Biscuits"),
            make_token("t2", "Net Quantity: 250 g"),
            make_token("t3", "MRP Rs. 150.00"),
        ]
        fields = self.extractor.extract_fields(tokens)
        assert "product_name" in fields
        assert "Choco" in fields["product_name"]["normalized_value"] or \
               "Biscuits" in fields["product_name"]["normalized_value"] or \
               "Premium" in fields["product_name"]["normalized_value"]


# ─── ConsistencyScreening Tests ────────────────────────────────────────────────

class TestConsistencyScreening:
    def setup_method(self):
        self.consistency = ConsistencyScreening()

    def test_gstin_valid_format(self):
        result = self.consistency.validate_gstin("09AAAAA1234A1Z5")
        assert result["valid_format"] is True
        assert result["state_name"] == "Uttar Pradesh"

    def test_gstin_invalid_format(self):
        result = self.consistency.validate_gstin("INVALID123")
        assert result["valid_format"] is False

    def test_gstin_none(self):
        result = self.consistency.validate_gstin(None)
        assert result["status"] == "NOT_PROVIDED"

    def test_gtin_valid_checksum(self):
        """BUG-03 regression: validate_gtin was crashing with NameError."""
        result = self.consistency.validate_gtin("8901234567890")
        # Should not raise NameError; result should be a dict
        assert isinstance(result, dict)
        assert "valid_checksum" in result

    def test_gtin_none(self):
        result = self.consistency.validate_gtin(None)
        assert result["status"] == "NOT_PROVIDED"

    def test_gtin_invalid_format(self):
        result = self.consistency.validate_gtin("ABCDEF")
        assert result["status"] == "FORMAT_INVALID"

    def test_identity_mismatch_detected(self):
        """BUG-04 regression: Identity mismatch must be detected."""
        result = self.consistency.check_identity_consistency(
            user_product_name="PureHarvest Atta 5kg",
            ocr_product_name="Premium Choco-Chip Biscuits",
            user_gtin=None,
            ocr_gtin=None,
            barcode_gtin=None
        )
        assert result["has_warnings"] is True
        assert result["name_mismatch"] is True
        assert any(w["type"] == "PRODUCT_IDENTITY_MISMATCH" for w in result["warnings"])

    def test_identity_match_no_warning(self):
        result = self.consistency.check_identity_consistency(
            user_product_name="PureHarvest Atta",
            ocr_product_name="PureHarvest Atta 5kg",
            user_gtin="8901234567890",
            ocr_gtin="8901234567890",
            barcode_gtin=None
        )
        assert result["name_mismatch"] is False

    def test_gtin_mismatch_detected(self):
        result = self.consistency.check_identity_consistency(
            user_product_name=None,
            ocr_product_name=None,
            user_gtin="8901234567890",
            ocr_gtin="8909876543210",
            barcode_gtin=None
        )
        assert result["has_warnings"] is True
        assert any(w["type"] == "GTIN_CONSISTENCY_WARNING" for w in result["warnings"])


# ─── Verdict Aggregator Tests ──────────────────────────────────────────────────

class TestVerdictAggregator:
    def setup_method(self):
        self.agg = VerdictAggregator()

    def good_quality(self):
        return {"status": "ACCEPTABLE", "blur_score": 100, "brightness_score": 0.5, "glare_ratio": 0.05}

    def partial_quality(self):
        return {"status": "PARTIALLY_USABLE", "blur_score": 50, "brightness_score": 0.5, "glare_ratio": 0.1}

    def retake_quality(self):
        return {"status": "RETAKE_REQUIRED", "blur_score": 10, "brightness_score": 0.05, "glare_ratio": 0.5,
                "reasons": ["Image too blurry"]}

    def barcode_not_found(self):
        return {"status": "BARCODE_NOT_FOUND", "scale_reference_usable": False,
                "reasons": ["No barcode detected"], "gtin": None}

    def context(self):
        return {"product_category": "food"}

    def test_pass_screening(self):
        traces = [{"rule_id": "LM001", "rule_name": "MRP", "status": "PASS", "applicable": True, "confidence": 0.94,
                   "reason": "MRP found", "evidence_ids": []}]
        result = self.agg.aggregate(traces, self.good_quality(), self.barcode_not_found(), self.context())
        assert result["status"] == "PASS_SCREENING"

    def test_potential_non_compliance(self):
        traces = [{"rule_id": "LM001", "rule_name": "MRP", "status": "POTENTIAL_NON_COMPLIANCE",
                   "applicable": True, "confidence": 0.88, "reason": "MRP missing", "evidence_ids": []}]
        result = self.agg.aggregate(traces, self.good_quality(), self.barcode_not_found(), self.context())
        assert result["status"] == "POTENTIAL_NON_COMPLIANCE"

    def test_needs_review_on_poor_quality(self):
        result = self.agg.aggregate([], self.retake_quality(), self.barcode_not_found(), self.context())
        assert result["status"] == "NEEDS_REVIEW"

    def test_identity_mismatch_forces_needs_review(self):
        """Identity mismatch must DOWNGRADE from POTENTIAL_NON_COMPLIANCE to NEEDS_REVIEW."""
        traces = [{"rule_id": "LM001", "rule_name": "MRP", "status": "POTENTIAL_NON_COMPLIANCE",
                   "applicable": True, "confidence": 0.88, "reason": "MRP missing", "evidence_ids": []}]
        warnings = [{"type": "PRODUCT_IDENTITY_MISMATCH", "severity": "NEEDS_REVIEW",
                     "explanation": "Product name mismatch"}]
        result = self.agg.aggregate(traces, self.good_quality(), self.barcode_not_found(), self.context(), warnings)
        assert result["status"] == "NEEDS_REVIEW", \
            "Identity mismatch must prevent POTENTIAL_NON_COMPLIANCE from being emitted"

    def test_technical_failure_not_non_compliance(self):
        """OCR failure (no traces) must produce NEEDS_REVIEW, not POTENTIAL_NON_COMPLIANCE."""
        result = self.agg.aggregate([], self.good_quality(), self.barcode_not_found(), self.context())
        assert result["status"] in ["NEEDS_REVIEW", "PASS_SCREENING"]
        assert result["status"] != "POTENTIAL_NON_COMPLIANCE"

    def test_only_three_allowed_statuses(self):
        allowed = {"PASS_SCREENING", "POTENTIAL_NON_COMPLIANCE", "NEEDS_REVIEW"}
        for traces in [
            [],
            [{"rule_id": "LM001", "applicable": True, "status": "PASS", "confidence": 0.9, "reason": "ok", "rule_name": "X", "evidence_ids": []}],
            [{"rule_id": "LM001", "applicable": True, "status": "NEEDS_REVIEW", "confidence": 0.7, "reason": "?", "rule_name": "X", "evidence_ids": []}],
        ]:
            for quality in [self.good_quality(), self.partial_quality()]:
                result = self.agg.aggregate(traces, quality, self.barcode_not_found(), self.context())
                assert result["status"] in allowed, f"Invalid status: {result['status']}"


# ─── Integration: Full Biscuit Image Scenario ─────────────────────────────────

class TestIdentityMismatchScenario:
    """
    Regression test for the main bug report scenario:
    User: 'PureHarvest Atta 5kg' + image: 'Premium Choco-Chip Biscuits'
    """
    def setup_method(self):
        self.extractor = FieldExtractor()
        self.consistency = ConsistencyScreening()
        self.agg = VerdictAggregator()

    def test_biscuit_package_full_extraction(self):
        """All key fields from the biscuit package must be extracted correctly."""
        tokens = [
            make_token("t01", "Premium Choco-Chip Biscuits"),
            make_token("t02", "Net Quantity: 250 g"),
            make_token("t03", "MRP: Rs. 150.00 (Incl. of all taxes)"),
            make_token("t04", "Mfg. Date: 09/2026"),
            make_token("t05", "Best Before: 6 Months from Mfg Date"),
            make_token("t06", "Manufactured & Packed by:"),
            make_token("t07", "ABC Foods Pvt Ltd."),
            make_token("t08", "123 Industrial Area, Andheri East"),
            make_token("t09", "Mumbai, Maharashtra - 400093"),
            make_token("t10", "Consumer Care: 1800-123-4567"),
            make_token("t11", "GSTIN: 27AAABC5678D1Z4"),
            make_token("t12", "8901234567890"),
        ]
        fields = self.extractor.extract_fields(tokens)

        # A. Product name extracted from image
        assert "product_name" in fields

        # B. All key fields extracted
        assert "net_quantity" in fields, "Net quantity must be extracted"
        assert "mrp" in fields, "MRP must be extracted"
        assert "manufacture_date" in fields, "Mfg. Date with period must be extracted (BUG-01)"
        assert "best_before" in fields, "Best before must be extracted"
        assert "manufacturer_or_packer" in fields, "Manufacturer must be extracted"
        assert "consumer_care" in fields, "Consumer care must be extracted"
        assert "gstin" in fields, "GSTIN must be extracted"
        assert "gtin" in fields, "GTIN must be extracted"

        # C. Values are correct
        assert fields["net_quantity"]["normalized_value"] == "250.0 g"
        assert fields["mrp"]["numeric_value"] == 150.0
        assert fields["manufacture_date"]["normalized_value"] == "09/2026", \
            f"Expected 09/2026, got {fields['manufacture_date']['normalized_value']}"
        assert fields["gtin"]["normalized_value"] == "8901234567890"
        assert "1800" in fields["consumer_care"]["normalized_value"]

        # D. No hardcoded fallback
        if "manufacturer_or_packer" in fields:
            assert "PureHarvest" not in fields["manufacturer_or_packer"]["normalized_value"]

    def test_identity_mismatch_warning(self):
        """User provides PureHarvest Atta but image says Premium Choco-Chip Biscuits."""
        result = self.consistency.check_identity_consistency(
            user_product_name="PureHarvest Atta 5kg",
            ocr_product_name="Premium Choco-Chip Biscuits",
            user_gtin=None, ocr_gtin=None, barcode_gtin=None
        )
        assert result["has_warnings"] is True
        assert result["name_mismatch"] is True

    def test_mismatch_verdict_is_needs_review(self):
        """With identity mismatch, verdict must be NEEDS_REVIEW regardless of rule results."""
        warnings = [{"type": "PRODUCT_IDENTITY_MISMATCH", "severity": "NEEDS_REVIEW",
                     "explanation": "User: PureHarvest Atta 5kg vs Image: Premium Choco-Chip Biscuits"}]
        traces = [{"rule_id": "LM001", "rule_name": "MRP", "status": "PASS",
                   "applicable": True, "confidence": 0.94, "reason": "MRP found", "evidence_ids": []}]
        quality = {"status": "ACCEPTABLE", "blur_score": 100, "brightness_score": 0.5, "glare_ratio": 0.05}
        barcode = {"status": "BARCODE_NOT_FOUND", "scale_reference_usable": False,
                   "reasons": ["No barcode"], "gtin": None}
        context = {"product_category": "food"}

        result = self.agg.aggregate(traces, quality, barcode, context, warnings)
        assert result["status"] == "NEEDS_REVIEW"
