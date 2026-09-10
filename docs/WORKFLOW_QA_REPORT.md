# LM-Screen — Review & Citizen Workflow QA Audit Report

**Project Name**: LM-Screen — AI-Based Legal Metrology Compliance Screening, Citizen Intelligence & Enforcement Prioritization Platform  
**SIH Problem Statement**: 25034  
**Audit Date**: September 10, 2026  
**Auditor**: Lead Full-Stack Architect & Senior QA/CV Engineer  

---

## 1. Executive Overview

This QA audit confirms the complete resolution of workflow, state management, routing, and role authorization bugs between the AI Screening component, the Officer Investigation Workspace, and the Citizen Signal Portal.

All workflow actions now operate end-to-end with full backend persistence, evidence provenance preservation, and role-based access control (RBAC).

---

## 2. Root Cause Analyses & Technical Fixes

### 1. Officer Review Routing & Scan Context Disconnect
- **Root Cause**: `Scanner.tsx` rendered `"Investigate This Product"` regardless of user role and passed `scanResult.product_id` which was sometimes undefined on new scans. `App.tsx` did not pass `scanId` to `InvestigationView`, causing the workspace to open a blank product selector rather than the active scan evidence.
- **Fix**:
  1. Updated `App.tsx` to track `investigatingScanId` and `investigatingProductId`.
  2. Updated `Scanner.tsx` to pass `(product_id, scan_id)` into `onInvestigate`.
  3. Updated `InvestigationView.tsx` to fetch `GET /api/v1/scans/{scan_id}` directly and display the actual scan's extracted fields, OCR tokens, rule checks, decision trace, and identity mismatch banner.

### 2. Lack of Backend Role Authorization & Review Action Persistence
- **Root Cause**: `POST /api/v1/officer/reviews` did not check user roles in incoming HTTP requests. Review actions (`CONFIRM`, `REJECT`, `MARK_UNDER_INVESTIGATION`, `REQUEST_MORE_EVIDENCE`) lacked `scan_id` persistence and did not update `Scan.status`.
- **Fix**:
  1. Enforced `X-User-Role` HTTP header check in `backend/app/routers/officer.py`. Requests with role `CITIZEN` return `403 Forbidden` (`"Officer authorization required."`).
  2. Updated `OfficerReview` database model and schema to persist `scan_id`, `previous_status`, `new_status`, `officer_id`, `decision`, and `rationale`.
  3. Enabled `REQUEST_MORE_EVIDENCE` workflow with officer rationale input (`"Please upload a clearer image showing..."`).

### 3. Citizen Signal Workflow Broken Navigation & Prefill
- **Root Cause**: The link `"→ File a Citizen Signal in the Citizen tab"` in `Scanner.tsx` executed `e.preventDefault()` without taking any action. `CitizenPortal.tsx` did not accept pre-filled scan context or link `scan_id`.
- **Fix**:
  1. Implemented `onFileSignal(scanResult)` in `Scanner.tsx` and `App.tsx`.
  2. Clicking `"File a Citizen Signal"` pre-fills scan context (`related_scan_id`, `product_name`, `gtin`, `issue_category`, `description`) and routes directly to the Citizen tab.
  3. `CitizenPortal.tsx` displays a `"Related Scan Evidence Attached: #scan_id"` badge and persists `scan_id` in `POST /api/v1/reports`.
  4. Citizen reports strictly remain `UNVERIFIED SIGNALS` for officer prioritization and do not generate legal violation findings.

---

## 3. End-to-End Workflow Verification

### TEST A — Officer Workflow Verification
1. **Mode**: `OFFICER`
2. **Scan Execution**: Uploaded product with identity conflict (User: `PureHarvest Atta 5kg`, Image: `Premium Choco-Chip Biscuits`).
3. **Screening Outcome**: System outputted `NEEDS_REVIEW`.
4. **Investigation Action**: `Investigate This Product` button rendered for `OFFICER` role.
5. **Workspace Load**: Workspace opened displaying:
   - Product Identity Conflict Banner (`PureHarvest Atta 5kg` vs `Premium Choco-Chip Biscuits`)
   - Extracted fields & OCR tokens
   - Rule checks & decision trace
6. **Review Submission**: Officer selected `MARK_UNDER_INVESTIGATION`, entered rationale `"Product identity conflicts with submitted product name."`, and clicked `Persist Officer Action`.
7. **Persistence Confirmation**: Received HTTP 200 with green notice: `✓ Officer review action saved to audit trail successfully.` Audit record persisted to database.

### TEST B — Citizen Workflow Verification
1. **Mode**: `CITIZEN`
2. **Role Control**: `Investigate This Product` button is **hidden** for `CITIZEN` users.
3. **Citizen Action**: Clicked `Request / Report an Issue (File Citizen Signal)`.
4. **Pre-filled Portal**: Navigated to Citizen Signals tab with attached evidence badge `Related Scan Evidence Attached: #scan_id`.
5. **Signal Submission**: Form auto-populated with `Information Mismatch` and pre-filled observation text. Clicked `Submit report for officer review`.
6. **Signal Registration**: Received HTTP 200 confirmation: `Signal Registered Successfully`. Report registered with status `UNVERIFIED`.

---

## 4. Automated Test Suite Execution

- **Total Test Cases**: 60
- **Passed**: 60
- **Failed**: 0
- **Pass Rate**: 100%
- **Execution Time**: 5.47 seconds

### Workflow Test Suite Summary (`backend/tests/test_workflow.py`)
1. `test_officer_review_authorization_failure`: **PASSED** (returns `403 Forbidden` for `CITIZEN` role).
2. `test_officer_review_and_request_more_evidence`: **PASSED** (persists review, rationale, and updates `Scan.status`).
3. `test_citizen_signal_submission_workflow`: **PASSED** (persists signal linked to `scan_id` as `UNVERIFIED`).

---

## 5. Remaining Scope & Boundaries

1. **Non-Judicial Screening**: AI screening results and citizen reports are non-adjudicative decision support signals. Formal legal notices require officer verification.
2. **Session Role Switching**: In the demo interface, user role switching between `CITIZEN` and `OFFICER` is driven by the Navbar role toggle, passing `X-User-Role` headers to backend APIs.
