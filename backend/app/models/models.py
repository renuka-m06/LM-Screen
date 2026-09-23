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
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    reviews = relationship("OfficerReview", back_populates="officer")
    audit_logs = relationship("AuditLog", back_populates="actor")

class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=generate_uuid)
    gtin = Column(String, unique=True, index=True, nullable=True)
    barcode = Column(String, index=True, nullable=True)
    brand_name = Column(String, nullable=True)
    product_name = Column(String, nullable=False)
    manufacturer = Column(String, nullable=True)
    category = Column(String, default="general")
    subcategory = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    scans = relationship("Scan", back_populates="product")
    reports = relationship("CitizenReport", back_populates="product")
    clusters = relationship("ProductCluster", back_populates="product")
    images = relationship("ProductImage", back_populates="product")
    investigations = relationship("Investigation", back_populates="product")

class ProductImage(Base):
    __tablename__ = "product_images"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=True)
    file_path = Column(String, nullable=False)
    original_filename = Column(String, nullable=True)
    mime_type = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    image_width = Column(Integer, nullable=True)
    image_height = Column(Integer, nullable=True)
    capture_source = Column(String, nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    product = relationship("Product", back_populates="images")
    quality = relationship("ImageQuality", back_populates="image", uselist=False)
    detections = relationship("Detection", back_populates="image")

class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(String, primary_key=True, default=generate_uuid)
    model_name = Column(String, nullable=False, index=True)
    version = Column(String, nullable=False)
    model_type = Column(String, nullable=False)
    framework = Column(String, nullable=True)
    dataset_version = Column(String, nullable=True)
    status = Column(String, default="DEVELOPMENT")
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Scan(Base):
    __tablename__ = "scans"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=True)
    image_id = Column(String, ForeignKey("product_images.id"), nullable=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    image_hash = Column(String, index=True, nullable=False)
    image_path = Column(String, nullable=False)
    
    # Image Quality (Legacy fields, moving to ImageQuality table)
    quality_status = Column(String, nullable=True)
    blur_score = Column(Float, nullable=True)
    brightness_score = Column(Float, nullable=True)
    glare_ratio = Column(Float, nullable=True)

    # Screening Verdict
    status = Column(String, nullable=False, index=True)
    category = Column(String, nullable=True)
    model_pipeline_version = Column(String, nullable=True)
    public_label = Column(String, nullable=False)
    screening_confidence = Column(Float, nullable=False)
    rule_version = Column(String, default="2026.1")
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)

    product = relationship("Product", back_populates="scans")
    cluster_id = Column(String, ForeignKey("product_clusters.id"), nullable=True)
    cluster = relationship("ProductCluster", back_populates="scans")
    duplicate_of_scan_id = Column(String, ForeignKey("scans.id"), nullable=True)
    
    ocr_results = relationship("OCRResult", back_populates="scan", cascade="all, delete-orphan")
    extracted_fields = relationship("ExtractedField", back_populates="scan", cascade="all, delete-orphan")
    rule_results = relationship("RuleResult", back_populates="scan", cascade="all, delete-orphan")
    decision_traces = relationship("DecisionTrace", back_populates="scan", cascade="all, delete-orphan")
    classifications = relationship("ProductClassification", back_populates="scan", cascade="all, delete-orphan")
    review_factors = relationship("ReviewFactor", back_populates="scan", cascade="all, delete-orphan")
    consistency_checks = relationship("ConsistencyCheck", back_populates="scan", cascade="all, delete-orphan")

class ImageQuality(Base):
    __tablename__ = "image_quality"

    id = Column(String, primary_key=True, default=generate_uuid)
    image_id = Column(String, ForeignKey("product_images.id"), nullable=False)
    usable = Column(Boolean, default=True)
    quality_score = Column(Float, nullable=True)
    blur_score = Column(Float, nullable=True)
    brightness_score = Column(Float, nullable=True)
    resolution_score = Column(Float, nullable=True)
    issues = Column(JSON, nullable=True)
    method = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    image = relationship("ProductImage", back_populates="quality")

class Detection(Base):
    __tablename__ = "detections"

    id = Column(String, primary_key=True, default=generate_uuid)
    image_id = Column(String, ForeignKey("product_images.id"), nullable=False)
    model_version_id = Column(String, ForeignKey("model_versions.id"), nullable=True)
    object_type = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    x = Column(Float, nullable=True)
    y = Column(Float, nullable=True)
    width = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    image = relationship("ProductImage", back_populates="detections")

