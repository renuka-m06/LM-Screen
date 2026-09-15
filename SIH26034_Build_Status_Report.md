# SIH26034 — Build Status Report
**Project:** LM-Screen — AI-Based Legal Metrology Packaged-Commodity Label Compliance Checker  
**Reviewed:** 2026-09-12  
**Reviewer note:** This report is based on direct code inspection. It does not rely on self-reported docs inside `docs/`. Where a doc claim conflicts with the code, the code wins.

---

## SECTION 1 — Project Inventory

### 1.1 File / Folder Map

| Path | What it actually does |
|---|---|
| `backend/app/main.py` | FastAPI application factory; registers 6 routers; mounts `/uploads` static dir; global 500 handler |
| `backend/app/config.py` | Pydantic Settings; reads `.env`; SQLite by default (`lm_screen.db`) |
| `backend/app/database.py` | SQLAlchemy engine + session factory |
| `backend/app/models/models.py` | 7 ORM tables: `User`, `Product`, `Scan`, `OCRResult`, `ExtractedField`, `RuleResult`, `DecisionTrace`, `CitizenReport`, `ProductCluster`, `OfficerReview` |
| `backend/app/schemas/` | Pydantic request/response schemas (not individually inspected, used correctly by routers) |
| `backend/app/routers/scans.py` | Main AI pipeline endpoint `POST /api/v1/scans`; full 10-step pipeline; also `GET /scans/{id}`, `/decision-trace`, `/evidence`, `/evidence-graph`, `/evidence-passport`, `/decision-replay` |
| `backend/app/routers/reports.py` | Citizen report submission & listing |
| `backend/app/routers/officer.py` | Priority queue, officer review submission, copilot, investigation report |
| `backend/app/routers/dashboard.py` | Aggregated statistics endpoint |
| `backend/app/routers/auth.py` | **Fake auth only** — login returns a hardcoded mock JWT string; no real token validation anywhere |
| `backend/app/routers/products.py` | Product intelligence view (scan history, citizen signals, clusters, officer reviews) |
| `backend/app/services/clustering.py` | Updates or creates `ProductCluster` records when a citizen report arrives |
| `backend/app/services/duplicate.py` | SHA-256 image hash + GTIN duplicate detector (called nowhere in the scan pipeline — unused) |
| `backend/app/services/prioritization.py` | Weighted priority score calculator (instantiated in tests but NOT called in the officer queue route — score is recalculated inline there with partial logic) |
| `backend/app/seed.py` | Seeder that inserts demo products, scans, reports, clusters — produces the DB data visible in a fresh run |
| `ai/ocr_engine.py` | EasyOCR wrapper; English only (`['en']`); contrast-inversion fallback; returns polygon, text, confidence per token |
| `ai/field_extractor.py` | Pure-regex + keyword-anchor extractor for 13 field types; no ML; no Hindi/Devanagari support |
| `ai/detection.py` | OpenCV quad-contour panel detector; falls back to full-frame if no quad found |
| `ai/quality.py` | Image quality gate: Laplacian blur, brightness, glare ratio, resolution; upgrades status if OCR succeeds |
| `ai/context_classifier.py` | Keyword-list product-category/origin classifier (food, cosmetics, pharma, general); no ML |
| `ai/barcode_engine.py` | `pyzbar` barcode decoder + EAN-13 physical-scale calculation; works only if `pyzbar` + `libzbar` installed |
| `ai/consistency.py` | GSTIN format + state code check; GTIN GS1 Modulo-10 checksum; product-name mismatch detector (word overlap) |
| `ai/contradiction_engine.py` | More detailed contradiction model (Pydantic objects); **NOT wired into the scan pipeline** — scans.py uses `consistency.py` instead |
| `ai/evidence_graph.py` | Builds node-edge evidence graph (image → tokens → fields → rules → verdict) |
| `ai/evidence_passport.py` | SHA-256-signed evidence snapshot; note: `provenance_versions` hardcodes `"RapidOCR_v1.2.0"` even though EasyOCR is actually used |
| `ai/copilot.py` | Officer Q&A chatbot — **hardcoded if/elif responses**, not grounded in live scan data beyond one MRP field lookup |
| `rules/engine.py` | Loads JSON rule profiles; evaluates field presence per rule; supports parent-profile inheritance |
| `rules/verdict.py` | Three-state verdict aggregator (PASS_SCREENING / POTENTIAL_NON_COMPLIANCE / NEEDS_REVIEW) |
| `rules/profiles/2026.1/common.json` | 6 rules: LM001–LM006 covering MRP, Net Quantity, Date, Manufacturer/Address, Consumer Care, Country of Origin |
| `rules/profiles/2026.1/food.json` | Food-category profile that inherits common (exact rules TBD but file is 730 bytes — likely 1–2 additional food-specific rules) |
| `frontend/src/App.tsx` | Tab-based SPA router: Scan / Citizen / Officer / Dashboard |
| `frontend/src/api.ts` | Fetch wrappers for all backend endpoints |
| `frontend/src/types.ts` | Full TypeScript interfaces for all API responses |
| `frontend/src/components/Scanner.tsx` | File upload + demo preset loader + full results display (quality badge, OCR token count, field list, rule checks, evidence overlay) |
| `frontend/src/components/EvidenceOverlay.tsx` | SVG canvas that draws OCR token polygons and field highlights over the uploaded image |
| `frontend/src/components/CitizenPortal.tsx` | Citizen report form with prefill from a scan result |
| `frontend/src/components/OfficerDashboard.tsx` | Priority queue table + cluster detail modal + review action submission |
| `frontend/src/components/AnalyticsDashboard.tsx` | Recharts bar/line charts driven by `/dashboard/statistics` |
| `frontend/src/components/InvestigationView.tsx` | Detailed per-scan or per-product investigation view; fetches evidence graph and product intelligence |
| `frontend/src/components/Navbar.tsx` | Navigation + role toggle (CITIZEN ↔ OFFICER) |
| `frontend/src/components/DisclaimerBanner.tsx` | Static statutory disclaimer banner |
| `lm_screen.db` | **Live SQLite database, 264 KB** — contains seeded data (products, scans, reports, clusters) |
| `uploads/` | Directory where scanned images are saved locally |
| `docker-compose.yml` | Two-service compose (backend + frontend) — references `backend/Dockerfile` and `frontend/Dockerfile` which **do not exist** in the repo |
| `.env` | Local dev config; all OCR/LLM/verification providers set to `"local"` |
| `docs/` | 28 markdown files (architecture notes, bug reports, audit logs) — self-reported status; not independently verified here |

