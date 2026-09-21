# SIH Judge Attack Checklist — LM-Screen

> Every answer in this document corresponds to the actual implementation.
> No claims are made beyond what exists in the codebase.

---

## PROBLEM STATEMENT

**Q: What exact problem are you solving?**

Manual inspection of pre-packaged commodity labels by Legal Metrology officers is slow, subjective, and difficult to scale. Officers physically visit markets and visually inspect labels for mandatory statutory declarations (MRP, Net Quantity, Manufacture Date, etc.) required under the Legal Metrology (Packaged Commodities) Rules, 2011. Citizens who observe violations have no structured mechanism to report them. Evidence from different sources (citizen observations, OCR extractions, barcode scans) cannot be easily aggregated.

LM-Screen provides: (1) structured image-based evidence extraction, (2) rule-based screening signals, and (3) an officer workbench that aggregates multi-source evidence for informed human decisions.

**Q: Who uses this?**

- **Enforcement Officers** — Use the Officer Workbench and Investigation Workspace to review prioritized cases, inspect evidence, and record decisions.
- **Citizens** — Submit observations and images through the Citizen Portal when they notice potential label violations in stores.
- **System** — Processes images, extracts evidence, and generates screening signals automatically.

**Q: Why is existing manual screening insufficient?**

- Officers cannot be everywhere simultaneously
- No structured digital record of inspection outcomes
- Citizen complaints have no systematic channel to reach officers
- Multiple citizen reports about the same product are not aggregated
- Evidence trail is paper-based and not reproducible

---

## TECHNICAL

**Q: Why OCR?**

Statutory declarations on pre-packaged commodities are printed text. OCR extracts this text from images, converting visual declarations into machine-readable evidence. We use PaddleOCR/EasyOCR for token extraction and deterministic regex patterns for field identification.

**Q: Why YOLO (planned)?**

Packaged commodity labels have multiple panels (front, back, nutrition, declaration area). A panel detector helps crop the image to the relevant declaration panel before running OCR, reducing noise and improving extraction accuracy. The model architecture is implemented; training awaits a sufficient annotated dataset.

**Q: Why PostgreSQL?**

Relational model supports: product-scan-evidence-rule result FK relationships, officer corrections linked to specific evidence records, citizen reports linked to products, and audit trails with actor + timestamp. SQLite is supported for development.

**Q: Why Evidence Graph?**

Evidence from multiple sources (OCR tokens, barcode scan, user-provided hints, ML detections) must be traceable to their origin. The Evidence Graph preserves source attribution — which OCR token supported which extracted field, which rule evaluated which evidence, and which officer corrected which evidence node.

**Q: Why Deterministic Rules?**

Legal Metrology rules are statutory — they are published law, not pattern-matching targets. A deterministic rule engine ensures: (1) results are auditable and explainable, (2) rules can be versioned and updated when law changes, (3) outputs cannot be attributed to "the AI said so."

**Q: Why not simply use an LLM?**

LLMs are non-deterministic, cannot be audited, may hallucinate legal requirements, produce unreproducible outputs, and cannot be legally cited in enforcement actions. A system that influences legal decisions must be deterministic, auditable, and explainable. Our rule engine produces step-by-step decision traces.

**Q: What happens when OCR is wrong?**

- Evidence state is set to `UNCERTAIN` or `CONFLICTING`
- Cross-evidence consistency engine detects conflicts between sources
- Evidence quality evaluator flags low-confidence fields
- Verdict degrades to `NEEDS_REVIEW`, not automatic non-compliance
- Officer can inspect the raw OCR token, normalized value, and correct it
- Correction is recorded in the audit trail; original value is preserved

**Q: What happens when ML is wrong?**

- ML output is evidence, not verdict
- The rule engine ignores `DETECTION` type evidence (ML bounding boxes do not trigger compliance rules)
- Officer can override any ML-derived evidence
- Original ML output is preserved alongside the correction
- System never hides when it is using heuristic fallback

**Q: What happens when the image is poor?**

- Image quality gate (Laplacian blur + brightness + glare) runs first
- If quality is `RETAKE_REQUIRED`, evidence extraction still runs but with degraded confidence
- Low-confidence extractions produce `UNCERTAIN` evidence states
- Verdict degrades to `NEEDS_REVIEW`
- System never converts OCR failure into "field missing" automatically

---

## LEGAL / OPERATIONAL

**Q: Is this making a legal decision?**

No. LM-Screen is a **decision-support system**. It produces three screening signals:
- `PASS_SCREENING` — "No issue detected in checks performed"
- `POTENTIAL_NON_COMPLIANCE` — "Potential issue detected; officer review required"
- `NEEDS_REVIEW` — "Insufficient evidence for any screening determination"

None of these signals are legal determinations. The public label deliberately uses hedged language. Only an authorized officer can make a legal determination.

**Q: Who makes the final decision?**

The authorized enforcement officer. The system presents evidence; the officer decides.

**Q: How are uncertain cases handled?**

Uncertain cases produce `NEEDS_REVIEW`. The officer workbench shows which evidence fields are uncertain and why. Officers can inspect raw OCR tokens, quality reasons, and consistency check results.

**Q: How do you preserve evidence?**

