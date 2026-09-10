# LM-Screen — Phase 2 Architecture Audit Report

**Project Name**: LM-Screen — AI-Based Legal Metrology Compliance Screening, Citizen Intelligence & Enforcement Prioritization Platform  
**Phase**: Phase 2 — Evidence Intelligence, Contradiction Detection & Evidence Passport Upgrade  
**Date**: September 10, 2026  
**Auditor**: Lead Full-Stack Architect & AI/CV Engineer  

---

## 1. Executive Summary & Existing System Audit

The existing LM-Screen repository provides a functional baseline for image processing, statutory field extraction, context classification, 3-state verdict screening, citizen signal submission, product clustering, priority queue management, and officer investigation review.

This audit evaluates the codebase to establish integration points for **Phase 2 Technical Upgrades**:

- **Feature 1**: Explicit Evidence Graph (Nodes & Edges linking Image $\rightarrow$ OCR Token $\rightarrow$ Field $\rightarrow$ Context $\rightarrow$ Rule $\rightarrow$ Verdict $\rightarrow$ Officer Decision).
- **Feature 2**: Generalized Contradiction Engine (`PRODUCT_IDENTITY_CONFLICT`, `PACKAGING_QUANTITY_CHANGE_SIGNAL`, `DATA_CONSISTENCY_CONFLICT`).
- **Feature 3**: Reproducible Evidence Passport & Decision Replay ("Why This Result?").
- **Feature 4**: Product Intelligence Timeline (Historical pack/MRP/quantity drift tracking).
- **Feature 5**: Geographic Intelligence & Cluster Analysis.
- **Feature 6**: Explainable Operational Priority Engine (Transparent score breakdown).
- **Feature 7**: Officer Evidence Copilot (Evidence-grounded assistant without legal claims).
- **Feature 8**: Structured Investigation PDF/Report Generator.

---

## 2. Component-by-Component Assessment

| Component | Current State | Phase 2 Integration Strategy |
| :--- | :--- | :--- |
| **Backend API (`FastAPI`)** | Router endpoints exist for `/scans`, `/reports`, `/officer`, `/products`, `/dashboard`. | Add `/scans/{scan_id}/evidence-graph`, `/scans/{scan_id}/evidence-passport`, `/scans/{scan_id}/decision-replay`, `/products/{product_id}/timeline`, `/reports/investigation/{cluster_id}`. |
| **Database (`SQLAlchemy`)** | 16 entities present in `models.py`. | Extend `Scan` and `ExtractedField` with explicit `contradiction_flags`, `passport_hash`, `evidence_graph_nodes`, and `evidence_graph_edges`. |
| **Contradiction Detection** | Basic `ConsistencyScreening` checks GTIN checksum and product name inclusion in `ai/consistency.py`. | Upgrade into a generalized `ContradictionEngine` producing reusable contradiction objects with severity, sources, confidence, and recommended officer actions. |
| **Evidence Graph** | Basic field-to-token list mapping in `/scans/{id}/evidence`. | Implement explicit Node/Edge Graph schema (`OCR_TOKEN`, `FIELD`, `CONTEXT`, `RULE`, `VERDICT`) and officer Evidence Graph Explorer. |
| **Reproducibility & Passport** | Timestamps & rule versions stored on `Scan`. | Implement structured `EvidencePassport` storing SHA-256 hash, OCR model version, extraction algorithm version, rule profile version, threshold profile, and audit events. |
| **Product Timeline** | Scans linked to `Product`. | Implement `ProductIntelligenceTimeline` tracking historical pack size, MRP, manufacturer, and declaration changes over time. |
| **Officer Assistant / Copilot** | Officer investigation view present. | Add `OfficerEvidenceCopilot` API & UI component providing structured evidence summaries without legal claims. |
| **Frontend UI (`React/Vite/TS`)** | Clean teal/green civic-tech theme. UI components: `Scanner`, `EvidenceOverlay`, `CitizenPortal`, `OfficerDashboard`, `InvestigationView`. | Extend `InvestigationView` with tabs for Evidence Graph Explorer, Decision Replay Drawer, Contradictions, Historical Timeline, Evidence Passport, and Investigation Report download. |

---

## 3. Mandatory Regression Fixture (Spec §9)

The Phase 2 upgrade must pass the exact regression scenario:

- **Input**: User product name: `PureHarvest Atta 5kg`.
- **Uploaded Image Contains**: `Premium Choco-Chip Biscuits`, `Net Quantity: 250 g`, `MRP: Rs. 150.00`, `Mfg Date: 09/2026`, `ABC Foods Pvt Ltd`, `Consumer Care: 1800-123-4567`, `GTIN: 8901234567890`.
- **Expected Outcome**:
  - Extracted fields derive biscuit metadata (`Premium Choco-Chip Biscuits`, `250 g`, `₹150.00`, `ABC Foods Pvt Ltd`, `09/2026`, `8901234567890`).
  - Contradiction Engine outputs `PRODUCT_IDENTITY_CONFLICT`.
  - Final screening verdict = `NEEDS_REVIEW` (NOT `POTENTIAL_NON_COMPLIANCE`, NOT `PASS_SCREENING`).

---

## 4. Architectural Rules

1. **AI is Decision Support Only**: AI/CV/OCR extracts and compares evidence. Humans retain sole legal enforcement authority.
2. **Fail-Safe Verdicts**: Uncertainty, poor OCR, missing barcodes, or data contradictions default safely to `NEEDS_REVIEW`.
3. **No Hardcoded Verdicts**: All outputs must be derived dynamically from processing pipelines and rule evaluation.