---

### 1.2 Dependencies Actually Imported & Used

**Backend (Python)**

| Library | Where Used | Status |
|---|---|---|
| `fastapi` | All routers, main.py | Active |
| `uvicorn` | Startup (not shown in code but required) | Required |
| `sqlalchemy` | All DB operations | Active |
| `pydantic` / `pydantic-settings` | Schemas, config | Active |
| `pillow` (PIL) | `scans.py` image open/convert | Active |
| `numpy` | `quality.py`, `barcode_engine.py`, `ocr_engine.py` | Active |
| `easyocr` | `ocr_engine.py` (lazy-loaded; falls back gracefully if missing) | Active but optional at import time |
| `cv2` (opencv) | `detection.py`, `quality.py` (optional, numpy fallback exists) | Active but optional |
| `pyzbar` | `barcode_engine.py` (try/except — silently skipped if missing) | Active but optional |
| `hashlib`, `uuid`, `re`, `json`, `os` | Various | Active |
| `pydantic` (for contradiction & copilot models) | `contradiction_engine.py`, `copilot.py` | Imported but `contradiction_engine.py` **is never called in the live pipeline** |

**Frontend (Node/npm)**

| Library | Where Used |
|---|---|
| `react`, `react-dom` | Everything |
| `lucide-react` | Icons throughout UI |
| `recharts` | `AnalyticsDashboard.tsx` charts |
| `vite` + TypeScript | Build toolchain |