Evidence records are never overwritten. When an officer corrects an evidence field:
1. Original value is stored in `evidence_corrections.original_value`
2. Corrected value is stored in `evidence_corrections.corrected_value`
3. `evidence.normalized_value` is updated to corrected value
4. `evidence.evidence_state` becomes `MANUALLY_VERIFIED`
5. A `DecisionTrace` record is written with actor, timestamp, stage, old/new value

**Q: Can an officer correct the system?**

Yes. The Officer Correction endpoint (`POST /api/v1/scans/{id}/evidence/{id}/correct`) allows officers to correct any evidence field. The correction triggers re-evaluation of consistency checks and the rule engine, producing a new verdict that is also traced.

---

## SCALABILITY

**Q: What happens with thousands of scans?**

The database is PostgreSQL with indexed queries on `scans.status`, `product_clusters.priority_class`, and `extracted_fields.field_name`. The analytics layer uses SQL aggregations. Frontend pagination is implemented on the officer dashboard queue.

**Q: How are duplicate submissions handled?**

SHA-256 image hashing detects identical image uploads. The `duplicate_of_scan_id` field on `Scan` marks subsequent submissions. The original scan is preserved; the duplicate is flagged as `DUPLICATE_OBSERVATION`.

**Q: How do you aggregate observations?**

`ProductCluster` entities group scans and citizen reports about the same product (matched by GTIN or perceptual hash). The cluster maintains aggregate counts (`report_count`, `ai_flag_count`), a priority score, and an actionability state.

**Q: How do you prevent repeated reports from becoming automatic proof?**

The system explicitly requires officer adjudication before any cluster changes status. `report_count` is an evidence weight signal, not a threshold trigger. The `actionability_state` can be `INSUFFICIENT_EVIDENCE` even with many reports.

---

## ML

**Q: What model are you using?**

The architecture implements a YOLOv8-based panel detector. Currently the model weights (`models/detector.pt`) do not exist. The system falls back to OpenCV heuristic detection and reports this transparently.

**Q: Is it trained?**

No. Training awaits a sufficient annotated dataset.

**Q: What is your dataset?**

Currently 0 images. The dataset specification (classes, format, annotation schema) is defined in `DATASET.md` and `ml/dataset/data.yaml`.

**Q: How many unique images?**

Zero at present.

**Q: How are annotations created?**

The annotation pipeline is designed for YOLOv8 TXT format using tools such as Roboflow or LabelImg. NER annotations use BIO format. Data collection has not begun.

**Q: How will you evaluate it?**

On a held-out test split using standard metrics: mAP@50, mAP@50-95, precision, recall. No evaluation metrics are claimed before training and evaluation are complete.

**Q: What happens if the model is unavailable?**

`ModelRegistry` returns `MODEL_NOT_FOUND`. `DetectionService` activates the OpenCV heuristic fallback. All evidence from the fallback is tagged `source: HEURISTIC`. The Analytics Dashboard shows the real-time model status. The system never claims YOLO ran when it did not.

---

## SECURITY

**Q: How do you protect citizen data?**

Citizen reports use a `reporter_hash` instead of direct identity. No citizen PII (name, address, phone) is required or stored for report submission.

**Q: How do you authenticate officers?**

The current demo uses header-based role checking (`x-user-role: OFFICER`). This is a demonstration simplification. A production deployment would require JWT-based authentication with proper token signing and verification. The `SECRET_KEY` setting is designed for this upgrade path.

**Q: How do you prevent unauthorized correction?**

The evidence correction endpoint checks `x-user-role` and returns `403 Forbidden` for non-officer roles. The frontend conditionally renders officer-only UI elements based on the logged-in role, but backend authorization is always enforced independently.

**Q: How are audit records preserved?**

`DecisionTrace`, `OfficerReview`, and `EvidenceCorrection` records are append-only. No endpoint deletes audit records. The database schema has no soft-delete mechanism on these tables.

---

## ARCHITECTURE BOUNDARY QUESTIONS

**Q: `NOT_DETECTED` vs `MISSING` — what's the difference?**

- `NOT_DETECTED` / `ABSENT_FROM_EVIDENCE` — The field was not found in the available OCR tokens. This could be because: (a) the field truly doesn't exist on the label, (b) the image quality is poor, (c) the text is in a different location, or (d) OCR failed to read it.
- `MISSING` (as a rule result `POTENTIAL_NON_COMPLIANCE`) — Only declared when the rule engine determines that a required field was not extractable after all evidence evaluation steps, and image quality was sufficient for a reasonable screening attempt.

The system never converts `NOT_DETECTED` directly into `MISSING`. Evidence state flows through quality evaluation first.

**Q: `INSUFFICIENT_EVIDENCE` vs `NON_COMPLIANCE` — what's the difference?**

- `INSUFFICIENT_EVIDENCE` — The cluster's `actionability_state` when evidence quality or quantity is too low to form a screening signal. Officers cannot act on this.
- `POTENTIAL_NON_COMPLIANCE` — The scan verdict when the rule engine detects that a required declaration appears absent from a readable image. Still a screening signal, not a legal determination.

**Q: Is `POTENTIAL_NON_COMPLIANCE` a legal verdict?**

No. It is a screening signal that tells an officer "this warrants your attention." The public-facing label says: "Potential non-compliance detected." The mandatory disclaimer states explicitly that this does not replace officer inspection or legal enforcement procedures.
