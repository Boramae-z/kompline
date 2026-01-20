"use client";

import { useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { Upload, FileCode, Play, X, File, Loader2 } from "lucide-react";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  createAuditRequest,
  uploadAuditFile,
  deleteAuditFile,
  submitAuditRequest,
  type AuditFile,
  type AuditRequest,
} from "@/lib/api";

const availableCompliances = [
  { id: "byeolji5-fairness", name: "알고리즘 공정성 자가평가", description: "금융상품 비교·추천 플랫폼 알고리즘 공정성 규정 (별지5)" },
  { id: "pipa-kr-2024", name: "개인정보보호법", description: "개인정보의 수집·이용·제공·관리 규정" },
];

type UploadStatus = "idle" | "uploading" | "success" | "error";

interface PendingFile {
  file: File;
  status: UploadStatus;
  error?: string;
}

export default function NewAuditPage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [selectedCompliances, setSelectedCompliances] = useState<string[]>(["byeolji5-fairness"]);
  const [useLLM, setUseLLM] = useState(true);
  const [requireReview, setRequireReview] = useState(true);

  // Audit request state
  const [auditRequest, setAuditRequest] = useState<AuditRequest | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<AuditFile[]>([]);
  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([]);

  // UI state
  const [step, setStep] = useState<"info" | "files" | "submit">("info");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);

  const toggleCompliance = (id: string) => {
    setSelectedCompliances((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    );
  };

  // Step 1: Create audit request
  const handleCreateRequest = async () => {
    if (!name.trim()) {
      setError("감사명을 입력해주세요");
      return;
    }
    if (selectedCompliances.length === 0) {
      setError("최소 하나의 규정을 선택해주세요");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const request = await createAuditRequest({
        name: name.trim(),
        description: description.trim() || undefined,
        compliance_ids: selectedCompliances,
        use_llm: useLLM,
        require_review: requireReview,
      });
      setAuditRequest(request);
      setStep("files");
    } catch (err) {
      setError(err instanceof Error ? err.message : "감사 요청 생성 실패");
    } finally {
      setLoading(false);
    }
  };

  // Step 2: Upload files
  const handleFileSelect = useCallback(async (files: FileList | null) => {
    if (!files || !auditRequest) return;

    const fileArray = Array.from(files);
    const newPending: PendingFile[] = fileArray.map((file) => ({
      file,
      status: "uploading" as UploadStatus,
    }));

    setPendingFiles((prev) => [...prev, ...newPending]);

    for (let i = 0; i < fileArray.length; i++) {
      const file = fileArray[i];
      try {
        const uploaded = await uploadAuditFile(auditRequest.id, file);
        setUploadedFiles((prev) => [...prev, uploaded]);
        setPendingFiles((prev) =>
          prev.map((p) =>
            p.file === file ? { ...p, status: "success" } : p
          )
        );
      } catch (err) {
        setPendingFiles((prev) =>
          prev.map((p) =>
            p.file === file
              ? { ...p, status: "error", error: err instanceof Error ? err.message : "업로드 실패" }
              : p
          )
        );
      }
    }

    // Clear successful uploads from pending after a delay
    setTimeout(() => {
      setPendingFiles((prev) => prev.filter((p) => p.status === "error"));
    }, 1000);
  }, [auditRequest]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleRemoveFile = async (fileId: string) => {
    if (!auditRequest) return;
    try {
      await deleteAuditFile(auditRequest.id, fileId);
      setUploadedFiles((prev) => prev.filter((f) => f.id !== fileId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "파일 삭제 실패");
    }
  };

  // Step 3: Submit audit
  const handleSubmit = async () => {
    if (!auditRequest) return;
    if (uploadedFiles.length === 0) {
      setError("최소 하나의 파일을 업로드해주세요");
      return;
    }

    setLoading(true);
    setError(null);
    setStep("submit");

    try {
      const result = await submitAuditRequest(auditRequest.id);
      // Store result in sessionStorage for the detail page
      sessionStorage.setItem("lastAuditRequest", JSON.stringify(result));
      router.push(`/audits/${auditRequest.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "감사 실행 실패");
      setStep("files");
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

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

  return (
    <div className="min-h-screen">
      <Header
        title="새 감사 신청"
        description="컴플라이언스 감사를 신청합니다"
      />

      <div className="p-6 space-y-6">
        {/* Progress Steps */}
        <div className="flex items-center justify-center gap-4 mb-8">
          <div className={`flex items-center gap-2 ${step === "info" ? "text-primary" : "text-muted-foreground"}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
              step === "info" ? "bg-primary text-primary-foreground" : "bg-primary/20 text-primary"
            }`}>1</div>
            <span className="text-sm font-medium">기본 정보</span>
          </div>
          <div className="w-12 h-px bg-border" />
          <div className={`flex items-center gap-2 ${step === "files" ? "text-primary" : "text-muted-foreground"}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
              step === "files" ? "bg-primary text-primary-foreground" :
              step === "submit" ? "bg-primary/20 text-primary" : "bg-muted"
            }`}>2</div>
            <span className="text-sm font-medium">파일 업로드</span>
          </div>
          <div className="w-12 h-px bg-border" />
          <div className={`flex items-center gap-2 ${step === "submit" ? "text-primary" : "text-muted-foreground"}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
              step === "submit" ? "bg-primary text-primary-foreground" : "bg-muted"
            }`}>3</div>
            <span className="text-sm font-medium">감사 실행</span>
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="rounded-lg bg-destructive/10 p-4 text-sm text-destructive">
            {error}
          </div>
        )}

        {/* Step 1: Basic Info */}
        {step === "info" && (
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2 space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>감사 정보</CardTitle>
                  <CardDescription>
                    감사의 기본 정보를 입력해주세요
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      감사명 <span className="text-destructive">*</span>
                    </label>
                    <input
                      type="text"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="예: 2024년 1분기 알고리즘 감사"
                      className="w-full px-3 py-2 rounded-lg border bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      설명 (선택)
                    </label>
                    <textarea
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      placeholder="감사 목적이나 범위에 대한 설명을 입력하세요..."
                      className="w-full h-24 px-3 py-2 rounded-lg border bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring"
                    />
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>규정 선택</CardTitle>
                  <CardDescription>
                    적용할 규정을 선택해주세요
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  {availableCompliances.map((compliance) => (
                    <label
                      key={compliance.id}
                      className={`flex items-start gap-3 rounded-lg border p-3 cursor-pointer transition-colors ${
                        selectedCompliances.includes(compliance.id)
                          ? "border-primary bg-primary/5"
                          : "hover:border-primary/50"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={selectedCompliances.includes(compliance.id)}
                        onChange={() => toggleCompliance(compliance.id)}
                        className="mt-1"
                      />
                      <div>
                        <p className="font-medium text-sm">{compliance.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {compliance.description}
                        </p>
                      </div>
                    </label>
                  ))}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>옵션</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <label className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={useLLM}
                      onChange={(e) => setUseLLM(e.target.checked)}
                    />
                    <div>
                      <p className="text-sm font-medium">LLM 평가 사용</p>
                      <p className="text-xs text-muted-foreground">
                        더 정확하지만 처리 시간이 길어집니다
                      </p>
                    </div>
                  </label>

                  <label className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      checked={requireReview}
                      onChange={(e) => setRequireReview(e.target.checked)}
                    />
                    <div>
                      <p className="text-sm font-medium">검토 요청 활성화</p>
                      <p className="text-xs text-muted-foreground">
                        불확실한 결과에 대해 사람의 검토를 요청합니다
                      </p>
                    </div>
                  </label>
                </CardContent>
              </Card>

              <Button
                className="w-full"
                size="lg"
                onClick={handleCreateRequest}
                disabled={loading || !name.trim() || selectedCompliances.length === 0}
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    생성 중...
                  </>
                ) : (
                  "다음: 파일 업로드"
                )}
              </Button>
            </div>
          </div>
        )}

        {/* Step 2: File Upload */}
        {step === "files" && auditRequest && (
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2 space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>파일 업로드</CardTitle>
                  <CardDescription>
                    감사할 코드 파일을 업로드해주세요 (Python, YAML, JSON 등)
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Drop Zone */}
                  <div
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    onDragLeave={handleDragLeave}
                    onClick={() => fileInputRef.current?.click()}
                    className={`flex flex-col items-center justify-center gap-4 rounded-lg border-2 border-dashed p-12 cursor-pointer transition-colors ${
                      isDragging
                        ? "border-primary bg-primary/5"
                        : "hover:border-primary/50"
                    }`}
                  >
                    <Upload className={`h-10 w-10 ${isDragging ? "text-primary" : "text-muted-foreground"}`} />
                    <div className="text-center">
                      <p className="font-medium">
                        {isDragging ? "여기에 놓으세요" : "파일을 드래그하거나 클릭하여 선택"}
                      </p>
                      <p className="text-sm text-muted-foreground mt-1">
                        .py, .yaml, .yml, .json, .pdf 파일 지원
                      </p>
                    </div>
                    <input
                      ref={fileInputRef}
                      type="file"
                      multiple
                      accept=".py,.yaml,.yml,.json,.pdf,.txt"
                      onChange={(e) => handleFileSelect(e.target.files)}
                      className="hidden"
                    />
                  </div>

                  {/* Pending Files (uploading) */}
                  {pendingFiles.length > 0 && (
                    <div className="space-y-2">
                      {pendingFiles.map((pf, idx) => (
                        <div
                          key={idx}
                          className="flex items-center gap-3 rounded-lg border p-3 bg-muted/50"
                        >
                          {pf.status === "uploading" && (
                            <Loader2 className="h-4 w-4 animate-spin text-primary" />
                          )}
                          {pf.status === "error" && (
                            <X className="h-4 w-4 text-destructive" />
                          )}
                          <span className="flex-1 text-sm truncate">{pf.file.name}</span>
                          {pf.error && (
                            <span className="text-xs text-destructive">{pf.error}</span>
                          )}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Uploaded Files */}
                  {uploadedFiles.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-sm font-medium text-muted-foreground">
                        업로드된 파일 ({uploadedFiles.length})
                      </p>
                      {uploadedFiles.map((file) => (
                        <div
                          key={file.id}
                          className="flex items-center gap-3 rounded-lg border p-3"
                        >
                          {getFileIcon(file.file_type)}
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{file.filename}</p>
                            <p className="text-xs text-muted-foreground">
                              {formatFileSize(file.size)} · {file.file_type}
                            </p>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleRemoveFile(file.id)}
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>감사 요약</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
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
                        <Badge key={id} variant="secondary" className="text-xs">
                          {availableCompliances.find((c) => c.id === id)?.name || id}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">업로드된 파일</p>
                    <p className="font-medium">{uploadedFiles.length}개</p>
                  </div>
                </CardContent>
              </Card>

              <Button
                className="w-full"
                size="lg"
                onClick={handleSubmit}
                disabled={loading || uploadedFiles.length === 0}
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    감사 실행 중...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    감사 시작
                  </>
                )}
              </Button>

              <Button
                variant="outline"
                className="w-full"
                onClick={() => {
                  setStep("info");
                  setAuditRequest(null);
                  setUploadedFiles([]);
                }}
                disabled={loading}
              >
                이전 단계로
              </Button>
            </div>
          </div>
        )}

        {/* Step 3: Submitting */}
        {step === "submit" && (
          <div className="flex flex-col items-center justify-center py-20">
            <Loader2 className="h-12 w-12 animate-spin text-primary mb-4" />
            <h2 className="text-xl font-semibold mb-2">감사 실행 중...</h2>
            <p className="text-muted-foreground">
              {uploadedFiles.length}개 파일을 분석하고 있습니다
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
