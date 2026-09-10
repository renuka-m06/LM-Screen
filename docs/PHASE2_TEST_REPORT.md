# LM-Screen Phase 2 Test Report

**Execution Date**: September 10, 2026  
**Total Test Cases**: 57  
**Passed**: 57  
**Failed**: 0  
**Pass Rate**: 100%  
**Execution Time**: 0.85 seconds  

---

## Key Test Suite Summaries

### 1. Contradiction Engine Tests (`test_contradictions.py`)
- `test_critical_regression_identity_mismatch`: **PASSED**
  - Verified user product `PureHarvest Atta 5kg` vs image `Premium Choco-Chip Biscuits`.
  - Verified derived biscuit metadata (`250 g`, `₹150.00`, `ABC Foods Pvt Ltd`).
  - Verified `PRODUCT_IDENTITY_CONFLICT` object generation.
  - Verified final verdict override = `NEEDS_REVIEW` (NOT `POTENTIAL_NON_COMPLIANCE`, NOT `COMPLIANT`, NOT `NON-COMPLIANT`).
- `test_gtin_contradiction_detection`: **PASSED**
  - Verified multi-source GTIN mismatch detection across user input, OCR, and barcode decoders.

### 2. Phase 2 Technical Upgrades (`test_phase2_features.py`)
- `test_evidence_graph_builder`: **PASSED** (Constructs 5+ node types and 4+ edge types).
- `test_evidence_passport_generator`: **PASSED** (Generates SHA-256 signature and locks model versions).
- `test_officer_copilot`: **PASSED** (Provides grounded answer without legal claims).

### 3. Core Engine Tests
- API endpoints (`test_api.py`): **PASSED**
- Statutory Field Extraction (`test_extraction.py`): **PASSED** (39 items)
- Quality Gate (`test_quality.py`): **PASSED**
- Rule Engine (`test_rules.py`): **PASSED**
- Priority Engine (`test_prioritization.py`): **PASSED**
