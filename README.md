# LM-Screen — AI-Based Legal Metrology Compliance Screening Platform

**SIH Problem Statement:** 25034 — Ministry of Consumer Affairs, Food & Public Distribution — Department of Consumer Affairs

> ⚠️ **ABSOLUTE PRODUCT PRINCIPLE:**
> LM-Screen is a **DECISION-SUPPORT SYSTEM**. It does NOT issue legal verdicts, replace authorized officers, or perform laboratory testing. All screening signals require human officer review.

---

## 1. Problem

Manual inspection of pre-packaged commodity labels by Legal Metrology officers is slow, unscalable, and leaves no digital evidence trail. Citizens who observe potential violations have no structured reporting channel. Multiple citizen observations about the same product cannot be aggregated.

---

## 2. Solution

LM-Screen provides:
1. **Automated evidence extraction** from product label images (OCR, barcode, CV)
2. **Deterministic rule evaluation** against Legal Metrology (Packaged Commodities) Rules 2011
3. **Citizen signal aggregation** — multiple observations clustered by product
4. **Evidence-based prioritization** — officer queue ranked by evidence weight
5. **Officer investigation workbench** — evidence inspection, correction, audit trail

---

## 3. Architecture

See [`docs/architecture/ARCHITECTURE.md`](docs/architecture/ARCHITECTURE.md) for the full Mermaid diagram.

**Pipeline summary:**
```
IMAGE → Quality Gate → Panel Detection (CV/YOLO*) → OCR + Barcode
     → Evidence Extraction → Product Identity → Context Classification
     → Rule Applicability → Consistency Engine → Evidence Quality
     → Deterministic Rules → Three-State Verdict
     → Citizen Clustering → Prioritization → Officer Workbench → Audit Trail
```

\* YOLO: Architecture implemented. Model not yet trained. OpenCV heuristic fallback active.

---

## 4. Features

| Feature | Status |
|---------|--------|
| Image quality gating | ✅ |
| OCR token extraction | ✅ |
| Barcode decoding | ✅ |
| 13+ statutory field extraction | ✅ |
| Product context classification | ✅ |
| Dynamic rule applicability engine | ✅ |
| Cross-evidence consistency engine | ✅ |
| Evidence quality intelligence | ✅ |
| Three-state legal safety model | ✅ |
| Citizen portal & signal aggregation | ✅ |
| Product cluster intelligence | ✅ |
| Evidence-based prioritization | ✅ |
| Officer investigation workbench | ✅ |
| Evidence correction + recalculation | ✅ |
| Audit trail (append-only) | ✅ |
| Analytics dashboard (4 layers) | ✅ |
| ML architecture (YOLO integration) | ✅ Architecture |
| YOLO panel detector (trained) | ❌ Model not trained |

---

## 5. Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + TypeScript + Vite |
| Backend | FastAPI (Python 3.10+) |
| Database | PostgreSQL (production) / SQLite (development) |
| OCR | PaddleOCR / EasyOCR |
| Barcode | pyzbar |
| CV Fallback | OpenCV |
| ML Architecture | Ultralytics YOLOv8 (weights pending) |
| ORM | SQLAlchemy |

---

## 6. Installation

### Prerequisites
- Python 3.10+
- Node.js v18+ & npm
- (Optional) PostgreSQL 14+

### Clone
```bash
git clone <your-repo-url>
cd LM
```

---

## 7. Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

**Critical variables:**

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | SQLite or PostgreSQL connection string | `sqlite:///./lm_screen.db` |
| `SECRET_KEY` | Secret key for future JWT signing | Change in production |
| `CORS_ORIGINS` | Allowed frontend origins | localhost:5173, :3000 |
| `ENV` | `development` or `production` | `development` |

> ⚠️ Never commit `.env` with real credentials. The `.env` file is in `.gitignore`.

---

## 8. Database Setup

### SQLite (default — no setup needed)
```bash
# DATABASE_URL=sqlite:///./lm_screen.db  (in .env)
# Tables created automatically on first backend start
```

