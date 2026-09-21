import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, EmailStr, Field

# Health Schema
class HealthResponse(BaseModel):
    status: str = "ok"

# Auth Schemas
class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: Optional[str] = None

# Scan Request / Response Schemas
class OCRTokenSchema(BaseModel):
    id: str
    text: str
    polygon: List[List[int]]
    confidence: float
    language: str = "en"
    model_version: str = "PaddleOCR-v4"

class ExtractedFieldSchema(BaseModel):
    field_name: str
    raw_value: str
    normalized_value: str
    confidence: float
    ocr_evidence_ids: List[str] = []
    extraction_method: str
    evidence_state: str = "UNCERTAIN"  # VERIFIED | SUPPORTED | UNCERTAIN | CONFLICTING | UNREADABLE | NOT_DETECTED | NOT_APPLICABLE | MANUALLY_VERIFIED
    quality_reasons: Optional[List[str]] = []
    source: Optional[str] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None

class RuleCheckSchema(BaseModel):
    rule_id: str
    rule_name: Optional[str] = None
    status: str
    reason: Optional[str] = None

class FindingSchema(BaseModel):
    finding_id: str
    scan_id: str
    field: str
    applicability: str = "REQUIRED"
    observed_value: Optional[str] = None
    rule_reference: str
    status: str
    explanation: str
    evidence_ids: List[str] = []
    created_at: str

class IdentityWarningSchema(BaseModel):
    type: str                           # PRODUCT_IDENTITY_MISMATCH | GTIN_CONSISTENCY_WARNING
    severity: str                       # NEEDS_REVIEW
    user_provided: Optional[str] = None
    image_evidence: Optional[str] = None
    ocr_value: Optional[str] = None
    barcode_decoded: Optional[str] = None
    explanation: str

class ConsistencyCheckSchema(BaseModel):
    check_id: str
    scan_id: str
    check_type: str
    status: str
    observed_values: Optional[Dict[str, Any]] = None
    calculated_value: Optional[str] = None
    explanation: str
    evidence_ids: List[str] = []
    created_at: str

class DecisionTraceStepSchema(BaseModel):
    stage: str
    status: str
    detail: Optional[str] = None

class ScanResponse(BaseModel):
    screening_id: str
    product_id: Optional[str] = None
    status: str
    image_quality: Dict[str, Any]
    detections: List[Dict[str, Any]] = []
    ocr: List[Dict[str, Any]] = []
    barcode: Dict[str, Any] = {}
    product_context: Dict[str, Any] = {}
    evidence: List[Dict[str, Any]] = []
    rule_results: List[Dict[str, Any]] = []
    consistency_checks: List[Dict[str, Any]] = []
    review_factors: List[Dict[str, Any]] = []
    decision_trace: List[Dict[str, Any]] = []
    evidence_summary: Optional[Dict[str, Any]] = None
    
    # Legacy fields to avoid immediate breakage if strictly needed by frontend
    public_label: str
    screening_confidence: float
    disclaimer: str
    rule_version: str = "2026.1"
    image_hash: Optional[str] = None
    processing_time_ms: Optional[float] = None

# Citizen Report Schemas
class ReportCreate(BaseModel):
    gtin: Optional[str] = None
    product_name: Optional[str] = None
    issue_category: str
    description: Optional[str] = None
    location_city: Optional[str] = "Delhi"
    scan_id: Optional[str] = None

class ReportResponse(BaseModel):
    report_id: str
    status: str
    message: str

class ReviewCreate(BaseModel):
    cluster_id: Optional[str] = None
    scan_id: Optional[str] = None
    product_id: Optional[str] = None
    decision: str  # CONFIRM, REJECT, REQUEST_MORE_EVIDENCE, MARK_UNDER_INVESTIGATION
    rationale: str

class PriorityQueueItem(BaseModel):
    cluster_id: str
    product_id: str
    product_name: str
    gtin: Optional[str] = None
    issue_type: str
    priority_score: float
    citizen_reports_count: int
    ai_flags_count: int
    recency: str
    status: str
