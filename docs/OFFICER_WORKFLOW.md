# LM-Screen Officer Investigation Workspace & Workflow

## Overview
The Officer Investigation Workspace provides legal metrology inspectors with an auditable workspace to review AI screening results, inspect visual evidence, view citizen signal clusters, and log official enforcement actions.

## Operational Priority Queue
Cases are ranked using the Operational Prioritization Score:
$$\text{Priority} = 0.25 \cdot N_{\text{citizens}} + 0.20 \cdot N_{\text{ai}} + 0.20 \cdot S_{\text{confirmed}} + 0.15 \cdot Q_{\text{evidence}} + 0.10 \cdot W_{\text{severity}} + 0.10 \cdot R_{\text{recency}} - P_{\text{rejected}}$$

## Investigation Workspace Tabs
1. **Overview**: Summary of product identity, priority score, location, and cluster status.
2. **Evidence**: Source package image with interactive SVG overlay of extracted bounding boxes.
3. **OCR Tokens**: Full listing of raw OCR tokens with confidence metrics.
4. **Rules Evaluated**: Detailed rule-by-rule breakdown with statutory references.
5. **Citizen Signals**: Individual citizen reports clustered for this product.
6. **Audit History**: Complete chronological history of automated steps and human officer actions.

## Action Overrides & Rationale
Officers can select from 4 formal actions:
- `CONFIRM`: Confirm potential issue for formal inspection.
- `REJECT`: Dismiss signal as non-issue / false positive.
- `MARK_UNDER_INVESTIGATION`: Queue for field officer visit.
- `REQUEST_MORE_EVIDENCE`: Request additional photos or details from reporter.

Every action requires a written rationale and is recorded immutably in the `OfficerReview` audit log.
