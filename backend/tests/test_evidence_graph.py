import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.main import app
from backend.app.database import Base, get_db
from backend.app.models.models import Scan, ExtractedField, RuleResult, EvidenceCorrection, User

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_evidence.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_findings_endpoint(setup_db):
    db = TestingSessionLocal()
    # Create mock scan
    scan = Scan(status="POTENTIAL_NON_COMPLIANCE", public_label="Review Required", image_hash="0000000", image_path="test.jpg", screening_confidence=1.0)
    db.add(scan)
    db.commit()

    # Create Mock Evidence
    field = ExtractedField(
        scan_id=scan.id,
        field_name="mrp",
        raw_value="MRP Rs. 150.00",
        normalized_value="150.00",
        source_type="OCR",
        confidence=1.0,
        extraction_method="regex"
    )
    db.add(field)

    # Create Mock RuleResult
    rule = RuleResult(
        scan_id=scan.id,
        rule_id="RULE_001",
        rule_name="MRP Validation",
        status="POTENTIAL_NON_COMPLIANCE",
        reason="MRP is not clearly readable",
        confidence=1.0
    )
    db.add(rule)
    db.commit()

    # Fetch findings
    response = client.get(f"/api/v1/scans/{scan.id}/findings")
    assert response.status_code == 200
    
    findings = response.json().get("findings", [])
    assert len(findings) == 1
    
    finding = findings[0]
    assert finding["field"] == "mrp"
    assert finding["observed_value"] == "150.00"
    assert "MRP Rs. 150.00" in finding["explanation"]
    assert "MRP Validation" in finding["explanation"]
    assert finding["evidence_ids"] == [field.id]

def test_evidence_correction(setup_db):
    db = TestingSessionLocal()
    
    # Create Officer
    officer = User(id="officer_1", email="officer@lm.gov.in", hashed_password="pw", role="OFFICER")
    db.add(officer)

    # Create mock scan and field
    scan = Scan(status="POTENTIAL_NON_COMPLIANCE", public_label="Review Required", image_hash="0000000", image_path="test.jpg", screening_confidence=1.0)
    db.add(scan)
    db.commit()

    field = ExtractedField(
        scan_id=scan.id,
        field_name="net_quantity",
        raw_value="NET 500 G",
        normalized_value="500 g",
        source_type="OCR",
        confidence=1.0,
        extraction_method="regex"
    )
    db.add(field)
    db.commit()

    payload = {
        "corrected_value": "500 ml",
        "reason": "Officer verified standard packaging"
    }

    # Execute correction
    response = client.post(
        f"/api/v1/scans/{scan.id}/evidence/{field.id}/correct",
        json=payload,
        headers={"X-User-Role": "OFFICER"}
    )
    
    assert response.status_code == 200
    
    # Verify DB state
    db.refresh(field)
    assert field.normalized_value == "500 ml"
    # Original raw value must be preserved!
    assert field.raw_value == "NET 500 G"

    correction = db.query(EvidenceCorrection).filter(EvidenceCorrection.evidence_id == field.id).first()
    assert correction is not None
    assert correction.original_value == "500 g"
    assert correction.corrected_value == "500 ml"
