# LM-SCREEN — MASTER BUILD PROMPT
### AI-Based Legal Metrology Compliance Screening, Citizen Intelligence & Enforcement Prioritization Platform
**SIH Problem Statement 25034 | Ministry of Consumer Affairs, Food & Public Distribution | Dept. of Consumer Affairs | Category: Software**

> Paste this document into any AI coding tool (Claude Code, Gemini/Antigravity, Colab, Cursor, etc.) as full project context before asking it to generate code. It consolidates the Technical Blueprint, the Final Master Plan, and the Team Onboarding doc into one authoritative, non-contradictory spec. Where the source documents differed in detail, the most conservative/safety-first version is used.

---

## 0. NON-NEGOTIABLE FRAMING (read this first, always obey it)

You are building a **screening tool, not a legal judge**. Every output, UI string, and API response must be consistent with this positioning:

- "No issue detected in the checks performed" — NOT "compliant" or "passed."
- "Potential non-compliance detected" — NOT "violation" or "illegal."
- "More evidence or human review required" — NOT "failed" or "error."

A poor-quality image must **never** become evidence of non-compliance. When in doubt about image quality, product context, rule applicability, or measurement validity, the system must return **NEEDS_REVIEW** — never guess, never default silently. Optimize for safe uncertainty, not for the number of automatic verdicts produced.

This system does not replace an authorized officer, provide legal adjudication, do laboratory testing, or trigger automatic enforcement. AI-only flags never confirm a violation — only a human officer review can.

---

## 1. PROBLEM STATEMENT

Every packaged commodity sold in India must display prescribed declarations under the **Legal Metrology Act, 2009** and the **Legal Metrology (Packaged Commodities) Rules, 2011**:

- Manufacturer/packer/importer name and complete address
- Common/generic commodity name
- Net quantity
- MRP (Maximum Retail Price), inclusive of all taxes
- Month and year of manufacture/packing/import
- Consumer-care contact details
- Country of origin (if imported)
- Minimum legible font size for the above

Today, compliance is checked by officers manually inspecting physical packages — too slow and inconsistent given the volume of retail and e-commerce products. LM-Screen automates first-pass screening from a photograph, flags likely issues with evidence, and routes uncertain cases to humans.

**One-line pitch:** AI extracts label declarations, checks them against versioned Legal Metrology rules, highlights potential issues with evidence, and routes uncertain cases for human review.

---

## 2. MVP SCOPE (locked)

**In scope:**
- Packaged food/snacks — biscuits, chips, snacks
- Rectangular packages / rectangular information panels only
- English first; Hindi after corpus validation
- Upload-based scanning (live camera optional/secondary)
- OCR with bounding boxes; required-field extraction & normalization
- MRP, quantity, date, address, consumer-care validation
- Barcode detection + **conditional** scale-based font screening
- Versioned deterministic rule evaluation (YAML/JSON)
- Evidence visualization, three-state result
- GSTIN format + local-dataset **consistency** screening (not full verification)
- Basic citizen reporting + officer review workflow

**Explicitly out of scope — if suggested mid-build, the answer is "future scope slide," not "let's build it":**
- FSSAI ingredient/health scoring (different law entirely)
- Full 22-language OCR (English + Hindi only)
- Large-scale e-commerce crawling; nationwide product database
- Blockchain, AR, LiDAR, depth-camera measurement
- Custom CV models trained from scratch (use existing tools: PaddleOCR, OpenCV)
- Cylindrical/irregular packaging (bottles, jars) — rectangular only
- Fully automated legal interpretation or enforcement

---

## 3. SYSTEM ARCHITECTURE

```
USER / CITIZEN / OFFICER
 ↓
PRODUCT IMAGE CAPTURE / UPLOAD
 ↓
IMAGE QUALITY ASSESSMENT           → ACCEPTABLE / PARTIALLY_USABLE / RETAKE_REQUIRED
 ↓
PACKAGE + PANEL DETECTION
 ↓
PERSPECTIVE CORRECTION
 ↓
OCR + BARCODE DETECTION
 ↓
EVIDENCE-FIRST FIELD EXTRACTION
 ↓
PRODUCT CONTEXT CLASSIFICATION
 ↓
RULE PROFILE SELECTION
 ↓
DETERMINISTIC RULE ENGINE
 ↓
OPTIONAL GSTIN/GTIN CONSISTENCY SCREENING
 ↓
CONFIDENCE + EVIDENCE AGGREGATION
 ↓
THREE-STATE SCREENING RESULT
      /              \
 AI SIGNAL       CITIZEN SIGNAL
      \              /
    UNIFIED VIOLATION SIGNAL
 ↓
 DUPLICATE DETECTION
 ↓
 PRODUCT ISSUE CLUSTERING
 ↓
 OPERATIONAL PRIORITIZATION SCORE
 ↓
 OFFICER DASHBOARD
 ↓
 HUMAN VERIFICATION → CONFIRMED / REJECTED
```

