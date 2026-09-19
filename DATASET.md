# LM-Screen Dataset Specification

This document defines the exact data collection and annotation requirements for training the true ML models in LM-Screen.

## 1. Object Detection (Package & Panel)

We require a YOLO-formatted dataset with bounding box annotations. 

### Classes
0. `package` - The entire physical product package
1. `front_panel` - Principal Display Panel (PDP)
2. `back_panel` - Information panel
3. `nutrition_panel` - The standardized nutritional facts table
4. `ingredients_panel` - The ingredient list block
5. `barcode` - The barcode region
6. `declaration_label` - Area containing MRP, Net Weight, Date, Mfg info
7. `warning_area` - Statutory warnings (e.g. tobacco, alcohol warnings)

### Requirements
* **Volume**: Minimum 1,000 distinct product images across varied lighting and backgrounds.
* **Format**: YOLOv8 TXT format for bounding boxes.

## 2. Product Classification (Context)

We require text-and-image paired datasets for assigning contextual product categories.

### Classes
1. `FOOD`
2. `BEVERAGE`
3. `COSMETIC`
4. `HOUSEHOLD`
5. `OTHER`

### Requirements
* **Volume**: Minimum 5,000 text-label pairs.
* **Input Features**: Raw OCR text string, plus optional cropped image of the PDP.

## 3. Evidence Extraction (NLP/NER)

We require labeled text spans to train an NER model to replace the current RegEx heuristics.

### Entities
* `product_name`
* `manufacturer`
* `brand`
* `mrp`
* `net_quantity`
* `ingredients`
* `batch_number`
* `packing_date`
* `expiry_date`
* `best_before`
* `consumer_care`
* `barcode`

### Requirements
* **Annotation**: BIO (Begin, Inside, Outside) format or span-based JSON mapping.
* **Separation of Concerns**: 
  * *OCR Annotation* is strictly for text recognition.
  * *Evidence Annotation* is strictly for semantic labeling of the extracted text.
  * *Human Verification* logs will be used to automatically augment this dataset over time.

## 4. Pipeline Traceability

No dataset should combine tasks. Bounding boxes are for detection, text is for classification and extraction. The final screening result is generated *deterministically* by the rule engine, so we do **NOT** train an ML model to output "PASS" or "FAIL".
