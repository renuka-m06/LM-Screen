# Database Documentation

This document describes the schema and database architecture for the Legal Metrology (LM) project.

## Tables & Relationships

### Core Entities
- **User**: Represents users of the system (Citizen, Officer, Admin).
- **Product**: Represents a standardized commodity identified by GTIN/barcode. Contains metadata like `product_name`, `manufacturer`, `brand_name`.

### Scanning & Extraction
- **Scan**: Represents a single screening event for a product image. Contains screening results, confidence scores, and links to extracted fields and OCR results.
- **ProductImage**: Stores image metadata, capture source, and references the original file path.
- **ImageQuality**: Stores quality metrics for the image (blur, brightness, glare).
- **OCRResult**: Stores raw OCR text tokens, bounding boxes, and confidences extracted from a scan.
- **Detection**: Object detections (e.g., logo, text blocks, barcode) on the product image.
- **ExtractedField**: The "Evidence Table". Represents a semantic field extracted from OCR text (e.g., MRP, Net Quantity, Manufacture Date).

### Rules Engine
- **RuleProfile**: A versioned set of rules applied during screening.
- **Rule**: A specific compliance rule to check (e.g., MRP present).
- **RuleResult**: The outcome (PASS/FAIL/POTENTIAL_NON_COMPLIANCE) of a specific rule evaluated against a Scan.
- **DecisionTrace**: Step-by-step pipeline execution trace, used for the "Why This Result?" replay functionality.

### Reporting & Investigations
- **CitizenReport**: Represents a complaint or issue reported by a citizen regarding a specific product/scan.
- **ProductCluster**: A group of scans/reports for a single product aggregated by an issue type (e.g., "Suspicious MRP").
- **Investigation**: Tracks officer investigations into flagged products.
- **OfficerReview**: The outcome of a human officer reviewing an AI-flagged cluster or scan.

## Schema Migrations (Alembic)
The project uses Alembic for database migrations.

**Key Commands:**
- Generate a new migration: `alembic revision --autogenerate -m "Migration message"`
- Apply migrations: `alembic upgrade head`

## Seed Data
The database can be seeded with initial demo data (users, compliant and non-compliant scans, rules, and citizen reports) for the SIH presentation using:
`python -m backend.app.seed`
