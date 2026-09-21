# ML_READINESS_REPORT.md — LM-Screen Machine Learning Status

> This report is completely honest about the current ML status.
> No performance metrics are fabricated. No accuracy numbers are claimed without evidence.

---

## 1. Overall ML Status: ARCHITECTURE READY — MODEL NOT TRAINED

The ML integration architecture is fully implemented and ready to receive trained weights.
**Current inference falls back to deterministic heuristic/OpenCV methods.**

---

## 2. Dataset Status

| Metric | Count | Notes |
|--------|-------|-------|
| Total images collected | **0** | Dataset collection phase not yet started |
| Corrupted images | 0 | — |
| Duplicate images | 0 | — |
| **Unique usable images** | **0** | |
| Images with YOLO annotations | 0 | — |
| Images with NER annotations | 0 | — |
| Training split | 0 | — |
| Validation split | 0 | — |
| Test split | 0 | — |

> **Why this is accurate:** The `ml/dataset/images/train/`, `val/`, and `test/` directories
> are empty. No collection drive has been conducted yet.
> The dataset specification and annotation schema are defined in `DATASET.md`.

---

## 3. Model Status

| Model | Purpose | Weights File | Status |
|-------|---------|-------------|--------|
| YOLOv8 Panel Detector | Detect label panels & barcodes on FMCG products | `models/detector.pt` | **NOT FOUND — FALLBACK ACTIVE** |
| NLP Product Classifier | Classify product category from OCR text | Not yet defined | **NOT STARTED** |
| NER Field Extractor | Replace regex field extraction | Not yet defined | **NOT STARTED** |

> The `ModelRegistry` (`backend/app/services/ml/registry.py`) automatically detects
> the absence of `models/detector.pt` and reports `MODEL_NOT_FOUND` at runtime.
> This is displayed on the Analytics Dashboard under "ML Model Health."

---

## 4. Current Inference Method (Fallback)

When `models/detector.pt` is not found, the system uses:

| Stage | Fallback Method | Source Tag |
|-------|----------------|-----------|
| Panel Detection | OpenCV edge detection + contour analysis | `HEURISTIC` |
| OCR | PaddleOCR / EasyOCR (full image, not panel-cropped) | `OCR_ENGINE` |
| Field Extraction | Deterministic regex + keyword anchors | `REGEX_PATTERN` / `KEYWORD_ANCHOR` |
| Barcode | pyzbar library | `BARCODE` |
| Product Classification | Keyword-based rule classifier | `KEYWORD_CLASSIFICATION` |

All fallback sources are explicitly tagged in the evidence record.
The frontend displays `HEURISTIC` or `OCR` provenance — **never misrepresents fallback as ML**.

---

## 5. ML Architecture (Implemented — Awaiting Weights)

The following components are implemented and ready for ML weights:

```
ModelRegistry                → Tracks model availability with explicit states
MLPackageDetector            → YOLO inference wrapper with bbox validation
DetectionService             → Queries ModelRegistry; routes to YOLO or CV fallback
ScreeningService             → Integrates detections into Evidence Graph
OCRService                   → Supports regional OCR on detected panel bboxes
ClassificationService        → Stub ready for NLP model integration
IdentityMatcher              → Stub ready for ML product matching
```

---

## 6. Evaluation Status

| Metric | Status |
|--------|--------|
| mAP@50 | Not measured (no trained model) |
| mAP@50-95 | Not measured |
| Precision | Not measured |
| Recall | Not measured |
| F1 Score | Not measured |
| Inference speed | Not measured |

> No accuracy, precision, recall, or mAP figures are claimed in this report.
> These will be measured after model training with a proper held-out evaluation set.

---

## 7. Annotation Plan

The annotation schema is defined in `DATASET.md`:

- **Detection**: YOLOv8 TXT format, 8 classes (package, front_panel, back_panel, nutrition_panel, ingredients_panel, barcode, declaration_label, warning_area)
- **Classification**: 5 categories (FOOD, BEVERAGE, COSMETIC, HOUSEHOLD, OTHER)
- **NER**: BIO format for 13 entity types (mrp, net_quantity, manufacture_date, expiry_date, etc.)

---

## 8. Known Limitations

1. **No training data** — All inference is heuristic/rule-based
2. **OCR accuracy** depends on image quality and is not benchmarked on Indian FMCG labels
3. **Panel detection** uses contour heuristics — may miss non-rectangular panels
4. **Product classification** is keyword-based — may misclassify hybrid products
5. **No GTIN database lookup** — barcode decoded but not verified against product registry

---

## 9. Honest System Capability Statement

> LM-Screen implements a complete, evidence-first screening pipeline using:
> deterministic regex-based field extraction, rule-based product classification,
> OpenCV-based panel detection heuristics, and a multi-source evidence graph.
>
> The ML architecture (YOLOv8-based panel detector, NLP classifier, NER extractor)
> is designed, implemented as an integration framework, and ready to receive
> trained weights once a sufficient annotated dataset is assembled.
>
> Current system performance is that of a deterministic heuristic pipeline,
> not a trained ML system.

---

## 10. Next Steps Toward ML Readiness

1. **Collect 1,000+ unique FMCG product images** (varied lighting, angles, brands)
2. **Annotate with YOLOv8 format** using Roboflow or LabelImg
3. **Train YOLOv8n/s** on annotated dataset; target mAP@50 > 0.75
4. **Evaluate on held-out test set** and report actual metrics
5. **Deploy `models/detector.pt`** — system automatically switches from heuristic to YOLO
6. **Collect OCR correction logs** from officer corrections → use as NER fine-tuning data
7. **Build product database** for GTIN → product identity lookup
