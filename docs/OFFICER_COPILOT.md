# LM-Screen Officer Evidence Copilot

## Overview
The Officer Evidence Copilot is an evidence-grounded decision-support assistant designed for legal metrology inspectors.

## Operational Boundaries
- **Permitted Capabilities**: Summarizes stored OCR tokens, explains priority score components, lists detected contradictions, and retrieves historical timeline changes.
- **Prohibited Behavior**: Does **NOT** issue legal verdicts, declare manufacturers guilty, or hallucinate missing information.
- **Mandatory Disclaimer**: Included in every copilot response reinforcing human inspector authority.

## API Endpoint
`POST /api/v1/officer/copilot`
Payload: `{ "scan_id": "...", "question": "Why is this case prioritized?" }`
