"""
test_cases.py - Officer Case Management & Action Workflow Tests

Tests cover:
1.  Case creation with valid OFFICER_CREATED trigger
2.  Case creation with valid CROSS_EVIDENCE_CONFLICT trigger
3.  Case creation rejection: no backing evidence for CROSS_EVIDENCE_CONFLICT
4.  Case creation rejection: raw OCR only (no scan_id, no cluster_id)
5.  Case creation rejection: unknown trigger type
6.  List cases returns correct structure
7.  List cases filtered by status
8.  Get case detail (existing)
9.  Get case detail (not found)
10. Status transition: REVIEW_REQUIRED -> UNDER_REVIEW
11. Status transition rejection: invalid transition
12. Status transition rejection: terminal state (DUPLICATE)
13. Add officer note to case
14. Record EVIDENCE_VERIFIED finding
15. Record INSPECTION_REQUIRED finding (auto-transitions status)
16. Record ISSUE_NOT_CONFIRMED finding (auto-transitions to DISMISSED)
17. Assign inspection to case
18. Close case with structured outcome
19. Reopen a closed case
20. Mark case as duplicate
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.database import Base, get_db
from backend.app.models.models import (
    Investigation, CaseNote, CaseInspection, CaseAuditEvent,
    ProductCluster, Scan, User, ConsistencyCheck, RuleResult, ExtractedField
)

# ─── Test Database Setup ──────────────────────────────────────────────────────

TEST_DB_URL = "sqlite:///./test_cases_temp.db"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Create all tables before tests; drop after."""
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)
    try:
        if os.path.exists("test_cases_temp.db"):
            os.remove("test_cases_temp.db")
    except PermissionError:
        pass  # Windows may keep the file locked briefly; safe to ignore in CI


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="function")
def db():
    """Fresh DB session per test."""
    db = TestSessionLocal()
    yield db
    db.rollback()
    db.close()


# ─── Helpers ──────────────────────────────────────────────────────────────────

OFFICER_HEADERS = {"X-User-Role": "OFFICER"}


def _seed_officer(db) -> User:
    officer = db.query(User).filter(User.role == "OFFICER").first()
    if not officer:
        officer = User(
            email="test_officer@lm.gov.in",
            hashed_password="hashed",
            full_name="Test Officer",
            role="OFFICER",
            badge_number="LM-TEST-001"
        )
        db.add(officer)
        db.commit()
        db.refresh(officer)
    return officer


def _seed_cluster_with_conflict(db) -> tuple:
    """Seed a ProductCluster + Scan + ConsistencyCheck (REVIEW_REQUIRED)."""
    officer = _seed_officer(db)

    cluster = ProductCluster(
        product_name="Test Product",
        brand="Test Brand",
        gtin="1234567890123",
        status="REVIEW_REQUIRED",
        report_count=3,
        ai_flag_count=1,
        priority_class="PRIORITY_REVIEW",
    )
    db.add(cluster)
    db.flush()

    scan = Scan(
        cluster_id=cluster.id,
        status="POTENTIAL_NON_COMPLIANCE",
        public_label="Potential Non-Compliance",
        image_hash="testhash1234",
        image_path="/tmp/test_scan.jpg",
        screening_confidence=0.85,
    )
    db.add(scan)
    db.flush()

    conflict = ConsistencyCheck(
        scan_id=scan.id,
        check_type="NET_QUANTITY_MISMATCH",
        status="REVIEW_REQUIRED",
        explanation="Declared 500g but barcode indicates 450g",
    )
    db.add(conflict)

    rule_result = RuleResult(
        scan_id=scan.id,
        rule_id="RULE_NET_WEIGHT",
        rule_name="Net Weight Labelling",
        status="POTENTIAL_NON_COMPLIANCE",
        applicability="REQUIRED",
        reason="Discrepancy in net weight.",
        confidence=0.85,
    )
    db.add(rule_result)

    db.commit()
    return cluster, scan


# ─── Tests ────────────────────────────────────────────────────────────────────

# ─ TEST 1: Create case with OFFICER_CREATED trigger ─────────────────────────

