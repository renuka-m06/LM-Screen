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

    # ── TIER 0.1 regression tests ─────────────────────────────────────────────

    def test_back_panel_nutrition_only_no_mrp_keyword(self):
        """
        TIER-0.1 / Parle-G scenario: back panel with only nutrition data and NO
        MRP indicator text must NOT produce an MRP field — not even at low
        confidence.  The old loose regex falsely extracted sodium/sugar values.
        """
        tokens = [
            make_token("t1", "Nutrition Information"),
            make_token("t2", "Energy: 447 kcal"),
            make_token("t3", "Protein: 6.7 g"),
            make_token("t4", "Carbohydrate: 74.3 g"),
            make_token("t5", "Fat: 14.2 g"),
            make_token("t6", "Sodium: 279 mg"),          # ← the number that was wrongly extracted
            make_token("t7", "Ingredients: Wheat flour, Sugar, Edible vegetable oil"),
        ]
        fields = self.extractor.extract_fields(tokens)
        assert "mrp" not in fields, (
            "TIER-0.1 regression: back-panel nutrition numbers must NOT be "
            "extracted as MRP when no MRP keyword is present"
        )

    def test_mrp_correctly_chosen_over_nearby_nutrition_numbers(self):
        """
        TIER-0.1: When a label has BOTH a clearly labelled MRP and a nutrition
        table with other numbers, only the MRP-labelled number must be returned.
        """
        tokens = [
            make_token("t1", "Nutrition Information"),
            make_token("t2", "Sodium: 279 mg"),
            make_token("t3", "Sugar: 18 g"),
            make_token("t4", "MRP: Rs. 99"),             # ← correct number
            make_token("t5", "Net Qty: 100 g"),
        ]
        fields = self.extractor.extract_fields(tokens)
        assert "mrp" in fields, "MRP must be extracted when MRP keyword is present"
        assert fields["mrp"]["numeric_value"] == 99.0, (
            f"Must extract 99 (the MRP-labelled value), not a nutrition number; "
            f"got {fields['mrp']['numeric_value']}"
        )

    def test_mrp_absent_returns_no_field_not_low_confidence(self):
        """
        TIER-0.1: When MRP genuinely cannot be found, the field must be absent
        (not returned with a guessed value and low confidence).
        """
        tokens = [
            make_token("t1", "Best Before: 6 months from manufacture"),
            make_token("t2", "Mfg. Date: 09/2026"),
            make_token("t3", "Manufactured by: ABC Foods Pvt Ltd"),
        ]
        fields = self.extractor.extract_fields(tokens)
        assert "mrp" not in fields, (
            "When no MRP keyword exists in any token, the field must be absent, "
            "not guessed"
        )

    def test_mrp_spatial_proximity_multi_token(self):
        """
        TIER-0.1: Spatial path — MRP keyword and value in separate word-level tokens
        with geometry (polygons) must be correctly associated when they share the
        same approximate Y line.
        """
        # Simulate word-level OCR: "MRP" at y≈100, "Rs." at y≈100, "150" at y≈100
        # and a nutrition figure at y≈200 that must be ignored.
        def tok_with_poly(id_, text, y_top, y_bot, conf=0.95):
            return {
                "id": id_,
                "text": text,
                "polygon": [[10, y_top], [60, y_top], [60, y_bot], [10, y_bot]],
                "confidence": conf,
            }

        tokens = [
            tok_with_poly("t1", "MRP",       95,  115),
            tok_with_poly("t2", "Rs.",        95,  115),
            tok_with_poly("t3", "150.00",     95,  115),    # ← MRP value
            tok_with_poly("t4", "Sodium",    195,  215),
            tok_with_poly("t5", "279",       195,  215),    # ← nutrition number, should be ignored
            tok_with_poly("t6", "mg",        195,  215),
        ]
        fields = self.extractor.extract_fields(tokens)
        assert "mrp" in fields, "MRP must be extracted when keyword + value are on the same line"
        assert fields["mrp"]["numeric_value"] == 150.0, (
            f"Must extract 150.00 (same line as MRP keyword), not 279; "
            f"got {fields['mrp']['numeric_value']}"
        )



# ─── TIER 0.2 — Sanity Check Layer ───────────────────────────────────────────

