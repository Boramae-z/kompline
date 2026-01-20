const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8888";

// ============ Types ============

export interface Audit {
  id: string;
  name: string;
  status: "pending" | "running" | "completed" | "failed";
  compliance_ids: string[];
  created_at: string;
  completed_at?: string;
  is_compliant?: boolean;
  total_passed?: number;
  total_failed?: number;
  total_review?: number;
  result?: AuditResult;
  report_markdown?: string;
  trace?: LogEvent[];
}

export interface AuditResult {
  is_compliant: boolean;
  total_passed: number;
  total_failed: number;
  total_review: number;
  relations: AuditRelation[];
}

export interface AuditRelation {
  id: string;
  compliance_id: string;
  artifact_id: string;
  status: string;
  findings: Finding[];
}

export interface Finding {
  id: string;
  rule_id: string;
  status: "pass" | "fail" | "review" | "not_applicable";
  confidence: number;
  reasoning: string;
  recommendation?: string;
  evidence_refs: string[];
  requires_human_review: boolean;
  review_status?: "pending" | "approved" | "rejected";
  audit_id?: string;
}

export interface LogEvent {
  timestamp: string;
  agent: string;
  event_type: string;
  message: string;
  metadata?: Record<string, unknown>;
}

export interface Compliance {
  id: string;
  name: string;
  description: string;
  jurisdiction: string;
  category: string;
}

export interface Report {
  id: string;
  audit_id: string;
  name: string;
  compliance_ids: string[];
  created_at: string;
  is_compliant: boolean;
  format: string;
  content_markdown?: string;
}

export interface AnalyzeRequest {
  source_code?: string;
  artifact_path?: string;
  compliance_ids?: string[];
  use_llm?: boolean;
  require_review?: boolean;
}

export interface AnalyzeResponse {
  success: boolean;
  audit_id?: string;
  result?: AuditResult;
  report?: Record<string, unknown>;
  report_markdown?: string;
  pending_reviews: Finding[];
  trace: LogEvent[];
  error?: string;
}

// ============ API Client ============

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || error.error || `API error: ${response.status}`);
  }

  return response.json();
}

// ============ Audits ============

export async function listAudits(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<{ audits: Audit[]; total: number }> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));

  const query = searchParams.toString();
  return fetchApi(`/api/audits${query ? `?${query}` : ""}`);
}

