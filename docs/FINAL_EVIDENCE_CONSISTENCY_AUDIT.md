# LM-Screen — Final Evidence Consistency QA & Audit Report

**Project Name**: LM-Screen — AI-Based Legal Metrology Compliance Screening, Citizen Intelligence & Enforcement Prioritization Platform  
**SIH Problem Statement**: 25034  
**Audit Date**: September 10, 2026  
**Auditor**: Lead Full-Stack Architect & Senior QA/CV Engineer  

---

## 1. Audited Bugs & Root Cause Analyses

### Bug #1: Product Identity Mismatch Address Fallback
- **Symptom**: In the identity mismatch scenario (User: `PureHarvest Atta 5kg`, Image: `Premium Choco-Chip Biscuits`), the UI warning displayed address text (`"123 Industrial Area, Andheri East"`) as image evidence instead of the product title.
- **Root Cause**: `FieldExtractor._extract_product_name()` sorted non-label text candidates purely by string length descending. Long address lines (32+ chars) beat shorter product titles (19 chars). `product_name_exclusions` regex also lacked address/location keywords (`industrial`, `area`, `plot`, `street`, `road`, `noida`, `andheri`, `mumbai`).
- **Fix**:
  1. Expanded `product_name_exclusions` and added `self.address_words` filter in `ai/field_extractor.py` to strip address/location/company registration lines.
  2. Preserved original top-to-bottom layout token order (product title is printed near the top of packaging).
  3. Attached `ocr_evidence_ids` directly to `product_name` for visual SVG bounding polygon highlights.

### Bug #2: Date Extraction & LM003 Rule Evaluation Inconsistency
- **Symptom**: Images with visible `Mfg. Date: 09/2026` produced extracted field `manufacture_date`, but rule `LM003` generated missing declaration strings (`"manufacture_date, packing_date, import_date missing from visible label panel."`).
- **Root Cause**: `mfg_date_pattern` regex missed prefixes like `Date of Mfg`, `Month & Year of Mfg:`, and date formats with spaces around slashes (`09 / 2026`). In addition, `rules/engine.py` missing field formatting logic did not distinguish `require_any` rules (where ANY ONE date satisfies Rule 6(1)(d)) from mandatory multi-field rules.
- **Fix**:
  1. Updated `mfg_date_pattern` in `ai/field_extractor.py` to capture `Date of Mfg`, `Month & Year of Mfg`, and spaced slash date strings (`09 / 2026`).
  2. Enhanced `rules/engine.py` to check `require_any` logic properly and output `PASS` with exact evidence ID links when `manufacture_date` is extracted.

---

## 2. Evidence Graph & Decision Trace Integrity

- **Evidence Graph**: Node-Edge schema (`IMAGE_QUALITY` $\rightarrow$ `OCR_TOKEN` $\rightarrow$ `FIELD` $\rightarrow$ `CONTEXT` $\rightarrow$ `RULE` $\rightarrow$ `VERDICT`) verified. Every extracted field (`mrp`, `net_quantity`, `manufacture_date`, `product_name`, `gtin`, `manufacturer_or_packer`, `consumer_care`, `address`) links directly to raw OCR token IDs and bounding polygons.
- **Decision Trace**: Tracing API outputs step-by-step pipeline execution stages (`IMAGE_LOAD`, `IMAGE_QUALITY`, `QUALITY_REFINEMENT`, `PANEL_DETECTION`, `OCR`, `FIELD_EXTRACTION`, `CONTEXT_CLASSIFICATION`, `BARCODE`, `IDENTITY_CHECK`, `RULE_EVALUATION`, `VERDICT`).
- **Verdict Safety**: Identity mismatch, poor OCR, missing barcodes, and context uncertainty strictly default to **`NEEDS_REVIEW`** (`"More evidence or human review required"`). Forbidden terms (`COMPLIANT`, `NON-COMPLIANT`, `ILLEGAL`, `VIOLATION`, `FAILED`) are **never** emitted.

---

## 3. Automated Test Suite Execution

- **Total Test Cases**: 57
- **Passed**: 57
- **Failed**: 0
- **Pass Rate**: 100%
- **Execution Time**: 0.81 seconds

### Section 6 Mandatory Regression Test Status
- `test_full_pipeline_regression_section_6`: **PASSED**
  - User: `PureHarvest Atta 5kg`
  - Image: `Premium Choco-Chip Biscuits`
  - Extracted `product_name`: `"Premium Choco-Chip Biscuits"` (NOT address!)
  - Extracted `net_quantity`: `"250 g"`
  - Extracted `mrp`: `"₹150.00"`
  - Extracted `manufacture_date`: `"09/2026"`
  - Extracted `manufacturer_or_packer`: `"ABC Foods Pvt Ltd."`
  - Extracted `consumer_care`: `"1800-123-4567"`
  - Extracted `gtin`: `"8901234567890"`
  - Contradiction Warning: `PRODUCT_IDENTITY_MISMATCH` (`user_provided` = `PureHarvest Atta 5kg`, `image_evidence` = `Premium Choco-Chip Biscuits`)
  - Rule `LM003` Status: **`PASS`**
  - Final Verdict: **`NEEDS_REVIEW`** (`"More evidence or human review required"`)

---

## 4. Remaining System Scope & Boundaries

1. **Non-Judicial AI**: AI operates exclusively as a decision-support and screening engine. Authorized human inspectors retain final enforcement authority.
2. **Approximate Font Scale**: Font height screening is performed relative to decodable barcode scale references and marked as approximate screening.