**Three implementation layers** (build in this priority order; degrade gracefully if time-constrained):
- **Layer 1 — Core Compliance Screening** (mandatory, graded): image processing → OCR → extraction → rule engine → barcode screening → evidence overlays → confidence-aware three-state result.
- **Layer 2 — Citizen Intelligence** (secondary): issue reporting, evidence attachment, duplicate detection, moderation, product issue history. Reduce to seeded demo data if Layer 1 isn't stable.
- **Layer 3 — Enforcement Intelligence** (secondary): report clustering, prioritization score, officer dashboard, human verification. Reduce to seeded demo data if Layer 1 isn't stable.

---

## 4. FINAL TECHNOLOGY STACK

| Layer | Technology |
|---|---|
| Frontend | React + TypeScript + Vite, mobile-first, Canvas/SVG evidence overlays, Recharts |
| Backend | Python, FastAPI, Pydantic, SQLAlchemy |
| OCR | PaddleOCR (English + Hindi models) |
| Computer vision | OpenCV (preprocessing, contours, perspective correction) — no custom-trained models for MVP |
| Barcode | pyzbar / OpenCV |
| Rule engine | Deterministic Python evaluator + versioned YAML/JSON rule profiles, tested independently |
| Database | PostgreSQL (Supabase-managed preferred for build speed; SQLite acceptable for early local dev) |
| Storage | Supabase Storage for MVP; design behind an interface so S3 can replace it later |
| Auth | Supabase Auth / JWT (best MVP choice for managed roles) |
| LLM (optional) | Groq / Gemini / OpenAI — normalization & explanation text only, **never** the legal verdict |
| Deployment | Vercel (frontend) + Render/Railway (backend) + Supabase (DB/storage/auth); Docker Compose once local functionality is stable |
| Dev tools | Google Colab (CV/OCR experiments), Google AI Studio (fast frontend scaffolding), Google Antigravity (agentic integration/testing) |

**Rationale for "no custom model initially":** scope is deliberately narrow (rectangular, 2–3 categories). Measure where deterministic OpenCV/PaddleOCR fails on real data before ever considering a trained model like YOLO.

---

## 5. DEPENDENCY-ORDERED BUILD PLAN (14 stages → mapped to a 4-week schedule)

| Stage | Deliverable |
|---|---|
| 1. Project Foundation | Monorepo, GitHub repo, env vars, Docker Compose, FastAPI health endpoint, React shell, DB connection, shared API contracts, feature-branch workflow |
| 2. Dataset Collection | 100–250 images (biscuits/chips/snacks): good/low light, blur, glare, tilt, distance, English/Hindi, compliant/missing-field cases, multi-product shots; metadata manifest |
| 3. Image Quality Gate | Blur (Laplacian variance), brightness (histogram/mean intensity), resolution minimum → ACCEPT / PARTIAL / RETAKE |
| 4. Package Geometry | grayscale → denoise → Canny edges → contours → polygon approx → 4-corner candidate → homography; manual crop fallback |
| 5. OCR Pipeline | Preprocess + PaddleOCR; persist raw text, polygons, confidence, language — never discard source evidence |
| 6. Field Extraction | Regex + keyword anchors + spatial relationships + normalization (MRP, net qty, dates, phone numbers) |
| 7. Context Classification | product_category, package_type, origin, geometry_supported, context_confidence; unknown → NEEDS_REVIEW |
| 8. Rule Engine | Versioned YAML/JSON rules evaluated independently of OCR; per-rule decision trace |
| 9. Verdict Engine | Aggregate rule outcomes + evidence confidence → three-state result |
| 10. Evidence UI | SVG overlays on OCR/evidence boxes; click-to-inspect why a field passed/failed/uncertain |
| 11. Citizen Reporting | Unverified signal creation: issue category, evidence, description, optional consent-based location |
| 12. Intelligence Layer | Duplicate matching, issue clustering, configurable priority scoring |
| 13. Officer Workflow | Priority queue, product intelligence profile, human review actions, audit trail |
| 14. Adversarial Testing | Blur, glare, partial barcode, multiple MRPs, mixed language, tilt, missing panels |

