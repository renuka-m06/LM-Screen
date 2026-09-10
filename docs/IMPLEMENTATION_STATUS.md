# LM-Screen — Implementation Status & Architecture Assessment

**Date:** September 9, 2026  
**System:** AI-Based Legal Metrology Compliance Screening, Citizen Intelligence & Enforcement Prioritization Platform  
**SIH Problem Statement:** 25034 — Department of Consumer Affairs  

---

## 1. Current Implementation State

* **Frontend:** Clean workspace initialized. Modern Vite + React + TypeScript + TailwindCSS / SVG Evidence overlay setup planned.
* **Backend:** FastAPI foundation with Pydantic v2 schemas and SQLAlchemy models planned.
* **Computer Vision & OCR:** OpenCV & EasyOCR/PaddleOCR pipeline architecture defined.
* **Database:** SQLite (local development) / PostgreSQL compatibility via SQLAlchemy ORM.
* **Rule & Verdict Engine:** External versioned YAML/JSON rule profiles (`rules/profiles`) with deterministic trace output.

---

## 2. Target Directory Structure

```text
LM-SCREEN/
├── frontend/                 # React + TypeScript + Vite + Recharts + SVG Overlays
│   ├── public/
│   └── src/
│       ├── assets/
│       ├── components/       # Common UI elements (Modals, Badges, Charts)
│       ├── features/         # Feature modules
│       │   ├── scanner/      # Product image upload & quality check
│       │   ├── evidence/     # Interactive SVG evidence overlay viewer
│       │   ├── citizen/      # Signal submission & community reporting
│       │   └── officer/      # Prioritization queue & decision audit
│       ├── services/         # API integration services
│       └── types/            # TypeScript schemas & interfaces
│
├── backend/                  # Python FastAPI Backend
│   ├── app/
│   │   ├── config.py         # App configuration & env variables
│   │   ├── database.py       # SQLAlchemy engine & session factory
│   │   ├── models/           # SQLAlchemy DB models (Scans, Evidence, Clusters, Reviews)
│   │   ├── schemas/          # Pydantic schemas for request/response validation
│   │   ├── routers/          # API endpoints (/scans, /reports, /officer, /dashboard)
│   │   ├── services/         # Business logic services
│   │   └── seed.py           # Idempotent demo database seeder
│   └── tests/                # Automated pytest unit & integration tests
│
├── ai/                       # CV & OCR Processing Modules
│   ├── quality.py            # Laplacian blur, brightness, glare, resolution quality gate
│   ├── detection.py          # OpenCV quadrilateral panel detection & perspective transform
│   ├── ocr_engine.py         # OCR token extraction & bounding box normalizer
│   ├── field_extractor.py    # Deterministic regex, anchor keyword & spatial field extractor
│   ├── context_classifier.py # Product category & package context classifier
│   ├── barcode_engine.py     # Symbology decoding & physical scale reference validator
│   └── consistency.py        # GSTIN checksum & GTIN consistency validator
│
├── rules/                    # Declarative Rule Profiles & Engine
│   ├── profiles/             # Versioned YAML profiles (2026.1 general & food profiles)
│   ├── engine.py             # Deterministic rule evaluator
│   └── verdict.py            # Three-state verdict aggregator (PASS, POTENTIAL, REVIEW)
│
├── docs/                     # Architectural & API Documentation
│   ├── architecture.md
│   ├── api.md
│   ├── ocr-pipeline.md
│   ├── rule-engine.md
│   ├── demo.md
│   └── IMPLEMENTATION_STATUS.md
│
├── .env.example
├── docker-compose.yml
└── README.md
```

---

## 3. Mandatory Product & Safety Principles

1. **Three Public Screening States ONLY:**
   * `PASS_SCREENING`: "No issue detected in the checks performed"
   * `POTENTIAL_NON_COMPLIANCE`: "Potential non-compliance detected"
   * `NEEDS_REVIEW`: "More evidence or human review required"
   * **FORBIDDEN VERDICTS:** `COMPLIANT`, `NON-COMPLIANT`, `VIOLATION`, `ILLEGAL`, `PASSED`, `FAILED`.

2. **Safety First:**
   * Low OCR confidence or blur defaults strictly to `NEEDS_REVIEW`.
   * Barcodes distorted or missing scale reference cannot be used for font height screening.
   * AI output is never a legal verdict; only authorized officer human review can confirm legal action.

3. **Mandatory Disclaimer:**
   > "This platform performs image-based Legal Metrology compliance screening for selected visible declarations. It does not replace inspection by an authorized officer, legal interpretation, laboratory testing, physical package measurement, or official enforcement procedures."

---

## 4. Implementation Roadmap & Phases

- [x] **Phase 0:** Repository Inspection & Structural Design
- [ ] **Phase 1:** Core Foundation (FastAPI + Vite React + Health Check)
- [ ] **Phase 2:** Database Models & Traceability Schemas
- [ ] **Phase 3:** Image Quality Gate (Blur, Brightness, Glare, Resolution)
- [ ] **Phase 4:** Package & Panel Geometry Detection (OpenCV Quadrilateral Homography)
- [ ] **Phase 5:** OCR Engine Wrapper & Token Persister
- [ ] **Phase 6:** Evidence-First Field Extraction (MRP, Net Qty, Dates, Origin, Consumer Care)
- [ ] **Phase 7:** Product Context Classifier
- [ ] **Phase 8 & 9:** Versioned Rule Profiles & Three-State Verdict Aggregator
- [ ] **Phase 10:** Interactive SVG Evidence Overlay UI
- [ ] **Phase 11 & 12:** Barcode Engine & Scale Reference Font Screening
- [ ] **Phase 13:** GSTIN / GTIN Consistency Screening
- [ ] **Phase 14:** Citizen Intelligence Signal Submission
- [ ] **Phase 15 & 16:** Perceptual Hash Duplicate Detection & Issue Clustering
- [ ] **Phase 17:** Operational Prioritization Scoring Engine
- [ ] **Phase 18:** Enforcement Officer Dashboard & Decision Audit Trail
- [ ] **Phase 19:** Role-Based Access Control (CITIZEN, OFFICER, ADMIN)
- [ ] **Phase 20 & 31:** Idempotent Demo Seeder (`python -m backend.app.seed`)
- [ ] **Phase 21 & 22:** Unit, Integration & Adversarial Verification Test Suite
- [ ] **Phase 25 & 32:** End-to-End SIH Demo Mode Verification