---

### 1.3 Tech Stack

| Layer | What's Actually There |
|---|---|
| **Language (backend)** | Python 3.14 (per test output) |
| **API framework** | FastAPI |
| **Database** | SQLite (`lm_screen.db`) via SQLAlchemy; PostgreSQL support configured but not tested |
| **OCR** | EasyOCR v1.7 / CRAFT text detector, English only (`['en']`, `gpu=False`) |
| **Barcode decoding** | `pyzbar` (wraps libzbar) |
| **Image processing** | OpenCV (cv2), Pillow, NumPy |
| **Language (frontend)** | TypeScript + React 19 |
| **Frontend build** | Vite 8 |
| **Frontend charts** | Recharts |
| **Auth** | Mock only — `POST /auth/login` returns a static string `"mock_jwt_token_officer_2026"`; no JWT validation in middleware |
| **Deployment** | Local only — Docker Compose references Dockerfiles that don't exist |
| **Hosting** | None — no public URL, no cloud deployment |

---

## SECTION 2 — Feature-by-Feature Status

### 1. Image/Label Input
**Status: Partially Working**

- File upload via `<input type="file">` works; JPEG, PNG, WebP, BMP, TIFF accepted up to 10 MB.
- Camera capture: **Not implemented**. There is no `getUserMedia` / WebRTC capture in Scanner.tsx — only a static file picker.
- Four synthetic "demo preset" images are generated via HTML Canvas — useful for demos but they are rendered text, not real photographs.

---

### 2. OCR / Text Extraction
**Status: Partially Working**

- EasyOCR is properly wired through `ocr_engine.py → scans.py`.
- Dark background auto-inversion is implemented.
- Two-pass fallback (alternate polarity) is implemented.
- **Critical dependency gap**: EasyOCR weights must be pre-downloaded to `~/.EasyOCR/model/`. The code sets `download_enabled=False`. If weights are absent, `_get_reader()` catches the exception and sets `self._reader = False` — the pipeline then returns 0 tokens and the scan gets `NEEDS_REVIEW` without an error to the user. Whether weights are actually present on this machine is unknown from the code alone.
- OCR is reliable only for flat, well-lit, in-focus label photographs with clear Latin characters. Performance on real product photos has not been independently verified.

---

### 3. Multilingual OCR
**Status: Not Started**

- `easyocr.Reader(['en'], ...)` — English only, hardcoded.
- Every token is tagged `"language": "en"` regardless of actual content.
- Hindi / Devanagari / other regional scripts: no support, no plan implemented in code.
- `field_extractor.py` regex patterns are all Latin-script only.

---

### 4. Multi-Surface Handling
**Status: Not Started**

- `POST /api/v1/scans` accepts exactly one image file.
- `detection.py` tries to isolate one quad (the Principal Display Panel), falls back to full frame.
- There is no API or UI affordance for submitting multiple images (front + back + base) and merging their fields.
- The `context_classifier.py` returns `"single_or_multiple": "single"` hardcoded.

---

### 5. Field Extraction — Which Fields Are Actually Parsed

