# LM-Screen — SIH Requirements Traceability Matrix

> All requirements mapped to: Implemented Feature → Backend Component → Frontend Component → Database Evidence → Demo Flow → Test

---

## REQ-01: Evidence-Based Product Screening

| Field | Detail |
|---|---|
| **Requirement** | Screen pre-packaged commodities for visible Legal Metrology statutory declarations |
| **Implementation** | Evidence Graph + Deterministic Rule Engine |
| **Backend** | `ScreeningService.process_image()` → `EvidenceService.extract()` → `DeterministicRuleEngine.evaluate()` → `VerdictAggregator.aggregate()` |
| **Frontend** | `Scanner.tsx` — Upload + result display; `InvestigationView.tsx` — Evidence Chain tab |
| **Database** | `scans`, `extracted_fields`, `rule_results`, `decision_traces` |
| **Demo Flow** | Scenario 1 (Clean PASS) or Scenario 2 (Missing MRP → POTENTIAL_NON_COMPLIANCE) |
| **Test** | `test_adversarial.py::test_verdict_states_are_distinct`, `test_ml_integration.py` |

---

## REQ-02: Three-State Legal Safety Model

| Field | Detail |
|---|---|
| **Requirement** | System must NEVER issue binary COMPLIANT/VIOLATING verdicts |
| **Implementation** | Hardcoded three-state model: PASS_SCREENING / POTENTIAL_NON_COMPLIANCE / NEEDS_REVIEW |
| **Backend** | `rules/verdict.py` — `VerdictAggregator` with `MANDATORY_DISCLAIMER` constant |
| **Frontend** | `DisclaimerBanner.tsx`; status badges in `Scanner.tsx` and `InvestigationView.tsx` |
| **Database** | `scans.status` constrained to three valid states |
| **Demo Flow** | Show all three verdicts across scenarios 1, 2, 3 |
| **Test** | `test_adversarial.py::test_public_labels_never_say_illegal_or_compliant` |

---

## REQ-03: Image Quality Gating

| Field | Detail |
|---|---|
| **Requirement** | Poor-quality images must not produce false evidence states |
| **Implementation** | Laplacian blur + brightness + glare assessment before OCR |
| **Backend** | `QualityService.assess()` in `backend/app/services/ml/quality_service.py` |
| **Frontend** | Quality badge shown in `Scanner.tsx` scan result panel |
| **Database** | `scans.quality_status`, `scans.blur_score`, `scans.brightness_score`, `scans.glare_ratio` |
| **Demo Flow** | Scenario 3 (Blurry → NEEDS_REVIEW) |
| **Test** | `test_adversarial.py::test_blurry_image_does_not_produce_non_compliance` |

---

## REQ-04: File Upload Security

| Field | Detail |
|---|---|
| **Requirement** | System must reject unsafe, malformed, or oversized uploads |
| **Implementation** | MIME type validation, 10MB size limit, corrupt image detection |
| **Backend** | `routers/scans.py` lines 42–65: `ALLOWED_MIME_TYPES`, `MAX_UPLOAD_BYTES`, `Image.open()` try/except |
| **Frontend** | Error displayed via `Scanner.tsx` error state UI |
| **Database** | Invalid uploads never reach DB |
| **Demo Flow** | (Background security — not in main demo flow) |
| **Test** | `test_adversarial.py::test_blank_image_produces_needs_review_not_violation` |

---

## REQ-05: OCR Evidence Extraction

| Field | Detail |
|---|---|
| **Requirement** | Extract statutory fields (MRP, Net Quantity, Dates, etc.) from product labels |
| **Implementation** | PaddleOCR/EasyOCR token extraction + deterministic regex field extractor |
| **Backend** | `OCRService.extract()` → `ai/field_extractor.py` (FieldExtractor) |
| **Frontend** | Evidence Chain panel in `InvestigationView.tsx` |
| **Database** | `ocr_results`, `extracted_fields` |
| **Demo Flow** | Visible in all scan scenarios — expand Evidence Chain tab |
| **Test** | `test_extraction.py` |

---

## REQ-06: Barcode Detection & Consistency

