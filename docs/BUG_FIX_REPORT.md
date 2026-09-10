# LM-Screen: Bug Fix Report

## 1. Bugs Discovered

### BUG-01: Mfg Date Regex Fails on "Mfg." (Period-Notation)
**File:** `ai/field_extractor.py` L23-26  
**Severity:** CRITICAL — root cause of "manufacture_date not detected" failure  
**Root Cause:** The regex pattern for mfg_date uses `(?:mfd|mfg|...)` but the character class does NOT include optional period `\.?`. When the OCR returns "Mfg. Date: 09/2026", the `mfg.` token fails to match because the literal `.` after `mfg` is not matched.

**Before:**
```
r"(?:mfd|mfg|manufactur(?:ed|ing)|pkd|packed)\s*(?:on|date)?[:\s]*..."
```
**After:**
```
r"(?:mfd\.?|mfg\.?|manufactur(?:ed|ing)|pkd\.?|packed)\s*(?:on|date)?[:\s]*..."
```

---

### BUG-02: Hardcoded Manufacturer Fallback
**File:** `ai/field_extractor.py` L167  
**Severity:** HIGH — fabricates evidence  
**Root Cause:** When the manufacturer regex fails to extract a name, the code falls back to the hardcoded string `"PureHarvest Agro"`. This invents manufacturer data from thin air.

**Fix:** Remove hardcoded fallback. If regex fails but keyword anchor confirms presence, use a safe generic label `"[Manufacturer declared — extraction uncertain]"` with reduced confidence.

---

### BUG-03: NameError Bug in GTIN Validation
**File:** `ai/consistency.py` L58, L84  
**Severity:** HIGH — crashes on GTIN validation  
**Root Cause:** `validate_gtin()` uses variable name `gstin_str` (the parameter for the OTHER method) instead of `gtin_str`. This is a copy-paste bug that causes a `NameError` at runtime.

---

### BUG-04: No Product Identity Mismatch Detection
**File:** `ai/field_extractor.py`, `backend/app/routers/scans.py`  
**Severity:** HIGH — violates evidence-first principle  
**Root Cause:** The system does not extract `product_name` from OCR, so it cannot compare user-provided product name against image evidence. User-supplied `product_name` is silently accepted as authoritative.

**Fix:** Add `product_name` extraction to `FieldExtractor`. Add identity mismatch check in `scans.py` that compares user-provided name vs. OCR-extracted name.

---

### BUG-05: User Input Used as Product Identity Without Verification
**File:** `backend/app/routers/scans.py` L105-115  
**Severity:** HIGH — evidence-first violation  
**Root Cause:** `product_name` from form input is used directly to create/find a Product record without checking if OCR evidence supports this identity. User can label any image with any product name and it will be accepted.

---

### BUG-06: Missing Field ≠ Declaration Absent — Not Distinguished
**File:** `rules/engine.py` L131-138  
**Severity:** MEDIUM — conflates OCR failure with legal non-compliance  
**Root Cause:** When a required field is not in `extracted_fields` AND quality is ACCEPTABLE, the engine immediately issues `POTENTIAL_NON_COMPLIANCE`. But "not extracted" may mean OCR couldn't reliably find it, not that the declaration is absent.  
**Fix:** Add a confidence threshold check. Only escalate to `POTENTIAL_NON_COMPLIANCE` when quality is good AND token count is sufficient (meaning OCR ran successfully).

---

### BUG-07: No Decision Trace in API Response
**File:** `backend/app/schemas/schemas.py`, `backend/app/routers/scans.py`  
**Severity:** MEDIUM — no explainability chain  
**Root Cause:** The API response includes `checks_performed` but no step-by-step pipeline decision trace (quality → OCR → extraction → context → rules → verdict).

---

### BUG-08: Demo "Identity Mismatch" Preset Missing
**File:** `frontend/src/components/Scanner.tsx`  
**Severity:** LOW — demo completeness  
**Root Cause:** The demo presets include Clean/Missing MRP/Blurry but not the "Identity Mismatch" scenario required by the prompt.

---

## 2. Files Changed

| File | Change |
|------|--------|
| `ai/field_extractor.py` | Fix Mfg Date regex; remove hardcoded fallback; add product_name extraction |
| `ai/consistency.py` | Fix NameError in `validate_gtin()` |
| `backend/app/routers/scans.py` | Add identity mismatch detection; add decision_trace to response |
| `backend/app/schemas/schemas.py` | Add `identity_warnings`, `decision_trace` to ScanResponse |
| `frontend/src/types.ts` | Add `identity_warnings`, `decision_trace` to TypeScript ScanResult |
| `frontend/src/components/Scanner.tsx` | Render identity mismatch warnings; add identity mismatch demo preset |
| `backend/tests/test_extraction.py` | Add comprehensive regression tests |

---

## 3. Data Flow Before Fix

```
Image → OCR → "Mfg. Date: 09/2026"
                  ↓ (regex fails to match because of "Mfg." dot)
             manufacture_date NOT extracted
                  ↓
             Rule engine: field absent + ACCEPTABLE quality
                  ↓
             POTENTIAL_NON_COMPLIANCE (WRONG)
```

## 4. Data Flow After Fix

```
Image → OCR → "Mfg. Date: 09/2026"
                  ↓ (fixed regex matches "Mfg." with optional dot)
             manufacture_date = "09/2026" extracted
                  ↓
             Rule engine: field present
                  ↓
             PASS (CORRECT)

User provides product_name = "PureHarvest Atta 5kg"
OCR extracts product_name = "Premium Choco-Chip Biscuits"
                  ↓
             identity_mismatch = TRUE
                  ↓
             NEEDS_REVIEW + mismatch warning (CORRECT)
```

## 5. Remaining Limitations

- OCR accuracy depends on image quality; the EasyOCR/PaddleOCR model may still fail on some fonts
- Product name extraction uses heuristics (first large bold text), not a dedicated text-classification model
- GSTIN external verification not connected (flagged as RULE_REQUIRES_OFFICIAL_VERIFICATION)
- Barcode physical scale measurement not defensible without calibration (flagged appropriately)
- The system is a screening aid, not an enforcement authority