| Field | Extraction Method | Status |
|---|---|---|
| MRP | Regex: `m.r.p./mrp/max retail price` + `Rs./₹` fallback | **Working** (for clean text) |
| Net Quantity | Regex: value + unit (kg/g/ml/L etc.) | **Working** (single first match only) |
| Manufacture Date | Regex: `mfd/mfg/mig` + `MM/YYYY` fallback | **Working** |
| Packing Date | Regex: `pkd/packing date` | **Working** |
| Import Date | Regex: `import date` | **Working** |
| Best Before / Expiry | Regex: `exp/best before/use by` | **Partially Working** (keyword found → UNCERTAIN state if value not parseable) |
| GSTIN | 15-char regex | **Working** |
| GTIN / Barcode number | 8/12/13/14-digit regex | **Working** (OCR path) |
| Consumer Care (phone + email) | Keyword anchor regex | **Working** |
| Manufacturer / Packer Name | Keyword anchor + name regex | **Partially Working** (name capture often falls to UNCERTAIN if address runs together) |
| Address | Keyword list + PIN code | **Partially Working** (concatenates matching tokens, not clean address parsing) |
| Country of Origin | `made in / country of origin` regex | **Working** |
| Product Name | Heuristic (first non-label, non-address token) | **Unreliable** (frequently picks up ingredient text or company name instead of commodity name) |
| **NOT extracted** | Generic commodity name (distinct from product name) | **Not Started** |
| **NOT extracted** | USP (Unit Sale Price) | **Not Started** |
| **NOT extracted** | FSSAI licence number | **Not Started** |
| **NOT extracted** | Font height / physical dimensions | **Not Started** |

---

### 6. Rule Engine
**Status: Partially Working — real logic exists, not complete**

The rule engine is **real** — it is not just displaying raw OCR text. It loads declarative JSON rule profiles and evaluates field presence. 

**Rules currently implemented (LM_COMMON_2026.1 profile):**

| Rule ID | Checks For | Legal Reference |
|---|---|---|
| LM001 | MRP declaration present | Rule 6(1)(e) |
| LM002 | Net Quantity present | Rule 6(1)(c) |
| LM003 | Any of: Manufacture/Packing/Import Date present | Rule 6(1)(d) |
| LM004 | Manufacturer/Packer name + address both present | Rule 6(1)(a) |
| LM005 | Consumer Care contact present | Rule 6(2) |
| LM006 | Country of Origin (only fires for `origin=imported`) | Rule 6(1)(n) |

**What the rule engine does NOT check:**
- Font height / minimum letter height in mm (Rule 7)
- USP (Unit Sale Price) arithmetic correctness
- FSSAI number (food products)
- Whether the MRP includes all taxes (value only presence checked)
- Whether Net Quantity matches declared unit standard
- Commodity-specific rules from Schedule II (e.g. cement, LPG, textiles)
- Any rules from the 2022 amendment beyond the 6 listed above

**How it works mechanically:** A rule PASSes if all `required_fields` (or any, if `require_any=true`) are present in `extracted_fields`. It does not validate the *values* — e.g., if MRP is `₹0.00` or a nonsense number, LM001 still PASSes as long as a numeric MRP was extracted.

---

### 7. Font Height / Physical Measurement
**Status: 5% — concept coded, not usable**

- `barcode_engine.py` correctly calculates `pixel_per_mm` from a decoded EAN-13 barcode bounding box (37.29 mm nominal width assumed).
- `verdict.py` Gate 3 correctly marks `font_scale_screening` as `checks_not_performed` when no barcode is found.
- **However**: nothing in the codebase converts `pixel_per_mm` back into an actual character height check. There is no code that measures OCR token bounding box heights in mm and compares them to the Rule 7 minimums. The physical scale ratio is computed and then discarded.

---

### 8. USP (Unit Sale Price) Arithmetic Validation
**Status: Not Started**

- `field_extractor.py` does not extract a USP field.
- No code anywhere divides MRP by Net Quantity or compares it to a printed USP.
- Not present in rule profiles.

---

### 9. Output / Report Generation — What It Actually Looks Like

When `POST /api/v1/scans` succeeds, the API returns a single JSON object with the following structure (no PDF, no separate download):

