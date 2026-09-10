# LM-Screen Evidence Model & Traceability

## Overview
LM-Screen uses an evidence-first approach where every extracted field maintains direct visual and logical linkage to raw OCR tokens and source image regions.

## Provenance Structure
```json
{
  "field_name": "mrp",
  "raw_value": "MRP Rs. 150.00 (Incl. of all taxes)",
  "normalized_value": "₹150.00",
  "confidence": 0.94,
  "extraction_method": "KEYWORD_ANCHOR",
  "ocr_evidence_ids": [27, 28],
  "bounding_box": [120, 340, 220, 35]
}
```

## Traceability Graph
```text
Screening Verdict (e.g. POTENTIAL_NON_COMPLIANCE)
       ▲
       │ evaluates
Rule Result (e.g. LM001 MRP Check)
       ▲
       │ inspects
Extracted Field (e.g. mrp = null)
       ▲
       │ linked to
OCR Tokens (e.g. Token #27, #28)
       ▲
       │ located at
Source Image Region (bounding polygon)
```
