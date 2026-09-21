import type { ScanResult, PriorityQueueItem, DashboardStats } from './types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export async function uploadScanImage(file: File, productName?: string, gtin?: string): Promise<ScanResult> {
  const formData = new FormData();
  formData.append('file', file);
  if (productName) formData.append('product_name', productName);
  if (gtin) formData.append('gtin', gtin);

  const response = await fetch(`${API_BASE_URL}/scans`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Scan processing failed.');
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
  const response = await fetch(`${API_BASE_URL}/reports`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    throw new Error('Signal submission failed.');
  }

  return response.json();
}

export async function getOfficerQueue(): Promise<PriorityQueueItem[]> {
  const response = await fetch(`${API_BASE_URL}/officer/queue`);
  if (!response.ok) {
    throw new Error('Failed to fetch officer queue.');
  }
  return response.json();
}

export async function getScanResult(scanId: string): Promise<ScanResult> {
  const response = await fetch(`${API_BASE_URL}/scans/${scanId}`);
  if (!response.ok) {
    throw new Error('Failed to fetch scan details.');
  }
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