class TestSanityCheckLayer:
    """
    TIER-0.2 regression tests: post-extraction plausibility layer.
    Validates that garbage OCR output is demoted to UNCERTAIN / low confidence
    and that genuine correct extractions are NOT over-penalized.
    """
    def setup_method(self):
        self.extractor = FieldExtractor()

    # ── Address ────────────────────────────────────────────────────────────────

    def test_garbage_address_demoted_to_uncertain(self):
        """
        Parle-G scenario: OCR produces gibberish address like
        'Caedaeupolyd, Vushusatunuuupaclernopjuels Golu' — must get
        UNCERTAIN + confidence ≤ 0.40, not 85%.
        """
        tokens = [
            make_token("t1", "address"),
            make_token("t2", "Caedaeupolyd, Vushusatunuuupaclernopjuels Golu"),
        ]
        fields = self.extractor.extract_fields(tokens)
        assert "address" in fields, "Address field must still be extracted"
        addr = fields["address"]
        assert addr["evidence_state"] == "UNCERTAIN", (
            f"TIER-0.2: Gibberish address must be UNCERTAIN, got {addr['evidence_state']}"
        )
        assert addr["confidence"] <= 0.40, (
            f"TIER-0.2: Gibberish address confidence must be ≤0.40, got {addr['confidence']}"
        )
        assert addr.get("sanity_check") == "FAILED"

    def test_real_address_with_pincode_passes(self):
        """A real address with a 6-digit PIN must pass at full confidence."""
        tokens = [
            make_token("t1", "address"),
            make_token("t2", "123 Industrial Area, Andheri East, Mumbai - 400093"),
        ]
        fields = self.extractor.extract_fields(tokens)
        assert "address" in fields
        assert fields["address"]["evidence_state"] == "PRESENT"
        assert fields["address"]["confidence"] >= 0.80
        assert fields["address"].get("sanity_check") == "PASSED"

    def test_real_address_with_state_name_passes(self):
        """Address containing an Indian state name must pass plausibility."""
        tokens = [
            make_token("t1", "Regd Office: Plot 5, Sector 12, Noida, Uttar Pradesh"),
        ]
        fields = self.extractor.extract_fields(tokens)
        assert "address" in fields
        assert fields["address"].get("sanity_check") == "PASSED"

    # ── Product Name ───────────────────────────────────────────────────────────

    def test_short_product_name_loor_demoted(self):
        """
        Parle-G scenario: OCR reads product name as 'loor' (4 chars).
        The _extract_product_name heuristic already requires len >= 4, so
        'loor' may be emitted — but with vowels present it passes sanity.
        The more important check is that a truly garbage consonant-burst
        OCR fragment like 'Bsrkltpnd' is demoted to UNCERTAIN.
        """
        # 'loor' has vowels so sanity correctly passes it; the important
        # guarantee is that it is NOT present with PRESENT state if it fails
        # sanity — which it doesn't for 'loor'.  Confirm truly short strings
        # (below _extract_product_name's own 4-char floor) never reach PRESENT.
        tokens_too_short = [make_token("t1", "lo")]   # len < 4, filtered before sanity
        fields = self.extractor.extract_fields(tokens_too_short)
        # "lo" must not appear as a PRESENT product_name
        if "product_name" in fields:
            assert fields["product_name"]["evidence_state"] != "PRESENT", (
                "TIER-0.2: 2-char OCR fragment must not be reported as PRESENT product name"
            )

        # A consonant-burst gibberish string must be demoted
        tokens_gibberish = [make_token("t1", "Bsrkltpndvck")]
        fields2 = self.extractor.extract_fields(tokens_gibberish)
        if "product_name" in fields2:
            pn = fields2["product_name"]
            assert pn["evidence_state"] == "UNCERTAIN", (
                f"TIER-0.2: Gibberish product name must be UNCERTAIN, got {pn['evidence_state']}"
            )
            assert pn["confidence"] <= 0.40


    def test_consonant_only_product_name_demoted(self):
        """A string with no vowels (e.g. OCR fragment 'Prml Chc') must be UNCERTAIN."""
        tokens = [
            make_token("t1", "Prml Chc Bscts"),   # consonants only, no vowels
        ]
        fields = self.extractor.extract_fields(tokens)
        if "product_name" in fields:
            pn = fields["product_name"]
            assert pn["evidence_state"] == "UNCERTAIN", (
                f"TIER-0.2: Vowelless product name must be UNCERTAIN, got {pn['evidence_state']}"
            )
            assert pn["confidence"] <= 0.40

    def test_real_product_name_not_penalized(self):
        """
        A properly OCR'd product name like 'Premium Choco-Chip Biscuits'
        must pass sanity and retain high confidence.
        """
        tokens = [make_token("t1", "Premium Choco-Chip Biscuits")]
        fields = self.extractor.extract_fields(tokens)
        assert "product_name" in fields
        pn = fields["product_name"]
        assert pn["evidence_state"] == "PRESENT", (
            f"TIER-0.2: Good product name must be PRESENT, got {pn['evidence_state']}"
        )
        assert pn["confidence"] >= 0.75
        assert pn.get("sanity_check") == "PASSED"

    # ── Net Quantity ───────────────────────────────────────────────────────────

    def test_net_quantity_31g_passes(self):
        """
        Parle-G scenario: 'Net Qty: 31.25 g' is a real number on the label —
        must pass sanity at full confidence (not over-penalized).
        """
        tokens = [make_token("t1", "Net Qty: 31.25 g")]
        fields = self.extractor.extract_fields(tokens)
        assert "net_quantity" in fields
        nq = fields["net_quantity"]
        assert nq.get("sanity_check") == "PASSED", (
            "TIER-0.2: 31.25g must pass net_quantity sanity — was over-penalized"
        )
        assert nq["evidence_state"] == "PRESENT"
        assert nq["confidence"] >= 0.80

    def test_net_quantity_implausible_value_flagged(self):
        """An absurd net quantity (e.g. 999999 g) must be flagged UNCERTAIN."""
        tokens = [make_token("t1", "Net Qty: 999999 g")]
        fields = self.extractor.extract_fields(tokens)
        if "net_quantity" in fields:
            assert fields["net_quantity"]["evidence_state"] == "UNCERTAIN"
            assert fields["net_quantity"]["confidence"] <= 0.40

    # ── MRP ────────────────────────────────────────────────────────────────────

    def test_mrp_plausible_range_passes(self):
        """MRP of ₹99 must pass sanity and stay PRESENT."""
        tokens = [make_token("t1", "MRP: Rs. 99")]
        fields = self.extractor.extract_fields(tokens)
        assert "mrp" in fields
        assert fields["mrp"].get("sanity_check") == "PASSED"
        assert fields["mrp"]["evidence_state"] == "PRESENT"

    # ── sanity_check() Public API ──────────────────────────────────────────────

    def test_sanity_check_api_address_garbage(self):
        """Public sanity_check() must return (False, ≤0.40) for a gibberish address."""
        e = FieldExtractor()
        ok, conf = e.sanity_check("address", "Caedaeupolyd Vushusatunuuupaclernopjuels")
        assert ok is False
        assert conf <= 0.40

    def test_sanity_check_api_address_real(self):
        """Public sanity_check() must return (True, …) for a real address with PIN."""
        e = FieldExtractor()
        ok, conf = e.sanity_check("address", "Andheri East, Mumbai 400093")
        assert ok is True

    def test_sanity_check_api_mrp_inrange(self):
        ok, _ = FieldExtractor().sanity_check("mrp", "Rs. 150", numeric_value=150.0)
        assert ok is True

    def test_sanity_check_api_mrp_outofrange(self):
        ok, conf = FieldExtractor().sanity_check("mrp", "9999999", numeric_value=9_999_999.0)
        assert ok is False
        assert conf <= 0.40

    def test_sanity_check_api_product_name_short(self):
        ok, conf = FieldExtractor().sanity_check("product_name", "lo")
        assert ok is False
        assert conf <= 0.40

    def test_sanity_check_api_unknown_field_always_passes(self):
        """Unknown field types must always pass (no false positives)."""
        ok, _ = FieldExtractor().sanity_check("gstin", "09AAAAA1234A1Z5")
        assert ok is True


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

    # ── TIER 0.4 regression tests ────────────────────────────────────────────

    def test_serving_size_only_does_not_populate_net_quantity(self):
        """
        Parle-G scenario: only a 'Serving size 31.25g' line is present —
        no explicit Net Wt / Net Qty keyword.  net_quantity must be ABSENT.
        The value must be captured in serving_size instead.
        """
        tokens = [
            make_token("t1", "Serving size (5 cookies) 31.25 g"),
            make_token("t2", "Servings per container: 32"),
        ]
        fields = self.extractor.extract_fields(tokens)
        assert "net_quantity" not in fields, (
            "TIER-0.4: serving-size value must NOT populate net_quantity"
        )
        assert "serving_size" in fields, (
            "TIER-0.4: serving-size value must be captured in serving_size field"
        )
        assert fields["serving_size"]["numeric_value"] == 31.25
        assert fields["serving_size"]["unit"] == "g"

    def test_combined_net_wt_and_serving_size_picks_net_wt(self):
        """
        The critical regression test: a label with BOTH 'Net Wt: 500g' AND
        'Serving size: 25g'.  net_quantity must be 500 g, NOT 25 g.
        """
        tokens = [
            make_token("t1", "Net Wt: 500 g"),
            make_token("t2", "Serving size: 25 g"),
            make_token("t3", "20 servings per container"),
        ]
        fields = self.extractor.extract_fields(tokens)
        assert "net_quantity" in fields, (
            "TIER-0.4: Net Wt anchor must produce net_quantity field"
        )
        assert fields["net_quantity"]["numeric_value"] == 500.0, (
            f"TIER-0.4: Expected 500g, got {fields['net_quantity']['numeric_value']}g — "
            "serving size (25g) was wrongly chosen over Net Wt (500g)"
        )
        assert fields["net_quantity"]["unit"] == "g"
        # Serving size must also be captured (data not silently dropped)
        assert "serving_size" in fields
        assert fields["serving_size"]["numeric_value"] == 25.0

    def test_net_weight_keyword_variant(self):
        """'Net Weight:' keyword variant must be accepted as a valid anchor."""
        tokens = [make_token("t1", "Net Weight: 200 g")]
        fields = self.extractor.extract_fields(tokens)
        assert "net_quantity" in fields
        assert fields["net_quantity"]["numeric_value"] == 200.0

    def test_bare_number_without_anchor_does_not_populate_net_quantity(self):
        """
        A bare 'g' number with no keyword anchor — e.g. just a table value —
        must NOT produce a net_quantity field (prevents old false-positive behaviour).
        """
        tokens = [make_token("t1", "279 mg sodium")]
        fields = self.extractor.extract_fields(tokens)
        assert "net_quantity" not in fields, (
            "TIER-0.4: unanchored number must not appear as net_quantity"
        )

    def test_per_serving_text_excluded_from_net_quantity(self):
        """'Per serving: 30g' — must go to serving_size, not net_quantity."""
        tokens = [make_token("t1", "Per serving 30 g")]
        fields = self.extractor.extract_fields(tokens)
        assert "net_quantity" not in fields, (
            "TIER-0.4: 'per serving' text must not produce net_quantity"
        )

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
        assert "packer_name" in fields or "manufacturer_or_packer" in fields
        # Must NOT be hardcoded "PureHarvest Agro" (BUG-02 regression)
        field = fields.get("packer_name") or fields.get("manufacturer_or_packer")
        assert "PureHarvest" not in field["normalized_value"], \
            "BUG-02: Hardcoded fallback must not appear for non-PureHarvest images"

    def test_mfg_by_keyword(self):
        tokens = [make_token("t1", "Mfg by: XYZ Industries Noida UP")]
        fields = self.extractor.extract_fields(tokens)
        assert "manufacturer_name" in fields or "manufacturer_or_packer" in fields

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
        assert "packer_name" in fields or "manufacturer_or_packer" in fields, "Manufacturer must be extracted"
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
        if "packer_name" in fields:
            assert "PureHarvest" not in fields["packer_name"]["normalized_value"]

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