| Field | Detail |
|---|---|
| **Requirement** | Decode barcodes and cross-check against OCR-extracted GTIN |
| **Implementation** | `BarcodeService` using pyzbar; consistency check in `ConsistencyEngine` |
| **Backend** | `backend/app/services/ml/barcode_service.py` → `ai/consistency_engine.py` |
| **Frontend** | Barcode result in `Scanner.tsx` scan output |
| **Database** | Consistency results in `consistency_checks` table |
| **Demo Flow** | Scenario 4 (Barcode/OCR GTIN mismatch) |
| **Test** | `test_consistency.py`, `test_adversarial.py::test_evidence_conflict_produces_conflict_state_not_violation` |

---

## REQ-07: Product Context Classification

| Field | Detail |
|---|---|
| **Requirement** | Classify product category to activate correct conditional rules |
| **Implementation** | Rule-based keyword + OCR-token context classifier |
| **Backend** | `ClassificationService.classify()` in `backend/app/services/ml/classification_service.py` |
| **Frontend** | Category shown in product details panel |
| **Database** | `product_classifications`, `scans.category` |
| **Demo Flow** | Scenario 7 (Unknown context — CONTEXT_REVIEW_REQUIRED, no conditional rules activated) |
| **Test** | `test_adversarial.py::test_blank_image_produces_needs_review_not_violation` |

---

## REQ-08: Dynamic Rule Applicability Engine

| Field | Detail |
|---|---|
| **Requirement** | Rules must only apply to relevant product categories; wrong-category rules must not fire |
| **Implementation** | Versioned rule profiles with applicability flags |
| **Backend** | `rules/engine.py` — `DeterministicRuleEngine`; `rules/profiles/` JSON configs |
| **Frontend** | Rule result table in `InvestigationView.tsx` Evidence Chain |
| **Database** | `rule_results.applicability` field |
| **Demo Flow** | Compare Scenarios 1 vs 7 (same rules, different applicability) |
| **Test** | `test_rules.py` |

---

## REQ-09: Cross-Evidence Consistency Engine

| Field | Detail |
|---|---|
| **Requirement** | Detect conflicts between OCR, barcode, and user-provided identity |
| **Implementation** | Multi-source consistency checks with CONSISTENT/CONFLICTING states |
| **Backend** | `ai/consistency_engine.py` — `ConsistencyEngine`; `ai/consistency.py` — `ConsistencyScreening` |
| **Frontend** | Consistency warnings shown in `Scanner.tsx` result and identity conflict banner in `InvestigationView.tsx` |
| **Database** | `consistency_checks` table |
| **Demo Flow** | Scenario 4 (GTIN mismatch) |
| **Test** | `test_consistency.py`, `test_contradictions.py` |

---

## REQ-10: Evidence Quality Intelligence

| Field | Detail |
|---|---|
| **Requirement** | Assign quality states to evidence (SUPPORTED, UNCERTAIN, CONFLICTING, NOT_DETECTED, etc.) |
| **Implementation** | `EvidenceQualityEvaluator` assesses each extracted field |
| **Backend** | `ai/evidence_quality.py` |
| **Frontend** | Evidence state badges in `InvestigationView.tsx` Evidence Chain |
| **Database** | `extracted_fields.evidence_state`, `extracted_fields.quality_reasons` |
| **Demo Flow** | Scenario 6 (OCR uncertainty — UNCERTAIN state, then officer correction) |
| **Test** | `test_evidence_quality.py` |

---

## REQ-11: Citizen Signal Collection & Clustering

| Field | Detail |
|---|---|
| **Requirement** | Aggregate multiple citizen reports about the same product without auto-determining guilt |
| **Implementation** | Perceptual hash clustering; `ProductCluster` entity |
| **Backend** | `backend/app/services/clustering.py`; `routers/products.py` citizen-report endpoints |
| **Frontend** | `CitizenPortal.tsx` — citizen submission; `InvestigationView.tsx` — Citizen Signals tab |
| **Database** | `citizen_reports`, `product_clusters` |
| **Demo Flow** | Scenario 5 (8 citizen signals → PRIORITY_REVIEW cluster) |
| **Test** | `test_clustering.py` |

---

## REQ-12: Evidence-Based Prioritization

