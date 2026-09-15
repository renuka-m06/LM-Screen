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
    evidence_state: str = "PRESENT"  # PRESENT | ABSENT_FROM_EVIDENCE | UNCERTAIN | NOT_APPLICABLE | NOT_CHECKED

class RuleCheckSchema(BaseModel):
    rule_id: str
    rule_name: Optional[str] = None
    status: str
    reason: Optional[str] = None

class IdentityWarningSchema(BaseModel):
    type: str                           # PRODUCT_IDENTITY_MISMATCH | GTIN_CONSISTENCY_WARNING
    severity: str                       # NEEDS_REVIEW
    user_provided: Optional[str] = None
    image_evidence: Optional[str] = None
    ocr_value: Optional[str] = None
    barcode_decoded: Optional[str] = None
    explanation: str

class DecisionTraceStepSchema(BaseModel):
    stage: str
    status: str
    detail: Optional[str] = None

class ScanResponse(BaseModel):
    scan_id: str
    product_id: Optional[str] = None
    status: str
    public_label: str
    screening_confidence: float
    quality: Dict[str, Any]
    ocr_tokens: List[OCRTokenSchema] = []
    extracted_fields: Dict[str, Any] = {}
    checks_performed: List[RuleCheckSchema] = []
    checks_not_performed: List[Dict[str, Any]] = []
    rule_version: str = "2026.1"
    review_reasons: List[str] = []
    identity_warnings: List[Dict[str, Any]] = []
    decision_trace: List[Dict[str, Any]] = []
    processing_time_ms: Optional[float] = None
    ocr_token_count: Optional[int] = None
    image_hash: Optional[str] = None
    disclaimer: str

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
