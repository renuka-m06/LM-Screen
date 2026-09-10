# LM-Screen System Architecture

## Overview
LM-Screen is an evidence-first, decision-support platform designed for AI-assisted Legal Metrology compliance screening.

## Core Architectural Principles
1. **Decision Support, Not Legal Judgment**: AI organizes evidence and runs deterministic screening checks. Final enforcement decisions rest strictly with human officers.
2. **Three-State Verdict Engine**: Public screening results are strictly `PASS_SCREENING`, `POTENTIAL_NON_COMPLIANCE`, or `NEEDS_REVIEW`.
3. **Traceable Evidence Graph**: Every extracted field links back to source image coordinates and OCR token IDs.
4. **Deterministic Fail-Safe**: Low quality or missing evidence gracefully defaults to `NEEDS_REVIEW`.

## System Architecture Diagram
```text
[Frontend (React/Vite/TS)]
       │ (REST APIs / JSON)
       ▼
[FastAPI Backend Server]
       ├── [Image Quality Gate] (Blur, Glare, Brightness, OCR visibility)
       ├── [Package Detector] (OpenCV Homography & Manual ROI)
       ├── [OCR Token Engine] (RapidOCR / PaddleOCR token bounding polygons)
       ├── [Field Extractor] (Regex, Anchors, Spatial, Normalization)
       ├── [Context Classifier] (Commodity, Package Type, Market Context)
       ├── [Barcode Engine] (Pyzbar / OpenCV scale reference)
       ├── [Deterministic Rule Engine] (Externalized YAML Rule Profiles)
       ├── [Verdict Aggregator] (3-State Aggregation)
       ├── [Citizen Intelligence & Clustering] (Deduplication + Priority Scoring)
       └── [Officer Investigation Workspace] (Audit Trails + Override Actions)
       │
       ▼
[SQLAlchemy Database] (16 Relational Models)
```