def test_01_create_case_officer_created(client, db):
    """OFFICER_CREATED trigger should succeed without evidence requirements."""
    officer = _seed_officer(db)
    resp = client.post("/api/v1/cases", json={
        "trigger_type": "OFFICER_CREATED",
        "reason": "Test officer-initiated case."
    }, headers=OFFICER_HEADERS)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "REVIEW_REQUIRED"
    assert data["trigger_type"] == "OFFICER_CREATED"
    assert "case_number" in data
    assert data["case_number"].startswith("LM-")
    assert "disclaimer" in data


# ─ TEST 2: Create case with CROSS_EVIDENCE_CONFLICT trigger ─────────────────

def test_02_create_case_cross_evidence_conflict(client, db):
    """CROSS_EVIDENCE_CONFLICT trigger requires and uses ConsistencyCheck evidence."""
    cluster, scan = _seed_cluster_with_conflict(db)

    resp = client.post("/api/v1/cases", json={
        "trigger_type": "CROSS_EVIDENCE_CONFLICT",
        "scan_id": scan.id,
        "cluster_id": cluster.id,
        "reason": "Conflict between barcode and label weight."
    }, headers=OFFICER_HEADERS)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["trigger_type"] == "CROSS_EVIDENCE_CONFLICT"
    assert data["status"] == "REVIEW_REQUIRED"


# ─ TEST 3: Case creation rejected: no backing evidence ──────────────────────

def test_03_case_creation_rejected_no_evidence(client, db):
    """CROSS_EVIDENCE_CONFLICT without a real conflict should be rejected (422)."""
    resp = client.post("/api/v1/cases", json={
        "trigger_type": "CROSS_EVIDENCE_CONFLICT",
        "reason": "Should be rejected."
    }, headers=OFFICER_HEADERS)

    assert resp.status_code == 422, resp.text
    assert "blocked" in resp.json()["detail"].lower() or "require" in resp.json()["detail"].lower()


# ─ TEST 4: Case creation rejected: raw OCR only trigger ─────────────────────

def test_04_case_creation_rejected_raw_ocr(client, db):
    """REPEATED_OBSERVATION without a real cluster with >= 2 observations should fail."""
    resp = client.post("/api/v1/cases", json={
        "trigger_type": "REPEATED_OBSERVATION",
        "reason": "Should fail — no cluster."
    }, headers=OFFICER_HEADERS)

    assert resp.status_code == 422, resp.text


# ─ TEST 5: Unknown trigger type rejected ────────────────────────────────────

def test_05_unknown_trigger_type_rejected(client, db):
    """Invalid trigger_type should return 400."""
    resp = client.post("/api/v1/cases", json={
        "trigger_type": "MADE_UP_TRIGGER",
        "reason": "Should fail."
    }, headers=OFFICER_HEADERS)

    assert resp.status_code == 400, resp.text


# ─ TEST 6: List cases returns correct structure ──────────────────────────────

def test_06_list_cases_structure(client, db):
    """GET /cases should return cases list with status_counts."""
    resp = client.get("/api/v1/cases", headers=OFFICER_HEADERS)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "cases" in data
    assert "status_counts" in data
    assert "total" in data
    assert "page" in data
    assert isinstance(data["cases"], list)
    assert "REVIEW_REQUIRED" in data["status_counts"]


# ─ TEST 7: List cases filtered by status ────────────────────────────────────

def test_07_list_cases_filtered(client, db):
    """GET /cases?status=REVIEW_REQUIRED should only return REVIEW_REQUIRED cases."""
    resp = client.get("/api/v1/cases?status=REVIEW_REQUIRED", headers=OFFICER_HEADERS)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    for c in data["cases"]:
        assert c["status"] == "REVIEW_REQUIRED"


# ─ TEST 8: Get case detail ──────────────────────────────────────────────────

def test_08_get_case_detail(client, db):
    """GET /cases/{case_id} should return full case detail."""
    # Create a case first
    create_resp = client.post("/api/v1/cases", json={
        "trigger_type": "OFFICER_CREATED",
        "reason": "Test case for detail check."
    }, headers=OFFICER_HEADERS)

    assert create_resp.status_code == 200
    case_id = create_resp.json()["case_id"]

    resp = client.get(f"/api/v1/cases/{case_id}", headers=OFFICER_HEADERS)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["case_id"] == case_id
    assert "evidence" in data
    assert "rule_results" in data
    assert "consistency_checks" in data
    assert "notes" in data
    assert "inspections" in data
    assert "audit_trail" in data
    assert "disclaimer" in data
    assert len(data["audit_trail"]) >= 1  # At least CASE_CREATED event
    assert data["audit_trail"][0]["action"] == "CASE_CREATED"


