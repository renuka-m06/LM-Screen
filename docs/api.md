# LM-Screen — REST API Specification

### Health Check
- `GET /health`: Returns `{"status": "ok"}`

### Scans Pipeline
- `POST /api/v1/scans`: Upload image file + optional commodity name/GTIN. Runs CV quality gate, OCR tokenization, field extraction, rule engine evaluation, and returns three-state screening verdict with interactive SVG tokens.
- `GET /api/v1/scans/{id}`: Retrieve stored scan record with OCR tokens and rule traces.

### Citizen Intelligence
- `POST /api/v1/reports`: Submit citizen signal (returns `status: "UNVERIFIED"`).
- `GET /api/v1/reports`: List citizen signals.

### Enforcement Officer Operations
- `GET /api/v1/officer/queue`: Retrieve Operational Prioritization Queue sorted by priority score.
- `POST /api/v1/officer/reviews`: Record official officer adjudication decision (`CONFIRM`, `REJECT`, `REQUEST_MORE_EVIDENCE`, `MARK_UNDER_INVESTIGATION`).

### Dashboard
- `GET /api/v1/dashboard/statistics`: Overall metrics breakdown.
