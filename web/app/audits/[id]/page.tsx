"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Download,
  FileCode,
  File,
  Clock,
  Loader2,
} from "lucide-react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PipelineView } from "@/components/pipeline/pipeline-view";
import { FindingCard } from "@/components/findings/finding-card";
import { LogStream } from "@/components/logs/log-stream";
import {
  getAuditRequest,
  type AuditRequest,
  type Finding,
  type AuditResult,
} from "@/lib/api";

export default function AuditDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  const [auditRequest, setAuditRequest] = useState<AuditRequest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"overview" | "files" | "findings" | "logs">("overview");
  const [selectedFileId, setSelectedFileId] = useState<string | null>(null);

  useEffect(() => {
    // First check sessionStorage for fresh result
    const stored = sessionStorage.getItem("lastAuditRequest");
    if (stored) {
      const parsed = JSON.parse(stored);
      if (parsed.id === id) {
        setAuditRequest(parsed);
        setLoading(false);
        sessionStorage.removeItem("lastAuditRequest");
        return;
      }
    }

    // Otherwise fetch from API
    async function fetchAudit() {
      try {
        const data = await getAuditRequest(id);
        setAuditRequest(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "감사 요청을 불러올 수 없습니다");
      } finally {
        setLoading(false);
      }
    }
    fetchAudit();
  }, [id]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (error || !auditRequest) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <XCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
          <h2 className="text-xl font-semibold mb-2">오류</h2>
          <p className="text-muted-foreground mb-4">{error || "감사를 찾을 수 없습니다"}</p>
          <Link href="/audits">
            <Button>감사 목록으로</Button>
          </Link>
        </div>
      </div>
    );
  }

  const isCompliant = auditRequest.is_compliant ?? false;
  const fileResults = auditRequest.result?.file_results ?? [];

  // Get all findings across all files
  const allFindings: (Finding & { filename: string })[] = [];
  for (const fr of fileResults) {
    for (const rel of fr.result?.relations ?? []) {
      for (const finding of rel.findings ?? []) {
        allFindings.push({ ...finding, filename: fr.filename });
      }
    }
  }

  const getFileIcon = (fileType: string) => {
    switch (fileType) {
      case "python":
        return <FileCode className="h-4 w-4 text-yellow-500" />;
      case "pdf":
        return <File className="h-4 w-4 text-red-500" />;
      case "yaml":
      case "json":
        return <File className="h-4 w-4 text-blue-500" />;
      default:
        return <File className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "completed":
        return <Badge variant="success">완료</Badge>;
      case "running":
        return <Badge variant="warning">실행 중</Badge>;
      case "failed":
        return <Badge variant="error">실패</Badge>;
      case "draft":
        return <Badge variant="secondary">초안</Badge>;
      default:
        return <Badge variant="secondary">{status}</Badge>;
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="min-h-screen">
      <Header
        title={auditRequest.name}
        description={auditRequest.description || "감사 결과"}
      />

      <div className="p-6 space-y-6">
        {/* Back button and status */}
        <div className="flex items-center justify-between">
          <Link href="/audits">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              감사 목록
            </Button>
          </Link>

          <div className="flex items-center gap-3">
            {getStatusBadge(auditRequest.status)}
            {auditRequest.status === "completed" && (
              isCompliant ? (
                <Badge variant="success" className="text-sm py-1 px-3">
                  <CheckCircle2 className="h-4 w-4 mr-1" />
                  준수
                </Badge>
              ) : (
                <Badge variant="error" className="text-sm py-1 px-3">
                  <XCircle className="h-4 w-4 mr-1" />
                  미준수
                </Badge>
              )
            )}
            <Button variant="outline" size="sm">
              <Download className="h-4 w-4 mr-2" />
              보고서 내보내기
            </Button>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid gap-4 md:grid-cols-5">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <File className="h-8 w-8 text-blue-500" />
                <div>
                  <p className="text-2xl font-bold">{auditRequest.files.length}</p>
                  <p className="text-sm text-muted-foreground">파일</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="h-8 w-8 text-green-500" />
                <div>
                  <p className="text-2xl font-bold">{auditRequest.total_passed}</p>
                  <p className="text-sm text-muted-foreground">통과</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <XCircle className="h-8 w-8 text-red-500" />
                <div>
                  <p className="text-2xl font-bold">{auditRequest.total_failed}</p>
                  <p className="text-sm text-muted-foreground">실패</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-8 w-8 text-yellow-500" />
                <div>
                  <p className="text-2xl font-bold">{auditRequest.total_review}</p>
                  <p className="text-sm text-muted-foreground">검토 필요</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <Clock className="h-8 w-8 text-gray-500" />
                <div>
                  <p className="text-xs text-muted-foreground">생성</p>
                  <p className="text-sm font-medium">{formatDate(auditRequest.created_at)}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 border-b">
          <button
            onClick={() => setActiveTab("overview")}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === "overview"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            개요
          </button>
          <button
            onClick={() => setActiveTab("files")}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === "files"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            파일별 결과 ({fileResults.length})
          </button>
          <button
            onClick={() => setActiveTab("findings")}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === "findings"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            전체 검사 결과 ({allFindings.length})
          </button>
          <button
            onClick={() => setActiveTab("logs")}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === "logs"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            로그
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === "overview" && (
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>감사 정보</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-xs text-muted-foreground">감사명</p>
                  <p className="font-medium">{auditRequest.name}</p>
                </div>
                {auditRequest.description && (
                  <div>
                    <p className="text-xs text-muted-foreground">설명</p>
                    <p className="text-sm">{auditRequest.description}</p>
                  </div>
                )}
                <div>
                  <p className="text-xs text-muted-foreground">적용 규정</p>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {auditRequest.compliance_ids.map((id) => (
                      <Badge key={id} variant="secondary">
                        {id}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-xs text-muted-foreground">생성 일시</p>
                    <p className="text-sm">{formatDate(auditRequest.created_at)}</p>
                  </div>
                  {auditRequest.submitted_at && (
                    <div>
                      <p className="text-xs text-muted-foreground">제출 일시</p>
                      <p className="text-sm">{formatDate(auditRequest.submitted_at)}</p>
                    </div>
                  )}
                  {auditRequest.completed_at && (
                    <div>
                      <p className="text-xs text-muted-foreground">완료 일시</p>
                      <p className="text-sm">{formatDate(auditRequest.completed_at)}</p>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>업로드된 파일</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {auditRequest.files.map((file) => (
                    <div
                      key={file.id}
                      className="flex items-center gap-3 rounded-lg border p-3"
                    >
                      {getFileIcon(file.file_type)}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{file.filename}</p>
                        <p className="text-xs text-muted-foreground">
                          {file.file_type} · {(file.size / 1024).toFixed(1)} KB
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {auditRequest.status === "completed" && (
              <Card className="lg:col-span-2">
                <CardHeader>
                  <CardTitle>파이프라인</CardTitle>
                </CardHeader>
                <CardContent>
                  <PipelineView
                    auditStatus={auditRequest.status}
                    result={
                      fileResults.length > 0
                        ? {
                            is_compliant: isCompliant,
                            total_passed: auditRequest.total_passed,
                            total_failed: auditRequest.total_failed,
                            total_review: auditRequest.total_review,
                            relations: fileResults.flatMap((fr) => fr.result?.relations ?? []),
                          }
                        : undefined
                    }
                    trace={auditRequest.trace ?? []}
                  />
                </CardContent>
              </Card>
            )}
          </div>
        )}

        {activeTab === "files" && (
          <div className="space-y-4">
            {fileResults.length === 0 ? (
              <p className="text-muted-foreground">아직 분석 결과가 없습니다.</p>
            ) : (
              <div className="grid gap-4">
                {fileResults.map((fr) => {
                  const fileFindings = fr.result?.relations?.flatMap((r) => r.findings) ?? [];
                  const passed = fr.result?.total_passed ?? 0;
                  const failed = fr.result?.total_failed ?? 0;
                  const review = fr.result?.total_review ?? 0;

                  return (
                    <Card key={fr.file_id}>
                      <CardHeader className="cursor-pointer" onClick={() => setSelectedFileId(selectedFileId === fr.file_id ? null : fr.file_id)}>
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <FileCode className="h-5 w-5 text-yellow-500" />
                            <CardTitle className="text-base">{fr.filename}</CardTitle>
                          </div>
                          <div className="flex items-center gap-2">
                            {passed > 0 && (
                              <Badge variant="success">{passed} 통과</Badge>
                            )}
                            {failed > 0 && (
                              <Badge variant="error">{failed} 실패</Badge>
                            )}
                            {review > 0 && (
                              <Badge variant="warning">{review} 검토</Badge>
                            )}
                          </div>
                        </div>
                      </CardHeader>
                      {selectedFileId === fr.file_id && (
                        <CardContent>
                          {fileFindings.length === 0 ? (
                            <p className="text-sm text-muted-foreground">검사 결과가 없습니다.</p>
                          ) : (
                            <div className="grid gap-4 md:grid-cols-2">
                              {fileFindings.map((finding) => (
                                <FindingCard
                                  key={finding.id}
                                  finding={finding}
                                  showActions={finding.requires_human_review}
                                />
                              ))}
                            </div>
                          )}
                        </CardContent>
                      )}
                    </Card>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {activeTab === "findings" && (
          <div className="space-y-4">
            {allFindings.length === 0 ? (
              <p className="text-muted-foreground">검사 결과가 없습니다.</p>
            ) : (
              <div className="grid gap-4 md:grid-cols-2">
                {allFindings.map((finding, idx) => (
                  <div key={finding.id || idx}>
                    <p className="text-xs text-muted-foreground mb-2">{finding.filename}</p>
                    <FindingCard
                      finding={finding}
                      showActions={finding.requires_human_review}
                    />
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === "logs" && (
          <Card>
            <CardHeader>
              <CardTitle>에이전트 활동 로그</CardTitle>
            </CardHeader>
            <CardContent>
              {auditRequest.trace && auditRequest.trace.length > 0 ? (
                <LogStream events={auditRequest.trace} maxHeight="600px" />
              ) : (
                <p className="text-muted-foreground">로그가 없습니다.</p>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