### PostgreSQL
```bash
# Create database
psql -U postgres -c "CREATE DATABASE lmscreen;"

# Set in .env:
# DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/lmscreen
```

---

## 9. Running the Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Start the backend (auto-creates DB tables on first run)
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Health check: `GET http://localhost:8000/health` → `{"status": "ok"}`

---

## 10. Running the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`

**Demo login credentials:**
- Officer: `officer@legalmetrology.gov.in` / any password
- Citizen: any other email

---

## 11. ML Setup

The ML integration architecture is implemented. Model weights are not yet trained.

The system automatically detects model availability via `ModelRegistry`:
- If `models/detector.pt` exists → YOLO inference runs
- If not found → OpenCV heuristic fallback activates (current state)

This is displayed transparently on the Analytics Dashboard under "ML Model Health."

**To add trained weights in future:**
```bash
# Copy trained weights to:
models/detector.pt
# System will automatically switch from heuristic to YOLO
```

See `ML_READINESS_REPORT.md` for complete ML status and dataset requirements.

---

## 12. Current ML Status

> **Honest statement:** No training data has been collected. No model has been trained.
> All inference currently uses deterministic heuristic methods (OpenCV + regex).
> The YOLO architecture, evidence integration, and fallback mechanisms are implemented
> and ready to receive trained weights.

---

## 13. Demo Instructions

### Seed demo data
```bash
python scripts/seed_demo_data.py
```
Creates 8 synthetic scenarios tagged `SIH_DEMO_SYNTHETIC`.

### Reset demo data
```bash
python scripts/reset_demo_data.py --confirm
```
Deletes only demo-tagged records. Never affects non-demo data.

See `SIH_FINAL_DEMO_SCRIPT.md` for the full live demo walkthrough.

---

## 14. API Overview

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | System health |
| `/api/v1/scans` | POST | Upload image + run screening pipeline |
| `/api/v1/scans/{id}` | GET | Get scan result |
| `/api/v1/scans/{id}/findings` | GET | Get evidence + findings |
| `/api/v1/scans/{id}/evidence/{id}/correct` | POST | Officer evidence correction |
| `/api/v1/officer/queue` | GET | Prioritized officer review queue |
| `/api/v1/officer/reviews` | POST | Submit officer decision |
| `/api/v1/products/{id}/intelligence` | GET | Product cluster intelligence |
| `/api/v1/analytics/overview` | GET | System analytics |
| `/api/v1/analytics/system/health` | GET | ML model health status |
| `/api/v1/auth/login` | POST | Login (demo auth) |

Full API docs: `http://localhost:8000/docs`

---

## 15. Testing

```bash
# Run ML integration + adversarial tests (no PYTHONPATH setup needed with conftest.py)
pytest backend/tests/test_ml_integration.py backend/tests/test_adversarial.py -v

# Run all tests (some may require external dependencies)
$env:PYTHONPATH="$(pwd)"; pytest backend/tests/ -v
```

---

## 16. Known Limitations

1. **No trained ML model** — CV heuristic fallback is active
2. **Simplified authentication** — header-based role checking (not JWT)
3. **OCR accuracy not benchmarked** on Indian FMCG label corpus
4. **No GTIN product registry** — barcodes decoded but not verified
5. **English-only OCR** — Hindi/regional language text may not be extracted
6. **No rate limiting** on API endpoints
7. **Not load tested** — performance under concurrent users is unknown

---

## 17. Future Roadmap

1. Collect and annotate 1,000+ FMCG product images
2. Train YOLOv8 panel detector; measure real mAP metrics
3. Implement full JWT authentication
4. Add Hindi/regional language OCR
5. Build GTIN product registry integration
6. Add API rate limiting
7. Production deployment with horizontal scaling
8. Mobile-responsive PWA

---

## ⚖️ Legal Disclaimer

> *This platform performs image-based Legal Metrology compliance screening for selected visible declarations. It does not replace inspection by an authorized officer, legal interpretation, laboratory testing, physical package measurement, or official enforcement procedures. Results depend on image quality, available declarations, product classification, rule version, and evidence confidence.*