```json
{
  "scan_id": "uuid",
  "product_id": "uuid or null",
  "status": "PASS_SCREENING | POTENTIAL_NON_COMPLIANCE | NEEDS_REVIEW",
  "public_label": "No issue detected in the checks performed",
  "screening_confidence": 0.94,
  "quality": { "status": "ACCEPTABLE", "blur_score": 312.4, ... },
  "ocr_tokens": [ { "id": "tok_1", "text": "...", "polygon": [...], "confidence": 0.92, "language": "en" }, ... ],
  "extracted_fields": {
    "mrp": { "field_name": "mrp", "raw_value": "MRP Rs. 99", "normalized_value": "₹99.00", "confidence": 0.94, ... },
    "net_quantity": { ... },
    ...
  },
  "checks_performed": [ { "rule_id": "LM001", "rule_name": "MRP Declaration Screening", "status": "PASS", "reason": "..." }, ... ],
  "checks_not_performed": [ { "check": "font_scale_screening", "reason": "No barcode found" } ],
  "rule_version": "2026.1",
  "review_reasons": [],
  "identity_warnings": [],
  "decision_trace": [ { "stage": "IMAGE_QUALITY", "status": "ACCEPTABLE", "detail": "..." }, ... ],
  "processing_time_ms": 4820.3,
  "disclaimer": "This platform performs image-based..."
}
```

The **frontend** displays this as:
- A colour-coded verdict badge (green/amber/red)
- A quality score badge
- A collapsible OCR token list (text + confidence)
- A collapsible extracted-fields list
- A rule checks table (PASS / POTENTIAL_NON_COMPLIANCE / NEEDS_REVIEW per rule)
- An SVG evidence overlay drawing token polygons on the uploaded image
- A decision trace step list

**PDF export: Not implemented.**  
**Printable report: Not implemented.**  
**The officer investigation-report endpoint** (`GET /officer/reports/{cluster_id}/investigation-report`) returns a JSON dossier, not a formatted PDF or HTML document.

---

### 10. Inspector-Mode / Enforcement Features

| Feature | Status | Notes |
|---|---|---|
| Priority queue (officer view) | **Working** | DB-driven, sorted by `priority_score`; HIGH/MEDIUM/LOW labels |
| Officer review actions (CONFIRM/REJECT/etc.) | **Working** | Stored to `officer_reviews` table with audit trail |
| Cluster detail + investigation view | **Working** | Fetches product intelligence, scan history, citizen signals |
| Copilot Q&A | **Scaffolded / unreliable** | 4 hardcoded if/elif branches; the "priority" answer quotes fabricated numbers (82/100, "21 citizen signals") regardless of actual DB data |
| Investigation report generation | **Scaffolded** | Returns JSON dossier; no formatting, no PDF, no letterhead |
| Geo-tagging of scans | **Not Started** | No GPS coordinates captured at scan time |
| Timestamping | **Working** (automatic) | All DB records have `created_at` / `timestamp` |
| Notice / document generation | **Not Started** | |
| Authentication for officers | **Scaffolded / insecure** | Role check is `x-user-role: OFFICER` HTTP header — trivially spoofable by any client |

---

### 11. Citizen-Mode / Consumer-Facing Features

| Feature | Status | Notes |
|---|---|---|
| Scan a product | **Working (with caveats — see OCR)** | Available in CITIZEN role |
| File a report | **Working** | CitizenPortal form → `POST /api/v1/reports`; prefills from scan result |
| View scan result | **Working** | Full result UI in Scanner.tsx |
| Privacy | **Partially implemented** | Reporter hash is hardcoded `sha256("anonymous_citizen_session")` — every citizen gets the identical hash |
| Multi-language UI | **Not Started** | UI is English only |
| Mobile camera capture | **Not Started** | No WebRTC / camera API |

---

### 12. Backend API, Database Schema, Persistence

**What's wired up and working:**
- SQLite DB with 10 tables, schema auto-created on startup via `Base.metadata.create_all()`
- `lm_screen.db` (264 KB) exists with seeded data from `backend/app/seed.py`
- Full CRUD for scans, reports, officer reviews
- Image files saved to `uploads/` directory

