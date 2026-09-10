# LM-Screen — AI-Based Legal Metrology Compliance Screening, Citizen Intelligence & Enforcement Prioritization Platform

**SIH Problem Statement:** 25034 — Ministry of Consumer Affairs, Food & Public Distribution — Department of Consumer Affairs  

---

## 📌 Executive Summary

**LM-Screen** is an evidence-first screening and decision-support platform designed to assist enforcement officers and citizens in screening pre-packaged commodities for visible Legal Metrology statutory declarations.

> ⚠️ **ABSOLUTE PRODUCT PRINCIPLE:**  
> LM-Screen is a **DECISION-SUPPORT SYSTEM**. It does NOT issue legal verdicts, replace authorized officers, or perform laboratory testing.

---

## ⚖️ Official Three-State Screening Verdicts

| State Badge | Public Label Text | Technical Meaning |
| :--- | :--- | :--- |
| **`PASS_SCREENING`** | *No issue detected in the checks performed* | All required statutory declarations visible with sufficient clarity and valid syntax. |
| **`POTENTIAL_NON_COMPLIANCE`** | *Potential non-compliance detected* | Mandatory statutory declaration (e.g. MRP, Net Qty) missing from visible label panel. |
| **`NEEDS_REVIEW`** | *More evidence or human review required* | Low OCR confidence, image blur, glare, or missing scale reference prevents definitive screening. |

*Public verdicts like `COMPLIANT`, `VIOLATION`, `ILLEGAL`, `PASSED`, `FAILED` are strictly forbidden.*

---

## 🏗 System Architecture

```text
PRODUCT IMAGE
     ↓
IMAGE QUALITY GATE (Laplacian Blur, Brightness, Glare)
     ↓
PACKAGE / PANEL DETECTION (OpenCV Quadrilateral Homography)
     ↓
OCR TOKEN EXTRACTION (PaddleOCR / EasyOCR bounding box tokens)
     ↓
EVIDENCE-FIRST EXTRACTION (Deterministic regex & spatial anchors)
     ↓
PRODUCT CONTEXT CLASSIFIER (Category, Origin, Market Context)
     ↓
VERSIONED RULE PROFILE (rules/profiles/2026.1/common.json)
     ↓
DETERMINISTIC RULE ENGINE (Auditable decision trace generator)
     ↓
THREE-STATE VERDICT AGGREGATOR + MANDATORY DISCLAIMER
     ↓
CITIZEN SIGNALS & PERCEPTUAL HASH DUPLICATE CLUSTERING
     ↓
OPERATIONAL PRIORITIZATION ENGINE (Weighted 6-factor score)
     ↓
ENFORCEMENT OFFICER ADJUDICATION QUEUE & AUDIT TRAIL
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- Python 3.10+
- Node.js v18+ & npm

### 2. Backend Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Seed synthetic SIH demo database
python -m backend.app.seed

# Run FastAPI backend server (Port 8000)
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend Health Check: `GET http://localhost:8000/health` -> `{"status": "ok"}`

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` in browser.

### 4. Running Automated Tests
```bash
python -m pytest backend/tests
```

---

## 📄 Legal Metrology Disclaimer

> *This platform performs image-based Legal Metrology compliance screening for selected visible declarations. It does not replace inspection by an authorized officer, legal interpretation, laboratory testing, physical package measurement, or official enforcement procedures. Results depend on image quality, available declarations, product classification, rule version, and evidence confidence.*