### Week-by-week schedule
- **Week 1:** Freeze scope, verify official rules text, repo + skeleton, collect dataset, image-quality checks, OCR v1.
- **Week 2:** Field extraction, normalization, rule profiles, deterministic rule engine, three-state outcome, evidence overlays, rule unit tests.
- **Week 3:** Barcode validation, conditional scale estimation, font-screening uncertainty handling, GSTIN extraction, local registry adapter, citizen reporting.
- **Week 4:** Duplicate detection, synthetic report data, clustering, prioritization score, officer dashboard, human review, final evaluation, demo prep.

---

## 6. DATASET & IMAGE QUALITY DESIGN

```
datasets/
  biscuits/{compliant, missing_mrp, missing_quantity, blurry, glare, tilted}/
  chips/
  snacks/
  metadata/image_manifest.csv
```
Manifest fields: `image_id, category, brand, language, lighting, blur_level, glare, tilt, expected_fields_present, known_issue, barcode_visible, notes`.

| Check | Method | Behavior |
|---|---|---|
| Resolution | Minimum pixel threshold | Retake if unusable |
| Blur | Variance of Laplacian | Low score → uncertain |
| Brightness | Histogram / mean grayscale | Warn if under/overexposed |
| Glare | High-intensity saturated regions | Warning or review |
| Tilt | Quadrilateral geometry | Correct if stable |
| Text visibility | OCR token count/confidence | Review if weak |
| Multiple products | Contour/object heuristic | Warn; never silently pick one |

**Safety rule:** poor image quality must never become evidence that a product is non-compliant.

---

## 7. OCR & MULTILINGUAL PIPELINE

```
IMAGE → denoise/resize → contrast enhancement → glare warning → edge detection + contours
→ four corners → perspective transform → PaddleOCR → text + bounding polygons + confidence
→ structured OCR evidence
```
Example payload:
```json
{
  "scan_id": "scan_001",
  "tokens": [{
    "text": "MRP Rs. 20",
    "polygon": [[120,50],[340,50],[340,85],[120,85]],
    "ocr_confidence": 0.96,
    "language": "en"
  }]
}
```
Validate Hindi recognition against the real package corpus before claiming multilingual support. **OCR confidence must never be treated as legal confidence.**

---

## 8. EVIDENCE-FIRST FIELD EXTRACTION

| Level | Method | Use |
|---|---|---|
| 1 | Regular expressions | Currency, quantities, dates, phone numbers |
| 2 | Keyword anchors | MRP, Net Qty, Packed On, Consumer Care |
| 3 | Spatial relationships | Nearest tokens, label-value layout |
| 4 | Normalization | g/kg, ₹/Rs, date canonicalization |
| 5 (optional) | LLM assistance | Ambiguous normalization / natural-language explanation only — **never** the final legal decision |

Hybrid extraction is required — LLM-only extraction can hallucinate absent declarations and weakens evidence provenance. Every normalized value must retain its raw OCR evidence ID(s).

**Required fields:** manufacturer/packer/importer (name, role, address), commodity name, net quantity, MRP, dates (manufacture/packing/import/best-before kept distinct), consumer care, country of origin (if imported).

**Product-context classification** (before rules apply): food vs. other category; retail vs. institutional/industrial/wholesale/transport; domestic vs. imported; rectangular vs. unsupported shape; single vs. multiple products; known vs. unknown manufacture period. If an exemption might apply, or context is unknown, flag for review — do not guess a default rule profile.

---

## 9. DETERMINISTIC RULE ENGINE

```
rule_profiles/
  food/retail_package.yaml
  food/imported_package.yaml
  common/declarations.yaml
  versions/2026.1/
```
Example rule record:
```yaml
rule_id: LM001
version: 2026.1
name: MRP Declaration
applies_when:
  package_type: retail
required_fields:
  - mrp
checks:
  - field_present
  - valid_format
failure_status: POTENTIAL_NON_COMPLIANCE
uncertain_status: NEEDS_REVIEW
```
Pipeline: select profile → evaluate applicability → verify evidence sufficiency → execute checks → record result → attach evidence IDs → save rule version → aggregate verdict.

