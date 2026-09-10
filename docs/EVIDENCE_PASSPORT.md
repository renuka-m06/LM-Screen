# LM-Screen Evidence Passport

## Overview
An Evidence Passport is a cryptographically signed snapshot generated for every scan. It guarantees reproducibility and auditability even if underlying ML models or rule profiles evolve.

## Passport Schema
- `passport_id`: Unique identifier (e.g. `PASS-SCAN1001`)
- `scan_id`: Associated scan ID
- `image_hash_sha256`: SHA-256 hash of original package image
- `created_at`: ISO timestamp
- `provenance_versions`: Model and rule versions (`ocr_engine_version`, `field_extractor_version`, `rule_profile_version`)
- `passport_signature_hash`: Cryptographic SHA-256 signature locking the audit snapshot

## API Endpoint
`GET /api/v1/scans/{scan_id}/evidence-passport`
