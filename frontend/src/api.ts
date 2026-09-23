import type { ScanResult, PriorityQueueItem, DashboardStats, CaseDetail, CaseListResponse } from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
const TIMEOUT_MS = 45000; // 45 seconds — for fast endpoints
const SCAN_TIMEOUT_MS = 180000; // 180 seconds — OCR/ML pipeline (CPU warm-up can take 2 min)

/**
 * Shared fetch wrapper with:
 *  - Timeout handling (30s default)
 *  - Network error detection (backend not running)
 *  - HTTP status → user-friendly error messages
 *  - Never exposes raw stack traces or internal server details to UI
 */
async function fetchWithTimeout(url: string, options: RequestInit = {}, timeoutMs: number = TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    clearTimeout(timeoutId);
    return response;
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err.name === 'AbortError') {
      throw new Error('Request timed out. The server may be busy — please try again.');
    }
    // Network-level failure (server not running, no connection, etc.)
    throw new Error('Cannot connect to the LM-Screen server. Please ensure the backend is running on port 8000.');
  }
}

function httpStatusMessage(status: number): string {
  switch (status) {
    case 400: return 'Invalid request. Please check your input.';
    case 401: return 'Authentication required. Please log in again.';
    case 403: return 'You do not have permission to perform this action.';
    case 404: return 'The requested record was not found.';
    case 413: return 'File is too large. Maximum upload size is 10MB.';
    case 415: return 'Unsupported file type. Please upload a JPEG, PNG, or WebP image.';
    case 500: return 'An internal server error occurred. Please try again or contact support.';
    default: return `Server returned an unexpected error (HTTP ${status}).`;
  }
}


export async function uploadScanImage(file: File, productName?: string, gtin?: string): Promise<ScanResult> {
  const formData = new FormData();
  formData.append('file', file);
  if (productName) formData.append('product_name', productName);
  if (gtin) formData.append('gtin', gtin);

  const response = await fetchWithTimeout(`${API_BASE_URL}/scans`, {
    method: 'POST',
    body: formData,
  }, SCAN_TIMEOUT_MS);

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || httpStatusMessage(response.status));
  }

  return response.json();
}

export async function submitCitizenReport(payload: {
  gtin?: string;
  product_name?: string;
  issue_category: string;
  description?: string;
  location_city?: string;
  scan_id?: string;
}): Promise<{ report_id: string; status: string; message: string }> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/reports`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new Error(errData.detail || httpStatusMessage(response.status));
  }

  return response.json();
}

export async function getOfficerQueue(): Promise<PriorityQueueItem[]> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/officer/queue`);
  if (!response.ok) throw new Error(httpStatusMessage(response.status));
  return response.json();
}