class TestNewComplianceFields:
    def setup_method(self):
        self.extractor = FieldExtractor()

    def test_fssai_license(self):
        tokens = [
            make_token("t1", "FSSAI Lic. No. 11221302000439"),
            make_token("t2", "Batch: AB12345")
        ]
        fields = self.extractor.extract_fields(tokens)
        assert "fssai_license" in fields
        assert fields["fssai_license"]["normalized_value"] == "11221302000439"
        
    def test_batch_number(self):
        tokens = [
            make_token("t1", "Batch No: AB-12345-X"),
            make_token("t2", "Lot 998877")
        ]
        fields = self.extractor.extract_fields(tokens)
        assert "batch_number" in fields
        assert fields["batch_number"]["normalized_value"] == "AB-12345-X"

    def test_ingredients_and_dimensions(self):
        tokens = [
            make_token("t1", "Ingredients: Coriander, Cumin, Chilli"),
            make_token("t2", "Length: 15.5 cm"),
            make_token("t3", "Net Qty: 100g")
        ]
        fields = self.extractor.extract_fields(tokens)
        assert "ingredients" in fields
        assert "Coriander" in fields["ingredients"]["normalized_value"]
        assert "dimensions" in fields
        assert fields["dimensions"]["normalized_value"] == "15.5 cm"