Rules live in YAML/JSON (not hardcoded in backend logic) because the underlying law is amended periodically — this must remain versionable, testable, and explainable. **The working rule checklist must be cross-checked against the official Act/Rules text and amendments before final deployment.**

---

## 10. CONFIDENCE MODEL & FINAL VERDICT

| Confidence type | Meaning |
|---|---|
| OCR confidence | Characters were read correctly |
| Extraction confidence | OCR tokens map to the intended field |
| Evidence confidence | Combined image quality + provenance |
| Screening confidence | Applicable checks were sufficiently supported |

| Internal status | Public-facing label | Meaning |
|---|---|---|
| PASS_SCREENING | "No issue detected in the checks performed" | All applicable checks completed with sufficient evidence |
| POTENTIAL_NON_COMPLIANCE | "Potential non-compliance detected" | A required declaration is confidently missing, invalid, or below threshold |
| NEEDS_REVIEW | "More evidence or human review required" | Evidence, context, measurement, or applicability is uncertain |

Every report must show: checks performed, checks not performed, evidence image, confidence level, rule version, reasons for review, and a screening disclaimer.

**Evidence UI:** SVG overlays (simpler than Canvas for MVP coordinate scaling/click interaction). Colors: green = passed, red = potential issue, yellow = uncertain, grey = not checked. Clicking evidence shows detected value, expected check, rule ID/version, confidence, and reason.

---

## 11. BARCODE, FONT SCREENING, GSTIN/GTIN

**Barcode pipeline:** detection → symbology classification → complete-symbol validation → decoding → geometry measurement → scale confidence estimation → association with nearby text.
Outcomes: `VALIDATED_SCALE_REFERENCE`, `DECODED_BUT_UNSUITABLE_FOR_SCALE`, `PARTIAL_OR_DISTORTED_BARCODE`, `BARCODE_NOT_FOUND`, `BARCODE_CONFLICT`. A barcode from another product, or a partial/distorted one, must never be used for measurement.

**Font/legibility screening is approximate, not a legal measurement.** Use the barcode as a scale reference only when: symbology + full geometry validated, perspective distortion estimated, barcode and text confirmed on the same plane, minimum pixel-per-mm resolution met. Report a measured height + applicable threshold + confidence interval + scale source + status — never a single unsupported number. Use the rule-specific threshold, not a universal 2mm assumption. No suitable barcode → NEEDS_REVIEW.

**GSTIN/GTIN — call this "consistency screening," not verification:**
- GSTIN: format, checksum (where supported), state-code consistency, local-record match, printed entity/address comparison.
- GTIN: barcode decode, identifier format, local product-record match, brand/name consistency.
- Outcomes: `FORMAT_VALID`, `LOCAL_DATABASE_MATCH`, `EXTERNAL_DATABASE_MATCH`, `CONFLICT_DETECTED`, `DATABASE_UNAVAILABLE`, `NOT_VERIFIABLE`.
- The local, clearly-labelled reference dataset is the dependable MVP path. Live external government API access is optional and must never block the core scanner — hide it behind a provider interface.

---

## 12. CITIZEN INTELLIGENCE & ENFORCEMENT LAYERS

**Citizen reporting flow:** notice concern → scan product (optional) → AI screening → report additional concern → select issue category (Suspicious MRP, Label Tampering, Missing Information, Quantity Concern, Information Mismatch, Other) → description + evidence → optional consent-based location → submit → unverified signal.
Required UI text: *"Your report is a signal for review. It is not a confirmed legal violation."* No public accusation before human verification. Include basic rate limiting.

**Unified signal schema** (AI and citizen signals share this shape, with source-specific provenance):
```json
{
  "signal_id": "SIG001",
  "source": "AI",
  "product_id": "PROD001",
  "issue_type": "MRP_SUSPICION",
  "confidence": 0.86,
  "status": "UNVERIFIED",
  "evidence_ids": ["EV12"]
}
```
**Duplicate detection (MVP):** GTIN exact match + normalized product/brand similarity + perceptual image hash + issue category. Mark likely duplicates — never auto-delete reports.
**Clustering key:** `canonical_product_id + issue_type`, aggregating unique reporters, AI flags, evidence quality, recency, officer outcomes.

**Prioritization score (operational heuristic, not a probability of guilt):**
```
priority = 0.25 * normalized_unique_citizen_reports
         + 0.20 * normalized_ai_flags
         + 0.20 * confirmed_case_signal
         + 0.15 * evidence_quality
         + 0.10 * severity_weight
         + 0.10 * recency
         - rejected_signal_penalty
```
Keep weights configurable; show contributing factors to officers. AI-only flags must never auto-trigger enforcement — a human officer must verify evidence before an issue is "confirmed."