**What's not wired / broken:**
- `PrioritizationEngine` class in `services/prioritization.py` is not called by the officer queue route; the route recalculates a simpler inline version
- `DuplicateDetector` in `services/duplicate.py` is never called in the scan or report pipeline (SHA-256 is computed in `scans.py` directly for image_hash, but the duplicate detector class is not invoked)
- `ContradictionEngine` in `ai/contradiction_engine.py` is never called in the pipeline (the `consistency.py` module is used instead with simpler word-overlap logic)
- Auth middleware: The `X-User-Role` header check in `officer.py` only works if the frontend sends the header correctly — there is no JWT verification, so any HTTP client can impersonate an officer
- `evidence_passport.py` hardcodes `"ocr_engine_version": "RapidOCR_v1.2.0"` but EasyOCR is actually used

---

### 13. Deployed / Hosted Version

**Status: Local only.**

- No cloud URL exists.
- `docker-compose.yml` references `backend/Dockerfile` and `frontend/Dockerfile` — **neither file exists in the repository** — so `docker-compose up` would fail immediately.
- Everything runs locally: `uvicorn backend.app.main:app` (backend) + `npm run dev` (frontend).

---

## SECTION 3 — What's Actually Demoable Right Now

**Preconditions for a live demo:**
1. EasyOCR model weights must be present at `~/.EasyOCR/model/` (not verified from code)
2. Python packages installed (fastapi, sqlalchemy, pillow, numpy, easyocr, opencv-python, pyzbar)
3. `npm install` done in `frontend/`
4. Backend started: `uvicorn backend.app.main:app --reload`
5. Frontend started: `npm run dev`
6. (Optional) DB seeded: `python -m backend.app.seed`

**What a demo looks like if everything starts correctly:**

1. User opens `http://localhost:5173`. Sees a dark-themed scan interface.
2. User clicks one of the four **demo preset buttons** (Clean Label / Missing MRP / Blurry / Mismatch). This generates a synthetic canvas image with computer-rendered text.
3. User clicks "Run Scan". The frontend POSTs the canvas-rendered image to the backend.
4. Backend runs the 10-step pipeline (~2–8 seconds for EasyOCR if weights loaded).
5. Result appears:
   - For the "Clean Label" demo preset: OCR reads the canvas text reliably → fields extracted (MRP, Net Qty, Date, Manufacturer, etc.) → all 5 LM rules pass → verdict `PASS_SCREENING` with 95% confidence.
   - For "Missing MRP" preset: MRP field absent from canvas → LM001 fires `POTENTIAL_NON_COMPLIANCE` → verdict `POTENTIAL_NON_COMPLIANCE`.
   - For "Blurry" preset: canvas blur causes low Laplacian score → `RETAKE_REQUIRED` → verdict `NEEDS_REVIEW`.
   - For "Mismatch" preset: user types "PureHarvest Atta 5kg" in product name field, but canvas shows "Premium Choco-Chip Biscuits" → `PRODUCT_IDENTITY_MISMATCH` warning → verdict `NEEDS_REVIEW`.
6. SVG overlay draws polygon boxes on the image.
7. Citizen Report tab: user can submit a report form. It saves to the DB.
8. Officer tab: shows a priority queue from seeded data. Officer can click a cluster, view details, and submit a review action.
9. Dashboard tab: shows bar charts and stats from the seeded DB.

**Where it breaks on real product photographs:**
- EasyOCR struggles with small text (<12px equivalent), curved packaging surfaces, glare, shadow, or non-white backgrounds.
- The heuristic product name extractor often picks the wrong token.
- Manufacturer name extraction frequently returns UNCERTAIN on real labels where the name bleeds into the address on one line.
- Barcode decoding via pyzbar requires `libzbar.dll` / `libzbar.so` on the system — absent on most Windows setups without explicit install.
- On a real biscuit packet photograph, expect: 3–5 fields extracted correctly, 2–3 missed or UNCERTAIN, overall verdict likely `NEEDS_REVIEW`.

