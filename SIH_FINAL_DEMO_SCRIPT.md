# SIH Final Demo Script — LM-Screen

> Keep the live demo under 8-10 minutes. This script follows the exact working system.
> All demo scenarios use data seeded by `scripts/seed_demo_data.py`.
> ⚠️ The presenter must NOT make any claims beyond what the system visibly demonstrates.

---

## PRE-DEMO SETUP (Before Presentation)

```bash
# 1. Start backend
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# 2. Start frontend
cd frontend && npm run dev

# 3. Seed demo data (if not already seeded)
python scripts/seed_demo_data.py

# 4. Verify health
curl http://localhost:8000/health
# Expected: {"status": "ok"}
```

Open browser to `http://localhost:5173`

---

## STEP 1 — Login as Officer (30 seconds)

**Action:** Enter credentials on the login screen
- Email: `officer@legalmetrology.gov.in`
- Password: (any string — demo auth accepts officer email prefix)

**What to say:**
> "The system supports multiple roles. As an enforcement officer, I have access to the full investigation workspace and the officer dashboard."

**What not to say:**
- ❌ "This uses industry-standard JWT authentication" (it uses simplified demo auth)

---

## STEP 2 — Officer Dashboard Overview (1 minute)

**Action:** Navigate to the Officer Dashboard

**What to show:**
- Priority queue sorted by priority class (PRIORITY_REVIEW at top)
- Point out Scenario 5: "FastBites Instant Noodles [DEMO]" — 8 citizen signals, PRIORITY_REVIEW
- Show the priority score and reasons

**What to say:**
> "The system aggregates evidence from system screenings and citizen signals, and uses a weighted 6-factor prioritization engine to surface cases that may warrant earlier human review."
> "The priority score is an evidence-weight signal — not a legal determination. The officer still decides."

---

## STEP 3 — Upload a Product Image (1 minute)

**Action:** Click "Scan a Product" → Upload any product image (or use a demo image)

**What to show:**
1. File validation (correct format, size check)
2. Image quality score (blur, brightness, glare)
3. Panel detection result (YOLO fallback → CV heuristic — system shows this honestly)
4. OCR tokens extracted
5. Evidence fields populated
6. Three-state verdict badge

**What to say:**
> "The system runs a full evidence extraction pipeline. First, image quality is assessed to determine if evidence can be reliably extracted. OCR tokens are extracted and individual statutory fields are identified using deterministic regex patterns."

**Point to the disclaimer:**
> "The verdict badge says 'No issue detected' or 'Potential non-compliance detected' — these are screening signals, not legal findings."

**What to say about ML:**
> "The architecture integrates a YOLOv8-based panel detector. Currently the model weights are not trained — the system transparently falls back to an OpenCV heuristic. You can see this on the Analytics Dashboard."

---

## STEP 4 — Show Evidence Chain (1 minute)

**Action:** For an officer, click "Investigate This Product" → Open Evidence Chain tab

**What to show:**
- Each extracted field with its evidence state badge (SUPPORTED / UNCERTAIN / CONFLICTING)
- The "Value" extracted from OCR
- The "Evidence Notes" showing quality reasons
- Rule result for each field (PASS / POTENTIAL_NON_COMPLIANCE)

**What to say:**
> "Every screening decision traces back to specific evidence. You can see exactly which OCR token supported each field extraction, the evidence quality state, and which rule produced each result."

---

## STEP 5 — Show Conflict Scenario (1 minute)

**Action:** Navigate to Scenario 4 (Barcode/OCR GTIN mismatch product)
- Product: "Oats Porridge Mix 500g [DEMO]"

**What to show:**
- GTIN evidence field with state `CONFLICTING`
- Quality reason: "Barcode scan returned different GTIN than OCR region"
- Verdict: NEEDS_REVIEW

**What to say:**
> "When multiple evidence sources disagree — here the barcode scanner and the OCR-extracted GTIN are different — the system flags a conflict. It does not automatically decide which source is correct. That requires human investigation."

---

## STEP 6 — Citizen Signals (30 seconds)

**Action:** Click "Citizen Signals" tab for the FastBites cluster

**What to show:**
- 8 synthetic citizen reports from 8 cities
- Descriptions of different MRP-related observations

**What to say:**
> "Citizens can submit observations through the Citizen Portal. Multiple reports about the same product are clustered together. Here, 8 citizens from different cities reported observations about this product's MRP."
> "⚠️ This is synthetic demo data — it does NOT represent real citizen activity."