**Officer dashboard sections:** Priority Queue, Product Intelligence Profile, Evidence Viewer, Review Actions (Confirm / Reject / Request More Evidence / Mark Under Investigation), Audit Trail (officer, timestamp, decision, rationale).

---

## 13. DATABASE SCHEMA (core entities)

`USERS, PRODUCTS, SCANS, IMAGES, OCR_RESULTS, EXTRACTED_FIELDS, RULE_PROFILES, RULE_RESULTS, EVIDENCE, VIOLATION_SIGNALS, CITIZEN_REPORTS, PRODUCT_CLUSTERS, RISK_SCORES, OFFICER_REVIEWS, DECISION_TRACES, LOCATION`

Core relationships: `USER→SCAN`; `SCAN→IMAGE/OCR_RESULT/EXTRACTED_FIELD/RULE_RESULT`; `PRODUCT→SIGNAL→CLUSTER→RISK_SCORE`; `CITIZEN_REPORT→SIGNAL`; `OFFICER_REVIEW→SIGNAL or CLUSTER`.

**Decision traceability (every scan must store):** input image hash + timestamp, OCR model version, extraction version, barcode detector version, rule-set version, threshold profile, rule-by-rule status, evidence bounding boxes, confidence values, human-review status/overrides — so any result can be explained after model/rule/threshold updates.

Storage: PostgreSQL (SQLite acceptable early), object storage for images, perceptual hashes for duplicate detection, access controls on evidence and consent-gated location data.

---

## 14. BACKEND API BLUEPRINT

| Endpoint | Purpose |
|---|---|
| `POST /api/v1/scans` | Create scan / upload image |
| `GET /api/v1/scans/{id}` | Processing status, verdict, evidence |
| `POST /api/v1/ocr/process` | Internal OCR processing |
| `GET /api/v1/products/{id}` | Product intelligence profile |
| `POST /api/v1/reports` | Create citizen report/signal |
| `GET /api/v1/reports` | Officer/admin report list |
| `GET /api/v1/officer/queue` | Prioritized investigation queue |
| `POST /api/v1/officer/reviews` | Human confirm/reject/review |
| `GET /api/v1/dashboard/statistics` | Dashboard metrics |
| `GET /api/v1/dashboard/priority-products` | Ranked product clusters |

For long-running scans: return `scan_id` + processing state immediately; poll or push status async rather than blocking the HTTP request.

---

## 15. REPOSITORY STRUCTURE

```
lm-screen/
  frontend/src/{pages, components, features, services, types}/
  backend/app/{api, core, models, schemas, services}/
  backend/pipeline/{quality, vision, ocr, extraction, context, rules, verdict}/
  backend/intelligence/{matching, clustering, prioritization}/
  backend/providers/{storage, llm, verification}/
  rule_profiles/
  datasets/
  tests/{unit, integration, adversarial}/
  docs/
  docker-compose.yml
  README.md
```
Keep every pipeline stage independently testable. **The frontend renders server decisions but never contains legal-rule logic.**

---

## 16. FRONTEND SCREENS

| Screen | Must show |
|---|---|
| Home | LM-Screen branding, Scan Product, Report Suspicious Product, Scan→Analyze→Review flow |
| Camera/Upload | Preview, upload, capture instructions, quality guidance |
| Processing | Quality → package → OCR → extraction → rules progress |
| Screening Result | Three-state status, checklist, evidence image, bounding boxes, rule explanation |
| Citizen Report | Issue selection, description, evidence, consent, disclaimer |
| Officer Dashboard | Priority products, clusters, signals, evidence confidence, review actions |

Design language: modern, clean, trustworthy, government-tech, mobile-first, evidence-focused. Avoid excessive futuristic/neon styling.

**User capture guidance to surface in-app:** move closer; avoid glare; one product at a time; photograph the info panel; include the complete barcode; keep the package flat; capture manufacturer and MRP areas separately if needed.

---

## 17. TESTING & SAFETY RULES

