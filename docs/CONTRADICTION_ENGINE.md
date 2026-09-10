# LM-Screen Generalized Contradiction Engine

## Overview
The Contradiction Engine in LM-Screen detects evidence mismatches across multiple input channels (user declarations, OCR text, barcode decoders, historical database records, citizen signals).

## Contradiction Types
1. `PRODUCT_IDENTITY_CONFLICT`: Triggered when user-declared product name differs significantly from OCR label text (e.g. User declares *PureHarvest Atta*, image contains *Choco-Chip Biscuits*).
2. `PACKAGING_QUANTITY_CHANGE_SIGNAL`: Triggered when net quantity statement changes between historical scan batches (e.g. 500 g vs 450 g).
3. `DATA_CONSISTENCY_CONFLICT`: Triggered when multiple conflicting GTIN/barcode values exist across user input, OCR, and barcode decoders.

## Safety Rule
A contradiction is a **SIGNAL FOR HUMAN REVIEW**. It automatically forces verdict = `NEEDS_REVIEW`.
It **NEVER** outputs `POTENTIAL_NON_COMPLIANCE`, `COMPLIANT`, `NON-COMPLIANT`, or `ILLEGAL`.