# ─ TEST 9: Get case detail - not found ──────────────────────────────────────

def test_09_get_case_not_found(client, db):
    """GET /cases/nonexistent should return 404."""
    resp = client.get("/api/v1/cases/nonexistent-id-12345", headers=OFFICER_HEADERS)
    assert resp.status_code == 404


# ─ TEST 10: Status transition REVIEW_REQUIRED -> UNDER_REVIEW ───────────────

def test_10_status_transition_valid(client, db):
    """PATCH /cases/{id}/status with valid transition should succeed."""
    create_resp = client.post("/api/v1/cases", json={
        "trigger_type": "OFFICER_CREATED",
        "reason": "Status transition test."
    }, headers=OFFICER_HEADERS)
    case_id = create_resp.json()["case_id"]

    resp = client.patch(f"/api/v1/cases/{case_id}/status", json={
        "status": "UNDER_REVIEW",
        "reason": "Starting review."
    }, headers=OFFICER_HEADERS)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["old_status"] == "REVIEW_REQUIRED"
    assert data["new_status"] == "UNDER_REVIEW"


# ─ TEST 11: Status transition rejection: invalid ─────────────────────────────

def test_11_status_transition_invalid(client, db):
    """PATCH /cases/{id}/status with invalid transition should return 422."""
    create_resp = client.post("/api/v1/cases", json={
        "trigger_type": "OFFICER_CREATED",
        "reason": "Invalid transition test."
    }, headers=OFFICER_HEADERS)
    case_id = create_resp.json()["case_id"]

    # REVIEW_REQUIRED -> RESOLVED is invalid
    resp = client.patch(f"/api/v1/cases/{case_id}/status", json={
        "status": "RESOLVED",
        "reason": "Jump to RESOLVED."
    }, headers=OFFICER_HEADERS)

    assert resp.status_code == 422, resp.text
    assert "Invalid status transition" in resp.json()["detail"]


# ─ TEST 12: Terminal state cannot transition ──────────────────────────────────

def test_12_terminal_status_cannot_transition(client, db):
    """Cases in DUPLICATE status should not allow further transitions."""
    # Create two cases
    r1 = client.post("/api/v1/cases", json={"trigger_type": "OFFICER_CREATED", "reason": "Original"}, headers=OFFICER_HEADERS)
    r2 = client.post("/api/v1/cases", json={"trigger_type": "OFFICER_CREATED", "reason": "Duplicate"}, headers=OFFICER_HEADERS)
    assert r1.status_code == 200 and r2.status_code == 200
    case1_id = r1.json()["case_id"]
    case2_id = r2.json()["case_id"]

    # Mark case2 as duplicate of case1
    dup_resp = client.post(f"/api/v1/cases/{case2_id}/duplicate", json={
        "duplicate_of_case_id": case1_id,
        "reason": "Duplicate investigation."
    }, headers=OFFICER_HEADERS)
    assert dup_resp.status_code == 200
    assert dup_resp.json()["status"] == "DUPLICATE"

    # Try to transition from DUPLICATE
    trans_resp = client.patch(f"/api/v1/cases/{case2_id}/status", json={
        "status": "UNDER_REVIEW"
    }, headers=OFFICER_HEADERS)
    assert trans_resp.status_code == 422


# ─ TEST 13: Add officer note ──────────────────────────────────────────────────

def test_13_add_officer_note(client, db):
    """POST /cases/{id}/notes should add a note and audit event."""
    create_resp = client.post("/api/v1/cases", json={
        "trigger_type": "OFFICER_CREATED",
        "reason": "Note test."
    }, headers=OFFICER_HEADERS)
    case_id = create_resp.json()["case_id"]

    note_resp = client.post(f"/api/v1/cases/{case_id}/notes", json={
        "note": "Physical label examined. Net weight appears consistent with declared value."
    }, headers=OFFICER_HEADERS)

    assert note_resp.status_code == 200, note_resp.text
    data = note_resp.json()
    assert "note_id" in data
    assert "author" in data

    # Verify note appears in detail
    detail = client.get(f"/api/v1/cases/{case_id}", headers=OFFICER_HEADERS).json()
    assert any(n["note"] == "Physical label examined. Net weight appears consistent with declared value." for n in detail["notes"])