**Unit tests:** MRP patterns, quantity normalization, date extraction, GSTIN checksum, address extraction, country-of-origin detection, rule applicability, exemption handling, verdict aggregation.
**Integration tests:** image→OCR→fields→rule engine→report→dashboard; barcode→scale estimate.
**Adversarial tests:** fake/partial barcode, barcode from another product, multiple MRP values, best-before vs. manufacture-date confusion, marketing text containing an MRP-like number, institutional package, imported product, blur, glare, wrong panel, multiple packages, mixed Hindi-English text.

**The system MUST return NEEDS_REVIEW when:** OCR confidence is too low; relevant text isn't visible; package context is unknown; a possible exemption exists; multiple products are present; the barcode is unsuitable for scale; the applicable rule profile is unknown; the image is severely distorted/blurred; conflicting values are detected; a database source is unavailable; the result would depend only on an illustrative/mock record.

**Evaluation metrics to report separately:** image-quality retake detection accuracy; OCR character-error-rate/word accuracy; field precision/recall/F1; normalization accuracy; bounding-box localization; barcode detection/decoding/scale-validation accuracy; rule-engine false-positive/false-negative rates; correct exemption handling; NEEDS_REVIEW routing rate; end-to-end processing time.

---

## 18. TEAM ALLOCATION (6 members)

| Member | Ownership |
|---|---|
| P1 | Computer vision + image quality + package/panel detection |
| P2 | OCR + field extraction + Hindi-English normalization + confidence scoring |
| P3 | Rule engine + three-state verdict logic + decision trace + database |
| P4 | Barcode + font/scale measurement + GSTIN/GTIN consistency screening |
| P5 | Frontend — scanner, upload flow, evidence overlay, report screens |
| P6 | Integration + citizen reporting + clustering/prioritization dashboard + testing + demo |

**Risk fallbacks:** OCR weak → manual crop / cloud OCR benchmark. Contour detection fails → manual ROI selection. Barcode unreadable → OCR-based identity only, skip scale measurement. External API unavailable → local validation/reference data via provider adapter. LLM unavailable → deterministic logic/templates. Cloud issue → local Docker demo deployment.

---

## 19. DEMONSTRATION FLOW (for the pitch/demo)

1. Upload a clean product image → **No issue detected**.
2. Upload a seeded image with a missing declaration → **Potential non-compliance detected**, with evidence shown.
3. Upload an intentionally blurry image → **Needs human review**.
4. Submit a citizen report → unverified signal created.
5. Submit repeated seeded reports on the same product → cluster forms + priority score appears.
6. Officer reviews the queue → confirms or rejects → audit trail recorded.

**Narrative for the pitch:** "AI detects → Citizens report → System connects patterns → Authorities investigate → Human verification creates feedback." Always state explicitly on a limitations slide: this is a screening tool, not a legal judge.

---

## 20. FINAL DIFFERENTIATORS

- Evidence-first screening — every result links to source text, image region, rule ID, and confidence.
- Three-state result — uncertain images are never forced into pass/fail.
- Conditional barcode-based physical-scale screening — used only after validation, always with an uncertainty interval (differentiator vs. competitors who ask users to place a coin next to the label).
- Rule-applicability profiles — rules selected by product context, not one universal checklist.
- GSTIN/GTIN consistency screening — identifier matches kept separate from legal-compliance claims.
- Human-review intelligence — citizen reports + AI flags prioritize investigation but never establish violations automatically.

---

## 21. FINAL LIMITATIONS STATEMENT (must appear in the product and the pitch)

> This platform performs image-based Legal Metrology compliance screening for selected visible declarations. It does not replace inspection by an authorized officer, legal interpretation, laboratory testing, physical package measurement, or official enforcement procedures. Results depend on image quality, available declarations, product classification, rule version, and evidence confidence.

---

## 22. HOW TO USE THIS PROMPT WITH AN AI CODING AGENT

When instructing an agent (Claude Code, Antigravity, Gemini, Cursor, etc.) to generate code from this document:
1. Paste this entire document as system/context.
2. Ask for **one stage at a time**, in the Section 5 build order — do not ask for the whole system in one shot.
3. For each stage, explicitly ask the agent to: (a) implement the stage, (b) write the unit/integration tests listed for it in Section 17, (c) confirm which NEEDS_REVIEW safety rules from Section 17 apply to that stage.
4. Never let the agent skip the three-state model or the disclaimer text in Sections 10, 12, and 21 — treat those as hard constraints, not suggestions.
5. Before wiring in any external API (GSTIN government registry, cloud OCR, etc.), confirm it's implemented behind a provider interface per Section 4/11, with the local/offline fallback working first.
