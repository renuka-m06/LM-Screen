# LM-Screen Testing Framework & Strategy

## Test Suite Execution
Run the automated test suite from the project root:
```bash
python -m pytest backend/tests
```

## Coverage Areas
- **Unit Tests**: MRP extraction, Net Quantity, Date parsing, GSTIN checksum.
- **Rule Engine Tests**: Evaluates rule profile applicability and exception handling.
- **Quality Gate Tests**: Validates blur, glare, brightness, and resolution scoring thresholds.
- **Prioritization Tests**: Validates weighted priority score calculation and cluster updates.
- **API Tests**: Validates endpoints (`/scans`, `/reports`, `/officer/queue`, `/dashboard/stats`).

## Regression & Adversarial Verification
The test suite includes 52 automated test cases verifying fail-safe behavior under blurry input, missing fields, user-product identity contradictions, and missing barcodes.