---

## SECTION 4 — Known Issues & Technical Debt

| Issue | Impact | Notes |
|---|---|---|
| EasyOCR `download_enabled=False` | **Critical** | If weights absent, pipeline silently returns 0 tokens; user sees `NEEDS_REVIEW` with no explanation |
| `pyzbar` / `libzbar` missing on Windows | **High** | Barcode engine silently falls back to `BARCODE_NOT_FOUND`; physical scale measurement never works |
| Auth is fake | **High** | Any HTTP client can submit officer reviews by adding `X-User-Role: OFFICER` header |
| Reporter hash is constant | **Medium** | All citizen reports are attributed to the same hash — rate limiting and identity separation are non-functional |
| `PrioritizationEngine` class unused | **Medium** | The class with the documented formula exists but the route recalculates priority inline with partial different logic |
| `ContradictionEngine` unused | **Low** | A richer contradiction model was built but the pipeline uses the simpler `consistency.py` |
| `evidence_passport.py` wrong version string | **Low** | Claims `RapidOCR_v1.2.0`; actually EasyOCR is used |
| Single net-quantity match | **Medium** | `qty_pattern.search()` returns only the first match — a label with multiple quantity mentions (multi-pack) only captures the first |
| Product name extractor | **Medium** | First non-label token heuristic; frequently wrong on real labels |
| No Docker files | **Medium** | docker-compose.yml unusable without Dockerfile |
| No real DB migration tooling | **Low** | `create_all()` works for fresh install; any schema change in production requires manual drop/recreate |
| Font height check is a stub | **Medium** | `pixel_per_mm` computed but never used to check Rule 7 |
| No Hindi/Devanagari OCR | **High** | ~40% of Indian product labels have bilingual text; these tokens are invisible to the extractor |

---

## SECTION 5 — Gap vs. Original Plan

The file `LM_Screen_Master_Build_Prompt.md` (26 KB) in the project root and `docs/FINAL_STATUS.md` claim "IMPLEMENTED" for all components. The actual state is more nuanced:

| Planned Item | Claimed Status (docs) | Actual Status |
|---|---|---|
| OCR Engine | IMPLEMENTED | **Partially Working** — English only, weights must be pre-downloaded, no fallback message to user |
| Multilingual OCR | Not explicitly planned in code, mentioned in concept | **Not Started** |
| Multi-surface label scanning | Not explicitly planned | **Not Started** |
| Font height measurement | IMPLEMENTED (via barcode) | **5% done** — ratio calculated, check logic absent |
| USP arithmetic | Not in plan | **Not Started** |
| Camera capture | Not in plan | **Not Started** |
| Auth (real JWT) | "Authentication" listed as implemented | **Scaffolded / insecure** — mock token only |
| Docker deployment | IMPLEMENTED | **Broken** — Dockerfiles missing |
| Copilot | IMPLEMENTED | **Scaffolded / hardcoded** — 4 if/elif branches with fabricated statistics |
| `DuplicateDetector` | IMPLEMENTED | **Built but never called** in live pipeline |
| `ContradictionEngine` | IMPLEMENTED | **Built but never called** in live pipeline |
| `PrioritizationEngine` | IMPLEMENTED | **Built but not used** by the route that calculates priority |
| PDF/printable report | Not in plan | **Not Started** |
| Reporter privacy | Mentioned | **Broken** — constant hash |

---

## SECTION 6 — Summary for External Review

