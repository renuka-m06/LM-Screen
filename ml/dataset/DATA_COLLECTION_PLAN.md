# LM-Screen Data Collection Plan

## 1. Purpose
This document outlines the rigorous, human-verified data collection strategy required to build a highly generalized YOLOv8 panel detector for LM-Screen. Because Legal Metrology enforcement relies on accurate structured data extraction from physical packages in varied real-world environments, the underlying ML detector must be robust against severe environmental noise, diverse packaging shapes, and varying camera hardware.

## 2. Class Coverage
Every collected image will eventually be annotated for the following 8 classes. The dataset collection must naturally contain a high density of these classes:
1. `package`
2. `front_panel`
3. `back_panel`
4. `nutrition_panel`
5. `ingredients_panel`
6. `barcode`
7. `declaration_label`
8. `warning_area`

## 3. Diversity Requirements
To ensure the model generalizes rather than memorizes, the dataset must span the following dimensions:

**Product Categories:**
- Food (e.g., snacks, grains, packaged meals)
- Beverages (e.g., bottles, cans, tetra packs)
- Cosmetics / Personal Care (e.g., lotions, soaps, makeup)
- Household Products (e.g., cleaners, detergents)

**Physical Attributes:**
- Different package shapes (cylindrical bottles, rectangular boxes, flexible pouches, blister packs)
- Different package sizes (micro items up to large bulk bags)
- Different brands (to avoid brand-specific color bias)

**Visual & Camera Variations:**
- **Angles:** Front views (PDP), back views (Information Panel), and angled/isometric views.
- **Environment:** Bright retail lighting, dim home lighting, extreme glare on glossy packaging, and cluttered backgrounds (supermarket shelves, hands, tables).
- **Quality:** High resolution, mild blur (motion or out-of-focus), and partial visibility/occlusions (fingers covering part of the package).

## 4. Target Image Counts
To scale effectively, collection will happen in three phases:
- **Minimum Experimental Dataset:** 200 Unique Images. (Strictly for verifying that the training pipeline and loss convergence function correctly).
- **Recommended Prototype Dataset:** 1,000 Unique Images. (The baseline required for a reliable proof-of-concept capable of handling common FMCG goods).
- **Long-term Target:** 5,000 - 10,000+ Unique Images. (Required for production-grade robustness across edge cases and rare packaging shapes).

## 5. Collection Checklist Tracker
For rigorous dataset management, every collected image should be logged in a master tracker (e.g., CSV/Excel) with the following metadata columns:
- `image_id` (Unique identifier, e.g., `IMG_0001`)
- `product_category` (Food, Beverage, Cosmetic, etc.)
- `product_type` (Cereal, Shampoo, etc.)
- `package_type` (Box, Bottle, Pouch, Tube, etc.)
- `visibility` (Front, Back, Side, Angled)
- `image_quality` (Clear, Glare, Blur, Cluttered)
- `source` (Captured by Agent X, Retail Store Y)
- `duplicate_status` (Verified Unique)

## 6. Quality Requirements
- **Authenticity:** All images must be REAL photographs of packaged products. NO AI-generated images or heavily photoshopped renders are permitted.
- **Copyright:** Avoid using scraped internet images unless their license strictly permits commercial/research machine learning usage. Prefer self-captured smartphone images.
- **Resolution:** Images should ideally be captured at high resolution (>1080p) to ensure text-heavy regions (like the `declaration_label`) remain legible when zoomed in.

## 7. Duplicate Prevention
- To avoid data leakage and false metrics, the dataset must not contain duplicate or near-duplicate images.
- **Action:** Utilize MD5/SHA-256 hashing to filter out exact duplicates (as seen with the 91 API duplicates). For near-duplicates (e.g., burst photos of the exact same product from the exact same angle), manually curate the set to include only the highest quality frame, or vary the angle significantly.

## 8. Annotation Preparation Requirements
- Do NOT annotate during the initial collection phase.
- Once a batch (e.g., 200 images) is verified as unique and diverse according to the checklist, import the batch into a human-verified annotation tool (CVAT or Label Studio).
- Ensure the tool is configured strictly for YOLO TXT export with the exact 8 classes.

## 9. Train / Validation / Test Strategy
To accurately gauge the model's performance on unseen data:
- **Train (80%):** The core dataset used to update model weights.
- **Validation (10%):** Used to tune hyperparameters and halt training if overfitting occurs.
- **Test (10%):** A heavily guarded, completely unseen set of images used ONLY for the final ML Audit Report. 
*Note: Ensure that images of the exact same physical product (taken from different angles) are kept within the same split to prevent data leakage from Train to Test.*