export async function getScanResult(scanId: string): Promise<ScanResult> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/scans/${scanId}`);
  if (!response.ok) throw new Error(httpStatusMessage(response.status));
  return response.json();
}

export function generateNoticeUrl(scanId: string): string {
  return `${API_BASE_URL}/scans/${scanId}/notice`;
}

export async function getScanFindings(scanId: string): Promise<{ findings: any[] }> {
  const response = await fetch(`${API_BASE_URL}/scans/${scanId}/findings`);
  if (!response.ok) {
    throw new Error('Failed to fetch findings.');
  }
  return response.json();
}

export async function correctEvidence(scanId: string, evidenceId: string, correctedValue: string, reason: string, userRole: string = 'OFFICER') {
  const response = await fetch(`${API_BASE_URL}/scans/${scanId}/evidence/${evidenceId}/correct`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Role': userRole,
    },
    body: JSON.stringify({ corrected_value: correctedValue, reason }),
  });
  if (!response.ok) {
    const errData = await response.json().catch(() => ({}));
    throw new Error(errData.detail || 'Failed to submit correction.');
  }
  return response.json();
}

export async function submitOfficerReview(
  payloadOrClusterId: string | { scan_id?: string; cluster_id?: string; product_id?: string; decision: string; rationale: string },
  decisionOrUserRole?: string,
  rationaleArg?: string,
  roleHeader: string = 'OFFICER'
) {
  let bodyPayload: any;
  let activeRole = roleHeader;

  if (typeof payloadOrClusterId === 'string') {
    bodyPayload = {
      cluster_id: payloadOrClusterId,
      decision: decisionOrUserRole,
      rationale: rationaleArg
    };
  } else {
    bodyPayload = payloadOrClusterId;
    if (typeof decisionOrUserRole === 'string') {
      activeRole = decisionOrUserRole;
    }
  }

  const response = await fetch(`${API_BASE_URL}/officer/reviews`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Role': activeRole,
    },
    body: JSON.stringify(bodyPayload),
  });

  if (!response.ok) {
    if (response.status === 403) {
      throw new Error('Officer authorization required.');
    }
    const errData = await response.json().catch(() => ({}));
    throw new Error(errData.detail || 'Unable to save this review. Please try again.');
  }

  return response.json();
}

export async function getDashboardStats(): Promise<DashboardStats> {
  const response = await fetch(`${API_BASE_URL}/dashboard/statistics`);
  if (!response.ok) {
    throw new Error('Failed to fetch dashboard statistics.');
  }
  return response.json();
}

export async function getSystemHealth(): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/analytics/system/health`);
  if (!response.ok) {
    throw new Error('Failed to fetch system health.');
  }
  return response.json();
}

export async function getProductIntelligence(productId: string): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/products/${productId}/intelligence`);
  if (!response.ok) {
    throw new Error('Failed to fetch product intelligence.');
  }
  return response.json();
}

export async function getClusterIntelligence(clusterId: string): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/products/clusters/${clusterId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch cluster intelligence.');
  }
  return response.json();
}

export async function listProducts(): Promise<any[]> {
  const response = await fetch(`${API_BASE_URL}/products`);
  if (!response.ok) {
    throw new Error('Failed to fetch product list.');
  }
  return response.json();
}

export async function getAnalyticsOverview(days: number = 30): Promise<any> {
  const response = await fetch(`${API_BASE_URL}/analytics/overview?days=${days}`);
  if (!response.ok) throw new Error('Failed to fetch analytics overview.');
  return response.json();
}

export async function getAnalyticsTrends(days: number = 30): Promise<any[]> {
  const response = await fetch(`${API_BASE_URL}/analytics/trends?days=${days}`);
  if (!response.ok) throw new Error('Failed to fetch analytics trends.');
  return response.json();
}

export async function getAnalyticsCategories(days: number = 30): Promise<any[]> {
  const response = await fetch(`${API_BASE_URL}/analytics/categories?days=${days}`);
  if (!response.ok) throw new Error('Failed to fetch analytics categories.');
  return response.json();
}

export async function getAnalyticsRequirements(days: number = 30): Promise<any[]> {
  const response = await fetch(`${API_BASE_URL}/analytics/requirements?days=${days}`);
  if (!response.ok) throw new Error('Failed to fetch analytics requirements.');
  return response.json();
}

export async function getAnalyticsQuality(days: number = 30): Promise<any[]> {
  const response = await fetch(`${API_BASE_URL}/analytics/quality?days=${days}`);
  if (!response.ok) throw new Error('Failed to fetch analytics quality.');
  return response.json();
}

export async function getAnalyticsConsistency(days: number = 30): Promise<any[]> {
  const response = await fetch(`${API_BASE_URL}/analytics/consistency?days=${days}`);
  if (!response.ok) throw new Error('Failed to fetch analytics consistency.');
  return response.json();
}

export async function getAnalyticsPrioritization(days: number = 30): Promise<any[]> {
  const response = await fetch(`${API_BASE_URL}/analytics/prioritization?days=${days}`);
  if (!response.ok) throw new Error('Failed to fetch analytics prioritization.');
  return response.json();
}

// ────────────────────────────────────────────────────────────────────────────────
// CASE MANAGEMENT API
// ────────────────────────────────────────────────────────────────────────────────

export async function createCase(payload: {
  trigger_type: string;
  scan_id?: string;
  cluster_id?: string;
  product_id?: string;
  source_scan_ids?: string[];
  reason?: string;
  priority?: string;
  [key: string]: any;
}): Promise<any> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/cases`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-User-Role': 'OFFICER' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || httpStatusMessage(response.status));
  }
  return response.json();
}

