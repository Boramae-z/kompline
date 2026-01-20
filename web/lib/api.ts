const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8888";

export interface Audit {
  id: string;
  status: "pending" | "running" | "completed" | "failed";
  compliance_ids: string[];
  artifact_ids: string[];
  created_at: string;
  completed_at?: string;
  result?: AuditResult;
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
}

export interface LogEvent {
  timestamp: string;
  agent: string;
  event_type: string;
  message: string;
  metadata?: Record<string, unknown>;
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
  result?: AuditResult;
  report?: Record<string, unknown>;
  report_markdown?: string;
  pending_reviews: Finding[];
  trace: LogEvent[];
  error?: string;
}

// API Client
export async function analyzeCode(request: AnalyzeRequest): Promise<AnalyzeResponse> {
  const response = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail?.error || "Analysis failed");
  }

  return response.json();
}

export async function getTrace(): Promise<LogEvent[]> {
  const response = await fetch(`${API_BASE}/trace`);
  if (!response.ok) throw new Error("Failed to fetch trace");
  const data = await response.json();
  return data.events || [];
}

export async function getPendingReviews(): Promise<Finding[]> {
  const response = await fetch(`${API_BASE}/reviews`);
  if (!response.ok) throw new Error("Failed to fetch reviews");
  const data = await response.json();
  return data.pending || [];
}

export async function getCompliances(): Promise<string[]> {
  // TODO: Implement when backend endpoint is ready
  return ["byeolji5-fairness", "pipa-kr-2024"];
}

export async function healthCheck(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/`);
    return response.ok;
  } catch {
    return false;
  }
}