export async function createAudit(request: AnalyzeRequest): Promise<AnalyzeResponse> {
  return fetchApi("/api/audits", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export async function getAudit(auditId: string): Promise<Audit> {
  return fetchApi(`/api/audits/${auditId}`);
}

export async function getAuditLogs(
  auditId: string,
  params?: { offset?: number; limit?: number }
): Promise<{ logs: LogEvent[]; total: number; has_more: boolean }> {
  const searchParams = new URLSearchParams();
  if (params?.offset) searchParams.set("offset", String(params.offset));
  if (params?.limit) searchParams.set("limit", String(params.limit));

  const query = searchParams.toString();
  return fetchApi(`/api/audits/${auditId}/logs${query ? `?${query}` : ""}`);
}

export async function deleteAudit(auditId: string): Promise<void> {
  await fetchApi(`/api/audits/${auditId}`, { method: "DELETE" });
}

// ============ Reviews ============

export async function listReviews(status?: string): Promise<{ pending: Finding[]; total: number }> {
  const query = status ? `?status=${status}` : "";
  return fetchApi(`/api/reviews${query}`);
}

export async function getReview(reviewId: string): Promise<Finding> {
  return fetchApi(`/api/reviews/${reviewId}`);
}

export async function approveReview(reviewId: string, comment?: string): Promise<Finding> {
  const result = await fetchApi<{ status: string; review: Finding }>(
    `/api/reviews/${reviewId}/approve`,
    {
      method: "POST",
      body: JSON.stringify({ comment }),
    }
  );
  return result.review;
}

export async function rejectReview(reviewId: string, comment?: string): Promise<Finding> {
  const result = await fetchApi<{ status: string; review: Finding }>(
    `/api/reviews/${reviewId}/reject`,
    {
      method: "POST",
      body: JSON.stringify({ comment }),
    }
  );
  return result.review;
}

export async function addReviewComment(reviewId: string, comment: string): Promise<Finding> {
  const result = await fetchApi<{ status: string; review: Finding }>(
    `/api/reviews/${reviewId}/comment`,
    {
      method: "POST",
      body: JSON.stringify({ comment }),
    }
  );
  return result.review;
}

// ============ Compliances ============

export async function listCompliances(): Promise<Compliance[]> {
  const result = await fetchApi<{ compliances: Compliance[] }>("/api/compliances");
  return result.compliances;
}

// ============ Reports ============

export async function listReports(): Promise<Report[]> {
  const result = await fetchApi<{ reports: Report[] }>("/api/reports");
  return result.reports;
}

export async function getReport(reportId: string): Promise<Report> {
  return fetchApi(`/api/reports/${reportId}`);
}

export async function exportReport(
  reportId: string,
  format: "markdown" | "json" = "markdown"
): Promise<{ format: string; content: string; filename: string }> {
  return fetchApi(`/api/reports/${reportId}/export?format=${format}`);
}

// ============ Legacy / Utility ============

export async function analyzeCode(request: AnalyzeRequest): Promise<AnalyzeResponse> {
  return createAudit(request);
}

export async function getTrace(): Promise<LogEvent[]> {
  const result = await fetchApi<{ events: LogEvent[] }>("/trace");
  return result.events;
}

export async function getPendingReviews(): Promise<Finding[]> {
  const result = await listReviews();
  return result.pending;
}

export async function getCompliances(): Promise<string[]> {
  const compliances = await listCompliances();
  return compliances.map((c) => c.id);
}

export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/`);
    return response.ok;
  } catch {
    return false;
  }
}

// ============ Audit Requests (Multi-file) ============

export interface AuditFile {
  id: string;
  filename: string;
  file_type: string;
  size: number;
  uploaded_at: string;
}

export interface AuditRequest {
  id: string;
  name: string;
  description?: string;
  status: "draft" | "pending" | "running" | "completed" | "failed";
  compliance_ids: string[];
  files: AuditFile[];
  created_at: string;
  submitted_at?: string;
  completed_at?: string;
  result?: {
    file_results: Array<{
      file_id: string;
      filename: string;
      result: AuditResult;
    }>;
    total_passed: number;
    total_failed: number;
    total_review: number;
  };
  is_compliant?: boolean;
  total_passed: number;
  total_failed: number;
  total_review: number;
  trace?: LogEvent[];
  error?: string;
}

export interface CreateAuditRequestInput {
  name: string;
  description?: string;
  compliance_ids: string[];
  use_llm?: boolean;
  require_review?: boolean;
}

export async function listAuditRequests(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<{ audit_requests: AuditRequest[]; total: number }> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));

  const query = searchParams.toString();
  return fetchApi(`/api/audit-requests${query ? `?${query}` : ""}`);
}

export async function createAuditRequest(
  input: CreateAuditRequestInput
): Promise<AuditRequest> {
  return fetchApi("/api/audit-requests", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function getAuditRequest(requestId: string): Promise<AuditRequest> {
  return fetchApi(`/api/audit-requests/${requestId}`);
}

export async function uploadAuditFile(
  requestId: string,
  file: File
): Promise<AuditFile> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/api/audit-requests/${requestId}/files`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || error.error || `Upload failed: ${response.status}`);
  }

  return response.json();
}

export async function deleteAuditFile(
  requestId: string,
  fileId: string
): Promise<void> {
  await fetchApi(`/api/audit-requests/${requestId}/files/${fileId}`, {
    method: "DELETE",
  });
}

export async function submitAuditRequest(requestId: string): Promise<AuditRequest> {
  return fetchApi(`/api/audit-requests/${requestId}/submit`, {
    method: "POST",
  });
}

export async function deleteAuditRequest(requestId: string): Promise<void> {
  await fetchApi(`/api/audit-requests/${requestId}`, { method: "DELETE" });
}