# ─ TEST 14: Record EVIDENCE_VERIFIED finding ─────────────────────────────────

def test_14_record_finding_evidence_verified(client, db):
    """POST /cases/{id}/finding with EVIDENCE_VERIFIED should record finding."""
    create_resp = client.post("/api/v1/cases", json={
        "trigger_type": "OFFICER_CREATED",
        "reason": "Finding test."
    }, headers=OFFICER_HEADERS)
    case_id = create_resp.json()["case_id"]

    # Transition to UNDER_REVIEW first
    client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "UNDER_REVIEW"}, headers=OFFICER_HEADERS)

    finding_resp = client.post(f"/api/v1/cases/{case_id}/finding", json={
        "finding": "EVIDENCE_VERIFIED",
        "notes": "All evidence reviewed and found consistent with the product label."
    }, headers=OFFICER_HEADERS)

    assert finding_resp.status_code == 200, finding_resp.text
    data = finding_resp.json()
    assert data["finding"] == "EVIDENCE_VERIFIED"


# ─ TEST 15: INSPECTION_REQUIRED auto-transitions to ACTION_REQUIRED ──────────

def test_15_finding_inspection_required_transitions(client, db):
    """INSPECTION_REQUIRED finding should auto-transition to ACTION_REQUIRED."""
    create_resp = client.post("/api/v1/cases", json={
        "trigger_type": "OFFICER_CREATED",
        "reason": "Auto-transition test."
    }, headers=OFFICER_HEADERS)
    case_id = create_resp.json()["case_id"]

    client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "UNDER_REVIEW"}, headers=OFFICER_HEADERS)

    finding_resp = client.post(f"/api/v1/cases/{case_id}/finding", json={
        "finding": "INSPECTION_REQUIRED",
        "notes": "On-site physical inspection is required."
    }, headers=OFFICER_HEADERS)

    assert finding_resp.status_code == 200, finding_resp.text
    assert finding_resp.json()["status"] == "ACTION_REQUIRED"


# ─ TEST 16: ISSUE_NOT_CONFIRMED finding auto-dismisses ───────────────────────

def test_16_finding_issue_not_confirmed_dismisses(client, db):
    """ISSUE_NOT_CONFIRMED finding should auto-transition to DISMISSED."""
    create_resp = client.post("/api/v1/cases", json={
        "trigger_type": "OFFICER_CREATED",
        "reason": "Auto-dismiss test."
    }, headers=OFFICER_HEADERS)
    case_id = create_resp.json()["case_id"]

    client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "UNDER_REVIEW"}, headers=OFFICER_HEADERS)

    finding_resp = client.post(f"/api/v1/cases/{case_id}/finding", json={
        "finding": "ISSUE_NOT_CONFIRMED",
        "notes": "Reviewed evidence: no issue found. Signal was a false positive."
    }, headers=OFFICER_HEADERS)

    assert finding_resp.status_code == 200, finding_resp.text
    assert finding_resp.json()["status"] == "DISMISSED"


# ─ TEST 17: Assign inspection ─────────────────────────────────────────────────

def test_17_assign_inspection(client, db):
    """POST /cases/{id}/inspection should create inspection and transition to INSPECTION_ASSIGNED."""
    create_resp = client.post("/api/v1/cases", json={
        "trigger_type": "OFFICER_CREATED",
        "reason": "Inspection test."
    }, headers=OFFICER_HEADERS)
    case_id = create_resp.json()["case_id"]

    # Get to ACTION_REQUIRED status
    client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "UNDER_REVIEW"}, headers=OFFICER_HEADERS)
    client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "EVIDENCE_VERIFIED"}, headers=OFFICER_HEADERS)
    client.patch(f"/api/v1/cases/{case_id}/status", json={"status": "ACTION_REQUIRED"}, headers=OFFICER_HEADERS)

    insp_resp = client.post(f"/api/v1/cases/{case_id}/inspection", json={
        "location_hint": "Main Market, Sector 17",
        "notes": "Check weight on all shelf samples."
    }, headers=OFFICER_HEADERS)

    assert insp_resp.status_code == 200, insp_resp.text
    data = insp_resp.json()
    assert "inspection_id" in data
    assert data["case_status"] == "INSPECTION_ASSIGNED"


