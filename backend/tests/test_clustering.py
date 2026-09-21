import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.models.models import Base, Scan, ProductCluster, ExtractedField
from backend.app.services.identity_matcher import IdentityMatcher

# Test Setup
engine = create_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

@pytest.fixture
def db_session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_new_cluster_creation(db_session):
    matcher = IdentityMatcher(db_session)
    scan = Scan(id="scan-1", status="POTENTIAL_NON_COMPLIANCE", image_path="/tmp/test1.jpg", public_label="Test", screening_confidence=1.0, image_hash="hash1")
    db_session.add(scan)
    db_session.commit()
    
    # Add extracted fields
    db_session.add(ExtractedField(scan_id="scan-1", field_name="gtin", normalized_value="1234567890123", found=True, confidence=1.0, extraction_method="TEST"))
    db_session.commit()

    cluster = matcher.process_scan("scan-1")
    assert cluster is not None
    assert cluster.gtin == "1234567890123"
    assert cluster.match_method == "INITIAL"
    assert cluster.report_count == 1
    
    # Check scan linkage
    scan_updated = db_session.query(Scan).filter(Scan.id == "scan-1").first()
    assert scan_updated.cluster_id == cluster.id

def test_strong_gtin_match(db_session):
    matcher = IdentityMatcher(db_session)
    
    # Pre-existing cluster
    cluster1 = ProductCluster(id="cluster-1", gtin="8901234567890", match_method="INITIAL", match_strength="NO_MATCH")
    db_session.add(cluster1)
    
    # Scan with matching GTIN
    scan2 = Scan(id="scan-2", status="POTENTIAL_NON_COMPLIANCE", image_path="/tmp/test2.jpg", public_label="Test", screening_confidence=1.0, image_hash="hash2")
    db_session.add(scan2)
    db_session.commit()
    
    db_session.add(ExtractedField(scan_id="scan-2", field_name="gtin", normalized_value="8901234567890", found=True, confidence=1.0, extraction_method="TEST"))
    db_session.commit()

    cluster = matcher.process_scan("scan-2")
    assert cluster.id == "cluster-1"
    assert cluster.match_method == "GTIN_MATCH"
    assert cluster.match_strength == "STRONG_MATCH"

def test_deterministic_identity_match(db_session):
    matcher = IdentityMatcher(db_session)
    
    cluster1 = ProductCluster(id="cluster-2", brand="TATA", product_name="Salt", net_quantity="1kg", match_method="INITIAL")
    db_session.add(cluster1)
    
    scan3 = Scan(id="scan-3", status="PASS_SCREENING", image_path="/tmp/test3.jpg", public_label="Test", screening_confidence=1.0, image_hash="hash3")
    db_session.add(scan3)
    db_session.commit()
    
    db_session.add_all([
        ExtractedField(scan_id="scan-3", field_name="brand_name", normalized_value="TATA", found=True, confidence=1.0, extraction_method="TEST"),
        ExtractedField(scan_id="scan-3", field_name="product_name", normalized_value="Salt", found=True, confidence=1.0, extraction_method="TEST"),
        ExtractedField(scan_id="scan-3", field_name="net_quantity", normalized_value="1kg", found=True, confidence=1.0, extraction_method="TEST")
    ])
    db_session.commit()

    cluster = matcher.process_scan("scan-3")
    assert cluster.id == "cluster-2"
    assert cluster.match_method == "BRAND_PRODUCT_MATCH"
    assert cluster.match_strength == "POSSIBLE_MATCH"

def test_duplicate_image_deduplication(db_session):
    matcher = IdentityMatcher(db_session)
    
    cluster1 = ProductCluster(id="cluster-3", gtin="111")
    db_session.add(cluster1)
    
    scan4 = Scan(id="scan-4", cluster_id="cluster-3", image_hash="abcde12345", image_path="/tmp/test4.jpg", status="UNVERIFIED", public_label="Test", screening_confidence=1.0)
    db_session.add(scan4)
    db_session.commit()
    
    scan5 = Scan(id="scan-5", image_hash="abcde12345", image_path="/tmp/test5.jpg", status="UNVERIFIED", public_label="Test", screening_confidence=1.0)
    db_session.add(scan5)
    db_session.commit()

    cluster = matcher.process_scan("scan-5")
    assert cluster.id == "cluster-3"
    
    scan5_updated = db_session.query(Scan).filter(Scan.id == "scan-5").first()
    assert scan5_updated.duplicate_of_scan_id == "scan-4"
