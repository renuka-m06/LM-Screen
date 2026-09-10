# LM-Screen Decision Replay ("Why This Result?")

## Overview
Decision Replay provides officers with a step-by-step audit trace answering *"Why did the system produce this result?"*.

## Replay Pipeline Steps
1. **IMAGE_QUALITY**: Evaluates blur, glare, brightness, and resolution thresholds.
2. **OCR**: Displays token count and confidence metrics.
3. **FIELD_EXTRACTION**: Displays extracted statutory declarations and provenance confidence.
4. **CONTEXT_CLASSIFICATION**: Displays commodity and package format classification.
5. **CONTRADICTIONS**: Highlights evidence conflicts if present.
6. **RULE_ENGINE**: Evaluates deterministic YAML rule profiles.
7. **VERDICT**: 3-State verdict output with statutory disclaimers.

## API Endpoint
`GET /api/v1/scans/{scan_id}/decision-replay`
