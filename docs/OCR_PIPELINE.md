# LM-Screen OCR & Evidence Pipeline

## Overview
The OCR pipeline in LM-Screen is designed to preserve maximum evidence provenance without discarding raw token details.

## Pipeline Sequence
```text
Raw Image -> Quality Gate -> Polygon Warp -> OCR Engine -> Token Polygons -> Field Extractor
```

## Token Data Structure
Every extracted OCR token stores:
- `token_id`: Unique identifier
- `text`: Raw extracted string
- `polygon`: `[[x1,y1], [x2,y2], [x3,y3], [x4,y4]]`
- `confidence`: Confidence float (0.0 to 1.0)
- `language`: Detected language (e.g. `en`, `hi`)
- `model_version`: OCR engine model version tag

## Fail-Safe States
If OCR processing experiences issues:
- `OCR_UNAVAILABLE`: External OCR engine offline -> Verdict `NEEDS_REVIEW`
- `NO_TEXT_DETECTED`: Blurry or featureless image -> Verdict `NEEDS_REVIEW`
- `LOW_CONFIDENCE_TEXT`: Token confidence below threshold -> Evidentiary confidence flagged
