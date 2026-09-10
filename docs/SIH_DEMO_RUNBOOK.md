# LM-Screen SIH Winning Upgrade Demo Runbook

## 2–3 Minute Flagship Killer Demonstration Flow

### STEP 1: Product Identity Mismatch Input
- Upload scan declaring user product: `PureHarvest Atta 5kg`.
- Upload image containing `Premium Choco-Chip Biscuits`.

### STEP 2: Processing & Evidence Extraction
- Quality Gate: `ACCEPTABLE`
- OCR Token Extractor: Derives `Premium Choco-Chip Biscuits`, `250 g`, `₹150.00`, `ABC Foods Pvt Ltd`, `09/2026`, `8901234567890`.

### STEP 3: Visual Evidence Polygon Overlay
- Click `MRP` card $\rightarrow$ SVG overlay highlights exact label coordinates on image.

### STEP 4: Contradiction Engine Flag
- System flags `PRODUCT_IDENTITY_CONFLICT` (User input vs label image).

### STEP 5: Safe Verdict Output
- Final verdict = **NEEDS_REVIEW** ("More evidence or human review required").
- Emphasize that the system gracefully handles uncertainty without falsely accusing manufacturers.

### STEP 6: Node-Edge Evidence Graph
- Open `/scans/{id}/evidence-graph` $\rightarrow$ Show traceable path Image $\rightarrow$ OCR Token $\rightarrow$ Field $\rightarrow$ Rule $\rightarrow$ Verdict.

### STEP 7: Evidence Passport & Decision Replay
- Open `/scans/{id}/evidence-passport` $\rightarrow$ Show cryptographically signed SHA-256 integrity hash & locked model versions.
- Open `/scans/{id}/decision-replay` $\rightarrow$ View step-by-step pipeline execution trace.

### STEP 8: Product Intelligence Timeline
- Show historical batch quantity shift (500 g vs 450 g) labelled as `Change detected — Requires Review`.

### STEP 9: Officer Investigation Workspace & Audit Trail
- Inspector opens priority queue, runs Officer Copilot ("Why is this case prioritized?"), selects `MARK_UNDER_INVESTIGATION` with rationale, and views immutable audit log.
