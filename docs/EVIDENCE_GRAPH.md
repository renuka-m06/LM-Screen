# LM-Screen Evidence Graph Architecture

## Overview
The Evidence Graph in LM-Screen establishes an immutable, backward-traceable node-edge graph linking physical image regions to final officer enforcement actions.

## Graph Schema
- **Nodes**:
  - `IMAGE_QUALITY`: Quality metrics (blur, brightness, glare, resolution).
  - `OCR_TOKEN`: Raw OCR text string, bounding polygon, confidence score.
  - `FIELD`: Extracted statutory declaration (`mrp`, `net_quantity`, `manufacture_date`, etc.).
  - `CONTEXT`: Commodity category, package type, market context.
  - `RULE`: Versioned YAML rule check (`LM001`–`LM009`).
  - `VERDICT`: 3-state screening verdict (`PASS_SCREENING`, `POTENTIAL_NON_COMPLIANCE`, `NEEDS_REVIEW`).
- **Edges**:
  - `PROCESSED_BY`: Image Quality -> OCR Token
  - `SUPPORTS`: OCR Token -> Extracted Field
  - `APPLIES_RULE`: Context -> Rule Profile
  - `EVALUATED_BY`: Extracted Field -> Rule Profile
  - `CONTRIBUTES_TO`: Rule Result -> Screening Verdict

## API Endpoint
`GET /api/v1/scans/{scan_id}/evidence-graph`
Returns structured `{ nodes: [...], edges: [...], summary: {...} }`.