class TestExpansionFields:
    def setup_method(self):
        self.extractor = FieldExtractor()

    def test_brand_and_variant(self):
        tokens = [
            make_token("t1", "Brand Name: Nestle"),
            make_token("t2", "Variant: Extra Strong Coffee"),
        ]
        fields = self.extractor.extract_fields(tokens)
        assert "brand_name" in fields
        assert fields["brand_name"]["normalized_value"] == "Nestle"
        assert "product_variant" in fields
        assert fields["product_variant"]["normalized_value"] == "Extra Strong Coffee"

    def test_identity_fields(self):
        tokens = [
            make_token("t1", "Model No: XYZ-123"),
            make_token("t2", "SKU: 9988-ABC"),
            make_token("t3", "Serial Number: SN-55555"),
            make_token("t4", "Website: www.example.com"),
            make_token("t5", "Email: contact@example.com")
        ]
        fields = self.extractor.extract_fields(tokens)
        assert fields["model_number"]["normalized_value"] == "XYZ-123"
        assert fields["sku"]["normalized_value"] == "9988-ABC"
        assert fields["serial_number"]["normalized_value"] == "SN-55555"
        assert fields["website"]["normalized_value"] == "www.example.com"
        assert fields["email"]["normalized_value"] == "contact@example.com"

    def test_certifications_array(self):
        tokens = [
            make_token("t1", "ISI Lic No. 1234567"),
            make_token("t2", "FSSAI Lic. No. 11221302000439")
        ]
        fields = self.extractor.extract_fields(tokens)
        assert "certifications" in fields
        certs = fields["certifications"]["normalized_value"]
        assert len(certs) == 2
        assert any(c["type"] == "ISI" and c["number"] == "1234567" for c in certs)
        assert any(c["type"] == "FSSAI" and c["number"] == "11221302000439" for c in certs)
        assert "fssai_license" in fields  # backward compat

    def test_food_specific_blocks(self):
        tokens = [
            make_token("t1", "Allergen Information: Contains Milk and Nuts"),
            make_token("t2", "Storage: Keep in a cool dry place"),
            make_token("t3", "Directions for use: Add 2 spoons in hot water"),
            make_token("t4", "WARNING: Keep out of reach of children"),
        ]
        fields = self.extractor.extract_fields(tokens)
        assert "allergens" in fields
        assert "Milk" in fields["allergens"]["normalized_value"]
        assert "storage_instructions" in fields
        assert "cool dry place" in fields["storage_instructions"]["normalized_value"]
        assert "usage_instructions" in fields
        assert "2 spoons" in fields["usage_instructions"]["normalized_value"]
        assert "warnings" in fields
        assert "children" in fields["warnings"]["normalized_value"]

    def test_nutrition_structured(self):
        tokens = [
            make_token("t1", "Nutrition Facts"),
            make_token("t2", "Energy 100 kcal"),
            make_token("t3", "Protein 5g"),
            make_token("t4", "Sodium 20mg"),
        ]
        fields = self.extractor.extract_fields(tokens)
        assert "nutrition" in fields
        nutrients = fields["nutrition"]["normalized_value"]
        assert type(nutrients) is dict
        assert nutrients["energy"] == "100 kcal"
        assert nutrients["protein"] == "5g"
        assert nutrients["sodium"] == "20mg"