---

## STEP 7 — Officer Correction (2 minutes)

**Action:** Navigate to Scenario 6 — "Brown Rice 1kg [DEMO]" (OCR uncertainty case)

**What to show:**

1. **Before correction:**
   - MRP field: `UNCERTAIN` state
   - OCR value: "Rs. 80.00 [OCR uncertain]"
   - Quality note: "Character '0' vs 'O' ambiguity detected"
   - Verdict: POTENTIAL_NON_COMPLIANCE

2. **Perform correction:**
   - Click "Correct Evidence" next to MRP field
   - Enter corrected value: `₹ 80.00`
   - Enter reason: "Physical inspection confirmed correct MRP"
   - Submit

3. **After correction:**
   - Evidence state changes to `MANUALLY_VERIFIED`
   - Recalculation runs (consistency + rules re-evaluated)
   - New verdict shown

4. **Show audit trail:**
   - Switch to Audit Trail tab
   - Show: actor (Inspector R. K. Sharma), timestamp, old value, corrected value, reason

**What to say:**
> "The system does not overwrite original evidence. The OCR output — including its uncertainty — is preserved. The officer's correction is recorded as a separate event with full traceability."
> "The system then re-evaluates consistency and rules based on the corrected evidence and updates the verdict."

---

## STEP 8 — Analytics Dashboard (1 minute)

**Action:** Navigate to Analytics → System Overview

**What to show:**
1. Total scans, observations, products, review-required cases
2. ML Model Health widget → "YOLOv8 Panel Detector: MODEL_NOT_FOUND — Fallback: OpenCV heuristic active"
3. Observation trends chart

**What to say:**
> "The analytics layer shows operational intelligence. Crucially, the ML Model Health widget honestly shows that the YOLO detector is not trained yet and the system is using CV fallback. This is real-time system status, not a static slide."

---

## STEP 9 — Close with Architecture Summary (1 minute)

**Show the architecture flow:**
```
Citizen/Officer → Image Upload → Quality Gate → Panel Detection (CV Heuristic / YOLO)
→ OCR → Barcode → Evidence Extraction → Product Identity → Context Classification
→ Rule Applicability → Consistency Engine → Evidence Quality → Rule Evaluation
→ Three-State Verdict → Citizen Clustering → Prioritization → Officer Workbench
→ Human Decision → Audit Trail
```

**Key statement:**
> "LM-Screen does not replace the officer. It makes the officer's investigation evidence-rich, traceable, explainable, and efficient. Every decision trace is preserved. Every correction is audited. The system is a tool — the officer is the decision-maker."

---

## ML ROADMAP (For Q&A If Asked)

> "Our ML architecture is designed and implemented. We need to:
> 1. Collect annotated FMCG images (target: 1,000+ unique products)
> 2. Train YOLOv8 on panel detection
> 3. Evaluate on held-out set with real metrics
> 4. Deploy weights — system automatically switches from heuristic to YOLO
>
> The officer correction log also becomes a natural source of NER training data
> over time, creating a feedback loop between human expertise and model improvement."

---

## DEMO FAILURE RECOVERY

| Failure | Recovery |
|---------|----------|
| Backend not running | Show `GET /health` error message → restart |
| ML unavailable | Expected — show Analytics Dashboard ML Health widget honestly |
| OCR returns empty | Show `NEEDS_REVIEW` verdict — explain graceful degradation |
| Database connection error | Have SQLite fallback ready: `DATABASE_URL=sqlite:///./lm_screen.db` |
| Frontend 500 error | Show the meaningful error message (not stack trace) — system handles it gracefully |

---

## WHAT NOT TO SAY (Red Lines)

| ❌ Do NOT say | ✅ Say instead |
|---|---|
| "Our AI is 99% accurate" | "The system uses deterministic rule-based screening" |
| "Our ML detects violations" | "The ML architecture detects label panels; rules detect screening signals" |
| "10,000 citizens reported this" | "This is synthetic demo data seeded for presentation" |
| "This product is non-compliant" | "This scan produced a POTENTIAL_NON_COMPLIANCE screening signal" |
| "The AI decided" | "The rule engine evaluated the extracted evidence" |
| "YOLO ran on this image" | "OpenCV heuristic was used — YOLO weights are not yet trained" |
