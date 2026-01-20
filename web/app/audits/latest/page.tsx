"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Download,
  RefreshCw,
} from "lucide-react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PipelineView } from "@/components/pipeline/pipeline-view";
import { FindingCard } from "@/components/findings/finding-card";
import { LogStream } from "@/components/logs/log-stream";
import type { AnalyzeResponse, AuditResult, LogEvent, Finding } from "@/lib/api";

export default function LatestAuditPage() {
  const router = useRouter();
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [activeTab, setActiveTab] = useState<"pipeline" | "findings" | "report">("pipeline");

  useEffect(() => {
    const stored = sessionStorage.getItem("lastAuditResult");
    if (stored) {
      setResult(JSON.parse(stored));
    } else {
      router.push("/audits/new");
    }
  }, [router]);

  if (!result) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  const auditResult = result.result;
  const isCompliant = auditResult?.is_compliant ?? false;
  const allFindings: Finding[] = auditResult?.relations?.flatMap((r) => r.findings) ?? [];

  return (
    <div className="min-h-screen">
      <Header
        title="Audit Results"
        description="Analysis completed"
      />

      <div className="p-6 space-y-6">
        {/* Back button and status */}
        <div className="flex items-center justify-between">
          <Link href="/audits">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back to Audits
            </Button>
          </Link>

          <div className="flex items-center gap-3">
            {isCompliant ? (
              <Badge variant="success" className="text-sm py-1 px-3">
                <CheckCircle2 className="h-4 w-4 mr-1" />
                COMPLIANT
              </Badge>
            ) : (
              <Badge variant="error" className="text-sm py-1 px-3">
                <XCircle className="h-4 w-4 mr-1" />
                NON-COMPLIANT
              </Badge>
            )}
            <Button variant="outline" size="sm">
              <Download className="h-4 w-4 mr-2" />
              Export Report
            </Button>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <CheckCircle2 className="h-8 w-8 text-green-500" />
                <div>
                  <p className="text-2xl font-bold">{auditResult?.total_passed ?? 0}</p>
                  <p className="text-sm text-muted-foreground">Passed</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <XCircle className="h-8 w-8 text-red-500" />
                <div>
                  <p className="text-2xl font-bold">{auditResult?.total_failed ?? 0}</p>
                  <p className="text-sm text-muted-foreground">Failed</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-8 w-8 text-yellow-500" />
                <div>
                  <p className="text-2xl font-bold">{auditResult?.total_review ?? 0}</p>
                  <p className="text-sm text-muted-foreground">Need Review</p>
                </div>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <RefreshCw className="h-8 w-8 text-blue-500" />
                <div>
                  <p className="text-2xl font-bold">{auditResult?.relations?.length ?? 0}</p>
                  <p className="text-sm text-muted-foreground">Relations</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 border-b">
          <button
            onClick={() => setActiveTab("pipeline")}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === "pipeline"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Pipeline
          </button>
          <button
            onClick={() => setActiveTab("findings")}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === "findings"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Findings ({allFindings.length})
          </button>
          <button
            onClick={() => setActiveTab("report")}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === "report"
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            Report
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === "pipeline" && (
          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Pipeline Progress</CardTitle>
              </CardHeader>
              <CardContent>
                <PipelineView
                  auditStatus="completed"
                  result={auditResult ?? undefined}
                  trace={result.trace}
                />
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Agent Activity Log</CardTitle>
              </CardHeader>
              <CardContent>
                <LogStream events={result.trace} maxHeight="500px" />
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "findings" && (
          <div className="space-y-4">
            {auditResult?.relations?.map((relation) => (
              <div key={relation.id}>
                <h3 className="text-lg font-medium mb-3">
                  {relation.compliance_id} × {relation.artifact_id}
                </h3>
                <div className="grid gap-4 md:grid-cols-2">
                  {relation.findings.map((finding) => (
                    <FindingCard
                      key={finding.id}
                      finding={finding}
                      showActions={finding.requires_human_review}
                    />
                  ))}
                </div>
              </div>
            ))}
            {(!auditResult?.relations || auditResult.relations.length === 0) && (
              <p className="text-muted-foreground">No findings available.</p>
            )}
          </div>
        )}

        {activeTab === "report" && (
          <Card>
            <CardHeader>
              <CardTitle>Generated Report</CardTitle>
            </CardHeader>
            <CardContent>
              {result.report_markdown ? (
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <pre className="whitespace-pre-wrap font-sans text-sm">
                    {result.report_markdown}
                  </pre>
                </div>
              ) : (
                <p className="text-muted-foreground">No report generated.</p>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
