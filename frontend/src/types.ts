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
  evidence_state?: string; // VERIFIED | SUPPORTED | UNCERTAIN | CONFLICTING | UNREADABLE | NOT_DETECTED | NOT_APPLICABLE | MANUALLY_VERIFIED
  quality_reasons?: string[];
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

export interface Finding {
  finding_id: string;
  scan_id: string;
  field: string;
  applicability: string;
  observed_value: string | null;
  rule_reference: string;
  status: string;
  explanation: string;
  evidence_ids: string[];
  created_at: string;
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

export interface ConsistencyCheck {
  check_id: string;
  scan_id: string;
  check_type: string;
  status: string; // CONSISTENT | INCONSISTENT | REVIEW_REQUIRED | INSUFFICIENT_EVIDENCE
  observed_values?: Record<string, any>;
  calculated_value?: string;
  explanation: string;
  evidence_ids: string[];
  created_at: string;
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
  [key: string]: any;
  screening_id: string;
  product_id?: string;
  status: 'PASS_SCREENING' | 'POTENTIAL_NON_COMPLIANCE' | 'NEEDS_REVIEW';
  public_label: string;
  screening_confidence: number;
  image_quality: ImageQuality;
  detections: any[];
  ocr: OCRToken[];
  barcode: any;
  product_context: any;
  evidence: any[];
  rule_results: RuleCheck[];
  consistency_checks?: ConsistencyCheck[];
  review_factors: any[];
  decision_trace: DecisionTraceStep[];
  evidence_summary?: {
    applicable_fields: number;
    supported: number;
    uncertain: number;
    conflicting: number;
    unreadable: number;
    not_detected: number;
    not_applicable: number;
  };
  
  // Legacy
  rule_version: string;
  processing_time_ms?: number;
  image_hash?: string;
  disclaimer: string;
}

export interface PriorityQueueItem {
  cluster_id: string;
  product_id: string;
  product_name: string;
  gtin?: string;
  issue_type?: string;
  priority_score: number;
  priority_class: string;
  priority_label: string; 
  evidence_strength?: string;
  actionability_state?: string;
  citizen_reports_count: number;
  ai_flags_count: number;
  priority_reasons?: Array<{
    code: string;
    description: string;
  }>;
  recency: string;
  status: string;
}

export interface PriorityProduct {
  cluster_id: string;
  product_name: string;
  gtin?: string;
  issue_type?: string;
  priority_score: number;
  priority_class: string;
  priority_label: string;
  evidence_strength?: string;
  actionability_state?: string;
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
// ─── Case Management Types ───────────────────────────────────────────────────

export interface CaseProduct {
  name: string;
  brand?: string;
  gtin?: string;
  category?: string;
  net_quantity?: string;
}

export interface CaseAssignedOfficer {
  id: string;
  name: string;
  badge?: string;
}

export interface CaseSummary {
  case_id: string;
  case_number: string;
  product: CaseProduct;
  trigger_type: string;
  trigger_description: string;
  priority: string; // LOW | MEDIUM | HIGH | PRIORITY_REVIEW
  status: string;   // REVIEW_REQUIRED | UNDER_REVIEW | EVIDENCE_VERIFIED | ACTION_REQUIRED
                    // | INSPECTION_ASSIGNED | RESOLVED | CLOSED | DISMISSED | EVIDENCE_INSUFFICIENT | DUPLICATE
  finding?: string;
  assigned_officer?: CaseAssignedOfficer;
  evidence_count: number;
  conflict_count: number;
  cluster_id?: string;
  created_at: string;
  updated_at: string;
}

export interface CaseNote {
  note_id: string;
  author: string;
  note: string;
  created_at: string;
}

export interface CaseInspection {
  inspection_id: string;
  assigned_to?: string;
  assigned_by?: string;
  status: string; // PENDING | IN_PROGRESS | COMPLETED | CANCELLED
  location_hint?: string;
  scheduled_at?: string;
  notes?: string;
  inspection_notes?: string;
  completed_at?: string;
  assigned_at: string;
}

export interface CaseAuditEvent {
  event_id: string;
  action: string;
  actor: string;
  actor_id?: string;
  old_status?: string;
  new_status?: string;
  reason?: string;
  detail: Record<string, any>;
  timestamp: string;
}

export interface CaseEvidenceItem {
  evidence_id: string;
  scan_id: string;
  field_name: string;
  raw_value?: string;
  normalized_value?: string;
  evidence_state?: string;
  confidence?: number;
  source_type?: string;
  source_image_id?: string;
  source_bbox?: any;
  extraction_method?: string;
  corrections: Array<{
    original_value?: string;
    corrected_value?: string;
    reason?: string;
    corrected_at: string;
  }>;
  quality_reasons: string[];
}

export interface CaseDetail extends CaseSummary {
  reason?: string;
  product_identity_snapshot?: Record<string, any>;
  source_scan_ids?: string[];
  finding_notes?: string;
  finding_recorded_at?: string;
  closure_outcome?: string;
  closure_reason?: string;
  closed_at?: string;
  duplicate_of_case_id?: string;
  evidence: CaseEvidenceItem[];
  rule_results: Array<{
    rule_id: string;
    rule_name: string;
    status: string;
    applicability: string;
    reason: string;
    confidence?: number;
    evaluated_at: string;
  }>;
  consistency_checks: Array<{
    check_id: string;
    check_type: string;
    status: string;
    observed_values?: Record<string, any>;
    calculated_value?: string;
    explanation: string;
    evidence_ids: string[];
    created_at: string;
  }>;
  cluster?: {
    cluster_id: string;
    observation_count: number;
    ai_flag_count: number;
    match_method?: string;
    match_strength?: string;
    priority_class?: string;
    priority_reasons?: Array<{ code: string; description: string }>;
    evidence_strength?: string;
    actionability_state?: string;
    related_scan_count: number;
    related_scan_ids: string[];
  };
  notes: CaseNote[];
  inspections: CaseInspection[];
  audit_trail: CaseAuditEvent[];
  disclaimer: string;
}

export interface CaseListResponse {
  total: number;
  page: number;
  page_size: number;
  cases: CaseSummary[];
  status_counts: Record<string, number>;
}