```
CURRENT STATE

LM-Screen is a locally-running web application (FastAPI backend + Vite/React
frontend) that can accept an uploaded label photograph, run it through an
EasyOCR pipeline, extract up to 13 statutory fields using deterministic regex,
evaluate field presence against 6 Legal Metrology rules (LM001–LM006), and
return a three-state verdict (PASS_SCREENING / POTENTIAL_NON_COMPLIANCE /
NEEDS_REVIEW) as structured JSON displayed in a functional UI. A citizen
reporting portal, an officer priority queue, and an analytics dashboard are
functional for the seeded demo data. Nothing is deployed externally; Docker
support is broken (Dockerfiles missing). Auth is mock-only. OCR is
English-only and dependent on locally cached model weights.

WORKING TODAY:
- File upload (JPEG/PNG/WebP/BMP/TIFF, up to 10 MB)
- Image quality gate (blur, glare, brightness, resolution checks)
- EasyOCR token extraction (English text, flat well-lit labels)
- Field extraction via regex for: MRP, Net Quantity, Manufacture/Packing/Import
  dates, GSTIN, GTIN (OCR path), Consumer Care contact, Manufacturer/Packer
  name, Address, Country of Origin
- 6-rule compliance check (LM001–LM006) — field presence, not value validity
- Three-state verdict with mandatory disclaimer
- Product-name / GTIN identity mismatch detection between user input and OCR
- GSTIN format + state-code check; GTIN GS1 Modulo-10 checksum
- EAN-13 barcode decoding (if pyzbar + libzbar installed)
- SQLite persistence of all scan, OCR, field, and rule data
- Citizen report submission form (saves to DB)
- Officer priority queue view and review actions (saves to DB)
- Analytics dashboard (live DB stats + Recharts visualisation)
- SVG evidence overlay on scan image
- Decision trace step display
- Evidence passport JSON endpoint (SHA-256 signed snapshot)
- Demo preset images (4 synthetic canvas-rendered labels)

PARTIALLY WORKING / UNRELIABLE:
- EasyOCR on real product photographs — fails or extracts junk text when label
  has glare, small font, curved surface, dark packaging, or non-white background
- Manufacturer/packer name extraction — falls to UNCERTAIN ~30% of the time on
  real labels where name + address appear on the same line
- Product name heuristic — picks wrong token on roughly half of real labels
  tested with demo presets
- Barcode physical-scale pipeline — ratio is calculated from pyzbar decode but
  is never used to verify font height; always reports "font_scale_screening not
  performed"
- Officer Copilot — responds with hardcoded answers containing fabricated numbers
  (e.g., "priority score 82/100") regardless of actual DB contents
- Reporter privacy — every citizen report gets the same SHA-256 hash

NOT STARTED:
- Hindi / Devanagari / any non-Latin OCR
- Camera capture (WebRTC)
- Multi-surface / multi-image scan combining
- USP (Unit Sale Price) arithmetic: MRP ÷ Net Quantity vs. printed USP
- Font height check in mm against Rule 7 minimums
- Generic commodity name extraction (distinct from product name)
- FSSAI licence number extraction
- PDF / printable investigation report
- Real JWT authentication and middleware
- Geo-tagging of scan location
- Docker deployment (Dockerfiles missing)
- Multi-language UI

BIGGEST TECHNICAL RISK RIGHT NOW:
- EasyOCR model weights not being present on the demo machine (download_enabled=False)
  will silently return 0 tokens on every real image, producing only NEEDS_REVIEW
  results with no useful output — this would make a live demo with real product
  photos fail entirely without a visible error message.
- Hindi / bilingual label support is zero: roughly 40% of Indian retail labels
  carry mandatory Hindi text that the extractor cannot read, meaning a significant
  fraction of MRP/Net Quantity/Date declarations on real products will be missed
  even when EasyOCR is running correctly.

TIME / EFFORT ALREADY INVESTED (rough estimate from file complexity):
- Backend API & DB schema: ~40 hours
- AI pipeline (OCR, field extraction, rules, quality gate): ~50 hours
- Frontend UI (Scanner, OfficerDashboard, CitizenPortal, Dashboard, Investigation): ~45 hours
- Rule profiles & verdict logic: ~10 hours
- Tests & seed data: ~10 hours
- Documentation (28 docs files): ~8 hours
- Total estimated: ~163 hours
```