# ─ TEST 18: Close case ────────────────────────────────────────────────────────

def test_18_close_case(client, db):
    """POST /cases/{id}/close should close case with structured outcome."""
    create_resp = client.post("/api/v1/cases", json={
        "trigger_type": "OFFICER_CREATED",
        "reason": "Close test."
    }, headers=OFFICER_HEADERS)
    case_id = create_resp.json()["case_id"]

    close_resp = client.post(f"/api/v1/cases/{case_id}/close", json={
        "closure_outcome": "ISSUE_NOT_CONFIRMED",
        "reason": "After officer review, the evidence was found to be insufficient. No issue confirmed."
    }, headers=OFFICER_HEADERS)

    assert close_resp.status_code == 200, close_resp.text
    data = close_resp.json()
    assert data["status"] == "CLOSED"
    assert data["closure_outcome"] == "ISSUE_NOT_CONFIRMED"

    # Verify case is closed in system
    detail = client.get(f"/api/v1/cases/{case_id}", headers=OFFICER_HEADERS).json()
    assert detail["status"] == "CLOSED"


# ─ TEST 19: Reopen a closed case ──────────────────────────────────────────────

def test_19_reopen_case(client, db):
    """POST /cases/{id}/reopen should reopen a closed case. Original closure preserved in audit."""
    create_resp = client.post("/api/v1/cases", json={
        "trigger_type": "OFFICER_CREATED",
        "reason": "Reopen test."
    }, headers=OFFICER_HEADERS)
    case_id = create_resp.json()["case_id"]

    client.post(f"/api/v1/cases/{case_id}/close", json={
        "closure_outcome": "ISSUE_NOT_CONFIRMED",
        "reason": "Closed initially."
    }, headers=OFFICER_HEADERS)

    reopen_resp = client.post(f"/api/v1/cases/{case_id}/reopen", json={
        "reason": "New evidence submitted — reopening for fresh assessment."
    }, headers=OFFICER_HEADERS)

    assert reopen_resp.status_code == 200, reopen_resp.text
    data = reopen_resp.json()
    assert data["new_status"] == "UNDER_REVIEW"
    assert data["previous_status"] == "CLOSED"
    assert "audit trail" in data["message"].lower()

    # Verify audit trail preserves both CASE_CLOSED and CASE_REOPENED events
    audit = client.get(f"/api/v1/cases/{case_id}/audit", headers=OFFICER_HEADERS).json()
    actions = [e["action"] for e in audit["audit_trail"]]
    assert "CASE_CLOSED" in actions
    assert "CASE_REOPENED" in actions


# ─ TEST 20: Mark case as duplicate ───────────────────────────────────────────

def test_20_mark_duplicate(client, db):
    """POST /cases/{id}/duplicate should mark case as DUPLICATE with canonical reference."""
    r1 = client.post("/api/v1/cases", json={"trigger_type": "OFFICER_CREATED", "reason": "Canonical"}, headers=OFFICER_HEADERS)
    r2 = client.post("/api/v1/cases", json={"trigger_type": "OFFICER_CREATED", "reason": "Dup candidate"}, headers=OFFICER_HEADERS)
    assert r1.status_code == 200 and r2.status_code == 200

    canonical_id = r1.json()["case_id"]
    dup_id = r2.json()["case_id"]

    dup_resp = client.post(f"/api/v1/cases/{dup_id}/duplicate", json={
        "duplicate_of_case_id": canonical_id,
        "reason": "Confirmed duplicate of existing case."
    }, headers=OFFICER_HEADERS)

    assert dup_resp.status_code == 200, dup_resp.text
    data = dup_resp.json()
    assert data["status"] == "DUPLICATE"
    assert data["duplicate_of_case_id"] == canonical_id
    assert "canonical_case_number" in data

    # Verify the duplicate case cannot be marked duplicate again
    self_dup = client.post(f"/api/v1/cases/{dup_id}/duplicate", json={
        "duplicate_of_case_id": canonical_id,
    }, headers=OFFICER_HEADERS)
    assert self_dup.status_code == 422  # Already in terminal DUPLICATE state