export async function listCases(params?: {
  status?: string;
  priority?: string;
  trigger_type?: string;
  cluster_id?: string;
  search?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_dir?: string;
}): Promise<CaseListResponse> {
  const qs = new URLSearchParams();
  if (params?.status) qs.set('status', params.status);
  if (params?.priority) qs.set('priority', params.priority);
  if (params?.trigger_type) qs.set('trigger_type', params.trigger_type);
  if (params?.cluster_id) qs.set('cluster_id', params.cluster_id);
  if (params?.search) qs.set('search', params.search);
  if (params?.page) qs.set('page', String(params.page));
  if (params?.page_size) qs.set('page_size', String(params.page_size));
  if (params?.sort_by) qs.set('sort_by', params.sort_by);
  if (params?.sort_dir) qs.set('sort_dir', params.sort_dir);

  const response = await fetchWithTimeout(
    `${API_BASE_URL}/cases${qs.toString() ? '?' + qs.toString() : ''}`,
    { headers: { 'X-User-Role': 'OFFICER' } }
  );
  if (!response.ok) throw new Error(httpStatusMessage(response.status));
  return response.json();
}

export async function getCaseDetail(caseId: string): Promise<CaseDetail> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/cases/${caseId}`, {
    headers: { 'X-User-Role': 'OFFICER' },
  });
  if (!response.ok) throw new Error(httpStatusMessage(response.status));
  return response.json();
}

export async function transitionCaseStatus(caseId: string, status: string, reason?: string): Promise<any> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/cases/${caseId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', 'X-User-Role': 'OFFICER' },
    body: JSON.stringify({ status, reason }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || httpStatusMessage(response.status));
  }
  return response.json();
}

export async function addCaseNote(caseId: string, note: string): Promise<any> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/cases/${caseId}/notes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-User-Role': 'OFFICER' },
    body: JSON.stringify({ note }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || httpStatusMessage(response.status));
  }
  return response.json();
}

export async function recordCaseFinding(caseId: string, finding: string, notes: string): Promise<any> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/cases/${caseId}/finding`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-User-Role': 'OFFICER' },
    body: JSON.stringify({ finding, notes }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || httpStatusMessage(response.status));
  }
  return response.json();
}

export async function createCaseInspection(caseId: string, payload: {
  location_hint?: string;
  scheduled_at?: string;
  notes?: string;
}): Promise<any> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/cases/${caseId}/inspection`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-User-Role': 'OFFICER' },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || httpStatusMessage(response.status));
  }
  return response.json();
}

export async function closeCase(caseId: string, closure_outcome: string, reason: string): Promise<any> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/cases/${caseId}/close`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-User-Role': 'OFFICER' },
    body: JSON.stringify({ closure_outcome, reason }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || httpStatusMessage(response.status));
  }
  return response.json();
}

export async function reopenCase(caseId: string, reason: string): Promise<any> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/cases/${caseId}/reopen`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-User-Role': 'OFFICER' },
    body: JSON.stringify({ reason }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || httpStatusMessage(response.status));
  }
  return response.json();
}

export async function linkCaseEvidence(caseId: string, scan_id: string, reason?: string): Promise<any> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/cases/${caseId}/evidence`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-User-Role': 'OFFICER' },
    body: JSON.stringify({ scan_id, reason }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || httpStatusMessage(response.status));
  }
  return response.json();
}

export async function getCaseAuditTrail(caseId: string): Promise<any> {
  const response = await fetchWithTimeout(`${API_BASE_URL}/cases/${caseId}/audit`, {
    headers: { 'X-User-Role': 'OFFICER' },
  });
  if (!response.ok) throw new Error(httpStatusMessage(response.status));
  return response.json();
}
