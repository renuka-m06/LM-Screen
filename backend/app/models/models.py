import datetime
import uuid
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, default="CITIZEN") # CITIZEN, OFFICER, ADMIN
    badge_number = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    reviews = relationship("OfficerReview", back_populates="officer")

class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=generate_uuid)
    gtin = Column(String, unique=True, index=True, nullable=True)
    brand_name = Column(String, nullable=True)
    product_name = Column(String, nullable=False)
    manufacturer = Column(String, nullable=True)
    category = Column(String, default="general")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    scans = relationship("Scan", back_populates="product")
    reports = relationship("CitizenReport", back_populates="product")
    clusters = relationship("ProductCluster", back_populates="product")

class Scan(Base):
    __tablename__ = "scans"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=True)
    image_hash = Column(String, index=True, nullable=False)
    image_path = Column(String, nullable=False)
    
    # Image Quality
    quality_status = Column(String, nullable=False) # ACCEPTABLE, PARTIALLY_USABLE, RETAKE_REQUIRED
    blur_score = Column(Float, nullable=False)
    brightness_score = Column(Float, nullable=False)
    glare_ratio = Column(Float, nullable=False)

    # Screening Verdict
    status = Column(String, nullable=False) # PASS_SCREENING, POTENTIAL_NON_COMPLIANCE, NEEDS_REVIEW
    public_label = Column(String, nullable=False)
    screening_confidence = Column(Float, nullable=False)
    rule_version = Column(String, default="2026.1")
    
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    product = relationship("Product", back_populates="scans")
    ocr_results = relationship("OCRResult", back_populates="scan", cascade="all, delete-orphan")
    extracted_fields = relationship("ExtractedField", back_populates="scan", cascade="all, delete-orphan")
    rule_results = relationship("RuleResult", back_populates="scan", cascade="all, delete-orphan")
    decision_traces = relationship("DecisionTrace", back_populates="scan", cascade="all, delete-orphan")

class OCRResult(Base):
    __tablename__ = "ocr_results"

    id = Column(String, primary_key=True, default=generate_uuid)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    token_id = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    polygon = Column(JSON, nullable=False)
    confidence = Column(Float, nullable=False)
    language = Column(String, default="en")
    model_version = Column(String, default="PaddleOCR-v4")

    scan = relationship("Scan", back_populates="ocr_results")

class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id = Column(String, primary_key=True, default=generate_uuid)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    field_name = Column(String, nullable=False)
    raw_value = Column(Text, nullable=False)
    normalized_value = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    ocr_evidence_ids = Column(JSON, nullable=True)
    extraction_method = Column(String, nullable=False)

    scan = relationship("Scan", back_populates="extracted_fields")

class RuleResult(Base):
    __tablename__ = "rule_results"

    id = Column(String, primary_key=True, default=generate_uuid)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    rule_id = Column(String, nullable=False)
    rule_name = Column(String, nullable=False)
    version = Column(String, default="2026.1")
    status = Column(String, nullable=False) # PASS, POTENTIAL_NON_COMPLIANCE, NEEDS_REVIEW, NOT_APPLICABLE
    confidence = Column(Float, nullable=False)
    reason = Column(Text, nullable=False)

    scan = relationship("Scan", back_populates="rule_results")

class DecisionTrace(Base):
    __tablename__ = "decision_traces"

    id = Column(String, primary_key=True, default=generate_uuid)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    stage = Column(String, nullable=False)
    input_summary = Column(JSON, nullable=True)
    output_summary = Column(JSON, nullable=True)
    duration_ms = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    scan = relationship("Scan", back_populates="decision_traces")

class CitizenReport(Base):
    __tablename__ = "citizen_reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=True)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=True)
    reporter_hash = Column(String, nullable=False)
    issue_category = Column(String, nullable=False) # Suspicious MRP, Label Tampering, Missing Information, Quantity Concern, Information Mismatch, Other
    description = Column(Text, nullable=True)
    location_city = Column(String, nullable=True)
    status = Column(String, default="UNVERIFIED") # UNVERIFIED, IN_REVIEW, CONFIRMED, REJECTED
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    product = relationship("Product", back_populates="reports")

class ProductCluster(Base):
    __tablename__ = "product_clusters"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    issue_type = Column(String, nullable=False)
    report_count = Column(Integer, default=1)
    ai_flag_count = Column(Integer, default=0)
    priority_score = Column(Float, default=0.0)
    status = Column(String, default="UNVERIFIED")
    updated_at = Column(DateTime, default=datetime.datetime.utcnow)

    product = relationship("Product", back_populates="clusters")
    reviews = relationship("OfficerReview", back_populates="cluster")

class OfficerReview(Base):
    __tablename__ = "officer_reviews"

    id = Column(String, primary_key=True, default=generate_uuid)
    cluster_id = Column(String, ForeignKey("product_clusters.id"), nullable=True)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=True)
    officer_id = Column(String, ForeignKey("users.id"), nullable=False)
    decision = Column(String, nullable=False) # CONFIRM, REJECT, REQUEST_MORE_EVIDENCE, MARK_UNDER_INVESTIGATION
    rationale = Column(Text, nullable=False)
    previous_status = Column(String, nullable=True)
    new_status = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    cluster = relationship("ProductCluster", back_populates="reviews")
    officer = relationship("User", back_populates="reviews")