class OCRResult(Base):
    __tablename__ = "ocr_results"

    id = Column(String, primary_key=True, default=generate_uuid)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    detection_id = Column(String, ForeignKey("detections.id"), nullable=True)
    token_id = Column(String, nullable=False)
    text = Column(Text, nullable=False)
    polygon = Column(JSON, nullable=True) # Legacy polygon
    bbox = Column(JSON, nullable=True)
    confidence = Column(Float, nullable=False)
    language = Column(String, default="en")
    panel_type = Column(String, nullable=True)
    ocr_engine = Column(String, nullable=True)
    ocr_version = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    scan = relationship("Scan", back_populates="ocr_results")

class ProductClassification(Base):
    __tablename__ = "product_classifications"

    id = Column(String, primary_key=True, default=generate_uuid)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    category = Column(String, nullable=False)
    subcategory = Column(String, nullable=True)
    confidence = Column(Float, nullable=False)
    model_version_id = Column(String, ForeignKey("model_versions.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    scan = relationship("Scan", back_populates="classifications")

class ExtractedField(Base):
    """The Evidence Table"""
    __tablename__ = "extracted_fields"

    id = Column(String, primary_key=True, default=generate_uuid)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    field_name = Column(String, nullable=False, index=True)
    raw_value = Column(Text, nullable=True)
    raw_text = Column(Text, nullable=True)
    normalized_value = Column(Text, nullable=True) # Also used as field_value
    found = Column(Boolean, default=True)
    confidence = Column(Float, nullable=False) # Legacy float
    evidence_state = Column(String, default="UNCERTAIN")
    quality_reasons = Column(JSON, nullable=True)
    
    source_type = Column(String, nullable=True)
    source_image_id = Column(String, ForeignKey("product_images.id"), nullable=True)
    source_ocr_id = Column(String, ForeignKey("ocr_results.id"), nullable=True)
    source_detection_id = Column(String, ForeignKey("detections.id"), nullable=True)
    source_panel = Column(String, nullable=True)
    source_bbox = Column(JSON, nullable=True)
    
    ocr_evidence_ids = Column(JSON, nullable=True)
    extraction_method = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    scan = relationship("Scan", back_populates="extracted_fields")
    corrections = relationship("EvidenceCorrection", back_populates="evidence", cascade="all, delete-orphan")

class EvidenceCorrection(Base):
    __tablename__ = "evidence_corrections"

    id = Column(String, primary_key=True, default=generate_uuid)
    evidence_id = Column(String, ForeignKey("extracted_fields.id"), nullable=False)
    original_value = Column(Text, nullable=True)
    corrected_value = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    corrected_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    evidence = relationship("ExtractedField", back_populates="corrections")

class RuleProfile(Base):
    __tablename__ = "rule_profiles"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    version = Column(String, nullable=False)
    status = Column(String, default="ACTIVE")
    effective_from = Column(DateTime, default=datetime.datetime.utcnow)
    effective_to = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    rules = relationship("Rule", back_populates="profile")

class Rule(Base):
    __tablename__ = "rules"

    id = Column(String, primary_key=True, default=generate_uuid)
    rule_profile_id = Column(String, ForeignKey("rule_profiles.id"), nullable=True)
    rule_code = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    required_evidence = Column(JSON, nullable=True)
    severity = Column(String, nullable=True)
    version = Column(String, nullable=False)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    profile = relationship("RuleProfile", back_populates="rules")

class RuleResult(Base):
    __tablename__ = "rule_results"

    id = Column(String, primary_key=True, default=generate_uuid)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    rule_id = Column(String, nullable=False, index=True)
    rule_name = Column(String, nullable=False)
    version = Column(String, default="2026.1")
    status = Column(String, nullable=False, index=True)
    applicability = Column(String, nullable=False, default="REQUIRED")
    confidence = Column(Float, nullable=False, default=1.0)
    reason = Column(Text, nullable=False)
    evaluated_at = Column(DateTime, default=datetime.datetime.utcnow)

    scan = relationship("Scan", back_populates="rule_results")

class RuleResultEvidence(Base):
    __tablename__ = "rule_result_evidence"

    rule_result_id = Column(String, ForeignKey("rule_results.id"), primary_key=True)
    evidence_id = Column(String, ForeignKey("extracted_fields.id"), primary_key=True)

class ConsistencyCheck(Base):
    __tablename__ = "consistency_checks"

    id = Column(String, primary_key=True, default=generate_uuid)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    check_type = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)
    observed_values = Column(JSON, nullable=True)
    calculated_value = Column(String, nullable=True)
    explanation = Column(Text, nullable=False)
    evidence_ids = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    scan = relationship("Scan", back_populates="consistency_checks")

class ReviewFactor(Base):
    __tablename__ = "review_factors"

    id = Column(String, primary_key=True, default=generate_uuid)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=False)
    rule_result_id = Column(String, ForeignKey("rule_results.id"), nullable=True)
    factor_type = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    resolved = Column(Boolean, default=False)
    resolved_by = Column(String, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    scan = relationship("Scan", back_populates="review_factors")

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
    image_id = Column(String, ForeignKey("product_images.id"), nullable=True)
    reporter_hash = Column(String, nullable=False)
    issue_category = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    location_city = Column(String, nullable=True)
    status = Column(String, default="UNVERIFIED", index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    product = relationship("Product", back_populates="reports")

class Investigation(Base):
    """Officer Case — the core case management entity.
    
    Lifecycle states:
      REVIEW_REQUIRED → UNDER_REVIEW → EVIDENCE_VERIFIED → ACTION_REQUIRED
      → INSPECTION_ASSIGNED → RESOLVED
    Terminal: EVIDENCE_INSUFFICIENT, CLOSED, DISMISSED, DUPLICATE
    Reopenable: RESOLVED, CLOSED, DISMISSED → UNDER_REVIEW
    """
    __tablename__ = "investigations"

    id = Column(String, primary_key=True, default=generate_uuid)
    case_number = Column(String, unique=True, index=True, nullable=True)  # LM-YYYY-NNNNN

    # Source links
    product_id = Column(String, ForeignKey("products.id"), nullable=True)
    cluster_id = Column(String, ForeignKey("product_clusters.id"), nullable=True)
    source_scan_ids = Column(JSON, nullable=True)  # List of scan IDs that triggered this case
    scan_id = Column(String, ForeignKey("scans.id"), nullable=True)  # Primary trigger scan

    # Trigger metadata
    trigger_type = Column(String, nullable=True, index=True)
    # CROSS_EVIDENCE_CONFLICT | POTENTIAL_NON_COMPLIANCE | REPEATED_OBSERVATION
    # | OFFICER_CREATED | CITIZEN_OBSERVATION | EVIDENCE_PATTERN | PRIORITIZATION_SIGNAL
    trigger_description = Column(Text, nullable=True)

    # Identity snapshot (denormalized at case creation time)
    product_identity_snapshot = Column(JSON, nullable=True)
    # {brand, product_name, variant, gtin, category, net_quantity}

    priority = Column(String, default="MEDIUM", index=True)  # LOW | MEDIUM | HIGH | PRIORITY_REVIEW
    status = Column(String, default="REVIEW_REQUIRED", index=True)
    # REVIEW_REQUIRED | UNDER_REVIEW | EVIDENCE_VERIFIED | ACTION_REQUIRED
    # | INSPECTION_ASSIGNED | RESOLVED | EVIDENCE_INSUFFICIENT | CLOSED | DISMISSED | DUPLICATE

    assigned_officer = Column(String, ForeignKey("users.id"), nullable=True)
    reason = Column(Text, nullable=True)  # Creation reason

    # Officer finding
    finding = Column(String, nullable=True)
    # EVIDENCE_VERIFIED | ISSUE_NOT_CONFIRMED | MORE_EVIDENCE_REQUIRED
    # | INSPECTION_REQUIRED | DUPLICATE_CASE | RESOLVED
    finding_notes = Column(Text, nullable=True)
    finding_recorded_at = Column(DateTime, nullable=True)
    finding_recorded_by = Column(String, ForeignKey("users.id"), nullable=True)

    # Closure
    closure_reason = Column(Text, nullable=True)
    closure_outcome = Column(String, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    closed_by = Column(String, ForeignKey("users.id"), nullable=True)

    # Duplication
    duplicate_of_case_id = Column(String, ForeignKey("investigations.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    product = relationship("Product", back_populates="investigations")
    cluster = relationship("ProductCluster", foreign_keys=[cluster_id])
    assigned_officer_user = relationship("User", foreign_keys=[assigned_officer])
    notes = relationship("CaseNote", back_populates="case", cascade="all, delete-orphan")
    inspections = relationship("CaseInspection", back_populates="case", cascade="all, delete-orphan")
    audit_events = relationship("CaseAuditEvent", back_populates="case", cascade="all, delete-orphan")


class CaseNote(Base):
    """Officer note attached to a case. Immutable once written."""
    __tablename__ = "case_notes"

    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, ForeignKey("investigations.id"), nullable=False, index=True)
    author_id = Column(String, ForeignKey("users.id"), nullable=False)
    note = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    case = relationship("Investigation", back_populates="notes")
    author = relationship("User", foreign_keys=[author_id])


class CaseInspection(Base):
    """Field inspection assignment linked to a case."""
    __tablename__ = "case_inspections"

    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, ForeignKey("investigations.id"), nullable=False, index=True)
    assigned_to = Column(String, ForeignKey("users.id"), nullable=True)
    assigned_by = Column(String, ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime, default=datetime.datetime.utcnow)
    scheduled_at = Column(DateTime, nullable=True)
    location_hint = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(String, default="PENDING", index=True)  # PENDING | IN_PROGRESS | COMPLETED | CANCELLED
    inspection_notes = Column(Text, nullable=True)  # Filled after completion
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    case = relationship("Investigation", back_populates="inspections")
    assignee = relationship("User", foreign_keys=[assigned_to])
    assigner = relationship("User", foreign_keys=[assigned_by])


class CaseAuditEvent(Base):
    """Immutable per-case audit event. Never deleted, never overwritten."""
    __tablename__ = "case_audit_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, ForeignKey("investigations.id"), nullable=False, index=True)
    actor_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    # CASE_CREATED | STATUS_CHANGED | ASSIGNED | NOTE_ADDED | EVIDENCE_LINKED
    # | INSPECTION_ASSIGNED | FINDING_RECORDED | CASE_CLOSED | CASE_REOPENED
    # | EVIDENCE_CORRECTED | MARKED_DUPLICATE
    old_status = Column(String, nullable=True)
    new_status = Column(String, nullable=True)
    detail = Column(JSON, nullable=True)  # Action-specific extra data
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    case = relationship("Investigation", back_populates="audit_events")
    actor = relationship("User", foreign_keys=[actor_id])

class ProductCluster(Base):
    """Product/Case Cluster for aggregating multiple evidence submissions relating to the same identity."""
    __tablename__ = "product_clusters"

    id = Column(String, primary_key=True, default=generate_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=True) # Canonical product if confirmed
    
    # Deterministic Identity representation
    gtin = Column(String, nullable=True, index=True)
    brand = Column(String, nullable=True)
    product_name = Column(String, nullable=True)
    variant = Column(String, nullable=True)
    net_quantity = Column(String, nullable=True)

    match_method = Column(String, nullable=True) # e.g. GTIN_MATCH, BRAND_PRODUCT_MATCH, INITIAL
    match_strength = Column(String, default="NO_MATCH") # STRONG_MATCH, POSSIBLE_MATCH, NO_MATCH, REVIEW_REQUIRED
    
    # Aggregated metrics
    report_count = Column(Integer, default=1)
    ai_flag_count = Column(Integer, default=0)
    priority_score = Column(Float, default=0.0) # Keeping for legacy sorting fallback

    # Evidence-Based Prioritization
    priority_class = Column(String, default="STANDARD_REVIEW")
    priority_reasons = Column(JSON, nullable=True)
    evidence_strength = Column(String, nullable=True)
    actionability_state = Column(String, nullable=True)
    prioritization_version = Column(String, nullable=True)

    status = Column(String, default="REVIEW_REQUIRED")
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    product = relationship("Product", back_populates="clusters")
    scans = relationship("Scan", back_populates="cluster")
    reviews = relationship("OfficerReview", back_populates="cluster")

class OfficerReview(Base):
    __tablename__ = "officer_reviews"

    id = Column(String, primary_key=True, default=generate_uuid)
    cluster_id = Column(String, ForeignKey("product_clusters.id"), nullable=True)
    scan_id = Column(String, ForeignKey("scans.id"), nullable=True)
    officer_id = Column(String, ForeignKey("users.id"), nullable=False)
    decision = Column(String, nullable=False)
    rationale = Column(Text, nullable=False)
    previous_status = Column(String, nullable=True)
    new_status = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    cluster = relationship("ProductCluster", back_populates="reviews")
    officer = relationship("User", back_populates="reviews")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    actor_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(String, nullable=False)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    actor = relationship("User", back_populates="audit_logs")

class ModelFeedback(Base):
    __tablename__ = "model_feedback"

    id = Column(String, primary_key=True, default=generate_uuid)
    prediction_type = Column(String, nullable=False)
    prediction_id = Column(String, nullable=False)
    original_value = Column(Text, nullable=True)
    corrected_value = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    corrected_by = Column(String, ForeignKey("users.id"), nullable=True)
    model_version_id = Column(String, ForeignKey("model_versions.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
