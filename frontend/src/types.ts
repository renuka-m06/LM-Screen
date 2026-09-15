// LM-Screen TypeScript Types — Evidence-First Pipeline
// Aligned with backend ScanResponse and all API schemas

export interface OCRToken {
  id: string;
  text: string;
  polygon: number[][];
  confidence: number;
  language: string;
  model_version?: string;
}

export interface ExtractedField {
  field_name: string;
  raw_value: string;
  normalized_value: string;
  confidence: number;
  ocr_evidence_ids: string[];
  extraction_method: string;
  evidence_state?: string; // PRESENT | ABSENT_FROM_EVIDENCE | UNCERTAIN | NOT_APPLICABLE | NOT_CHECKED
  bounding_box?: { x: number; y: number; width: number; height: number };
}

export interface RuleCheck {
  rule_id: string;
  rule_name?: string;
  status: string; // PASS | POTENTIAL_NON_COMPLIANCE | NEEDS_REVIEW | NOT_APPLICABLE | RULE_REQUIRES_OFFICIAL_VERIFICATION
  reason?: string;
  confidence?: number;
  legal_reference?: string;
  applicable?: boolean;
  evidence_ids?: string[];
}

export interface IdentityWarning {
  type: string; // PRODUCT_IDENTITY_MISMATCH | GTIN_CONSISTENCY_WARNING
  severity: string;
  user_provided?: string;
  image_evidence?: string;
  ocr_value?: string;
  barcode_decoded?: string;
  explanation: string;
}

export interface DecisionTraceStep {
  stage: string;
  status: string;
  detail?: string;
}

export interface ImageQuality {
  status: string; // ACCEPTABLE | PARTIALLY_USABLE | RETAKE_REQUIRED
  quality_label?: string;
  blur_score?: number;
  brightness_score?: number;
  glare_ratio?: number;
  contrast_score?: number;
  resolution_ok?: boolean;
  width?: number;
  height?: number;
  reasons?: string[];
}

export interface ScanResult {
  scan_id: string;
  product_id?: string;
  status: 'PASS_SCREENING' | 'POTENTIAL_NON_COMPLIANCE' | 'NEEDS_REVIEW';
  public_label: string;
  screening_confidence: number;
  quality: ImageQuality;
  ocr_tokens: OCRToken[];
  extracted_fields: Record<string, ExtractedField>;
  checks_performed: RuleCheck[];
  checks_not_performed: Array<Record<string, unknown>>;
  rule_version: string;
  review_reasons: string[];
  identity_warnings: IdentityWarning[];
  decision_trace: DecisionTraceStep[];
  processing_time_ms?: number;
  ocr_token_count?: number;
  image_hash?: string;
  disclaimer: string;
}

export interface PriorityQueueItem {
  cluster_id: string;
  product_id: string;
  product_name: string;
  gtin?: string;
  issue_type: string;
  priority_score: number;
  priority_label?: string; // HIGH | MEDIUM | LOW
  citizen_reports_count: number;
  ai_flags_count: number;
  priority_breakdown?: {
    citizen_signals: number;
    ai_flags: number;
    confirmed_history: number;
    evidence_quality: number;
    severity: number;
    recency: number;
  };
  recency: string;
  status: string;
}

export interface PriorityProduct {
  cluster_id: string;
  product_name: string;
  gtin?: string;
  issue_type: string;
  priority_score: number;
  priority_label: string;
  citizen_reports: number;
  ai_flags: number;
  status: string;
}

export interface DashboardStats {
  scans: {
    total: number;
    pass_screening: number;
    potential_non_compliance: number;
    needs_review: number;
  };
  citizen_intelligence: {
    total_signals: number;
    unverified_signals: number;
    issue_distribution?: Array<{ issue: string; count: number }>;
  };
  enforcement_prioritization: {
    active_clusters: number;
    completed_officer_reviews: number;
    priority_products?: PriorityProduct[];
  };
  scan_trend?: Array<{ date: string; scans: number }>;
}