| Field | Detail |
|---|---|
| **Requirement** | Rank cases for officer review based on evidence weight, not arbitrary scores |
| **Implementation** | 6-factor weighted prioritization engine with explainable reasons |
| **Backend** | `backend/app/services/prioritization.py` — `EvidencePrioritizationEngine` |
| **Frontend** | Priority queue in `OfficerDashboard.tsx`; priority badge in `InvestigationView.tsx` |
| **Database** | `product_clusters.priority_score`, `priority_class`, `priority_reasons` |
| **Demo Flow** | Officer dashboard → sorted queue shows Scenario 5 at top |
| **Test** | `test_prioritization.py` |

---

## REQ-13: Officer Intelligence Workbench

| Field | Detail |
|---|---|
| **Requirement** | Authorized officers can inspect evidence, verify/correct, and record decisions with audit trail |
| **Implementation** | Officer review flow with role-gated endpoints |
| **Backend** | `routers/officer.py`, `routers/scans.py` — `/evidence/{id}/correct` endpoint |
| **Frontend** | `InvestigationView.tsx` — Officer Action Panel, correction form |
| **Database** | `officer_reviews`, `evidence_corrections`, `decision_traces` |
| **Demo Flow** | Scenario 6 — Open Investigation Workspace → correct MRP field → view audit trail |
| **Test** | `test_adversarial.py::test_authorization_header_parsing` |

---

## REQ-14: Audit Trail

| Field | Detail |
|---|---|
| **Requirement** | Every officer action must be recorded with actor, timestamp, old/new value, reason |
| **Implementation** | `DecisionTrace` for pipeline steps; `OfficerReview` + `EvidenceCorrection` for officer actions |
| **Backend** | Decision traces written at each pipeline stage in `ScreeningService`; corrections in `scans.py` |
| **Frontend** | Audit Trail tab in `InvestigationView.tsx` |
| **Database** | `decision_traces`, `officer_reviews`, `evidence_corrections` |
| **Demo Flow** | After officer correction in Scenario 6, view Audit Trail tab |
| **Test** | `test_adversarial.py::test_authorization_header_parsing` |

---

## REQ-15: ML Integration Architecture (Model-Ready)

| Field | Detail |
|---|---|
| **Requirement** | Architecture ready for ML inference; transparent fallback when model unavailable |
| **Implementation** | `ModelRegistry` with explicit states; YOLO→CV fallback; evidence source tagging |
| **Backend** | `backend/app/services/ml/registry.py`, `detection_service.py`, `screening_service.py` |
| **Frontend** | ML Model Health panel in `AnalyticsDashboard.tsx` |
| **Database** | `model_versions` table |
| **Demo Flow** | Analytics Dashboard → System Overview → ML Model Health: shows MODEL_NOT_FOUND + fallback active |
| **Test** | `test_ml_integration.py`, `test_adversarial.py::test_model_registry_correctly_reports_missing_model` |

---

## REQ-16: Product Intelligence & Analytics

| Field | Detail |
|---|---|
| **Requirement** | Officers can view aggregated screening intelligence over time |
| **Implementation** | Multi-layer analytics dashboard |
| **Backend** | `routers/analytics.py` — overview, trends, categories, requirements, quality, consistency, prioritization |
| **Frontend** | `AnalyticsDashboard.tsx` with 4 layers: System Overview, Product Intelligence, Evidence, Officer |
| **Database** | Queries across `scans`, `extracted_fields`, `rule_results`, `product_clusters`, `officer_reviews` |
| **Demo Flow** | Navigate to Analytics → System Overview → show scan trends and evidence stats |
| **Test** | Manual verification (no dedicated analytics unit test) |

---

## REQ-17: Authorization & Role Separation

| Field | Detail |
|---|---|
| **Requirement** | Citizens cannot access officer functions; officer endpoints must require authorization |
| **Implementation** | Role-header checking (`x-user-role`) on officer endpoints |
| **Backend** | `routers/officer.py` — `x_user_role` header check; `routers/scans.py` evidence correction |
| **Frontend** | `Scanner.tsx` — role-conditional UI (citizen vs officer action buttons) |
| **Database** | `users.role` field |
| **Demo Flow** | Login as OFFICER → officer features visible. Login as CITIZEN → investigation workspace hidden |
| **Test** | `test_adversarial.py::test_authorization_header_parsing` |
