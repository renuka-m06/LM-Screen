# LM-Screen SIH Live Demonstration Script

## Demo Overview
This script guides a presenter through demonstrating LM-Screen to SIH judges in under 3 minutes.

## Prerequisites
Run `python -m backend.app.seed` before beginning to populate demo presets.

## Demo Sequence

### Scenario 1: Clean Compliant Scan
1. Open Scanner UI at `http://localhost:5173`.
2. Select Preset **1. Clean Scan (Pass)**.
3. System runs pipeline and displays **PASS_SCREENING** ("No issue detected in the checks performed").
4. Point out the green status banner, rule evaluation list, and mandatory disclaimer.

### Scenario 2: Visual Evidence Viewer
1. Click on the **MRP** extracted field card.
2. Observe the SVG overlay highlighting the exact bounding region on the product photo.
3. Click on the image region to highlight the corresponding statutory field card.

### Scenario 3: Potential Non-Compliance
1. Select Preset **2. Missing MRP (Potential Issue)**.
2. System evaluates rule `LM001` and displays **POTENTIAL_NON_COMPLIANCE** ("Potential non-compliance detected").
3. Point out the missing statutory declaration callout.

### Scenario 4: Image Quality Gate & Fail-Safe
1. Select Preset **3. Blurry Image (Review Required)**.
2. System detects low Laplacian score and displays **NEEDS_REVIEW** ("More evidence or human review required").
3. Emphasize that poor image quality never becomes evidence of non-compliance.

### Scenario 5: Product Identity Contradiction
1. Select Preset **4. Product Identity Mismatch**.
2. User specified `PureHarvest Atta 5kg`, but image contains `Choco-Chip Biscuits`.
3. System flags **PRODUCT IDENTITY MISMATCH** and defaults safely to **NEEDS_REVIEW**.

### Scenario 6: Citizen Intelligence & Clustering
1. Navigate to **Citizen Signals**.
2. Show clustered reports for `FastBites Instant Noodles` aggregated from 8 citizen submissions.
3. Show the Operational Prioritization Score (0.87) with its transparent breakdown.

### Scenario 7: Officer Investigation Workspace & Audit Log
1. Navigate to **Officer Dashboard**.
2. Open the **Investigation Workspace** for the noodle cluster.
3. Review evidence graph and Decision Trace.
4. Record officer action `MARK_UNDER_INVESTIGATION` with rationale.
5. Show the immutable Audit Log record created.
