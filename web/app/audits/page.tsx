"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Plus,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
  FileText,
  Files,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";
import { listAuditRequests, type AuditRequest } from "@/lib/api";

const statusConfig = {
  draft: { icon: FileText, color: "text-muted-foreground", label: "초안", animate: false },
  pending: { icon: Clock, color: "text-muted-foreground", label: "대기 중", animate: false },
  running: { icon: Loader2, color: "text-blue-500", label: "실행 중", animate: true },
  completed: { icon: CheckCircle2, color: "text-green-500", label: "완료", animate: false },
  failed: { icon: XCircle, color: "text-red-500", label: "실패", animate: false },
};

type StatusFilter = "all" | "draft" | "pending" | "running" | "completed" | "failed";

export default function AuditsPage() {
  const [audits, setAudits] = useState<AuditRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<StatusFilter>("all");

  useEffect(() => {
    async function loadAudits() {
      try {
        const params = filter !== "all" ? { status: filter } : undefined;
        const data = await listAuditRequests(params);
        setAudits(data.audit_requests);
      } catch (error) {
        console.error("Failed to load audits:", error);
      } finally {
        setLoading(false);
      }
    }
    loadAudits();
  }, [filter]);

  return (
    <div className="min-h-screen">
      <Header
        title="감사 목록"
        description="컴플라이언스 감사를 조회하고 관리합니다"
      />

      <div className="p-6 space-y-6">
        {/* Actions */}
        <div className="flex justify-between items-center">
          <div className="flex gap-2">
            <Button
              variant={filter === "all" ? "outline" : "ghost"}
              size="sm"
              onClick={() => setFilter("all")}
            >
              전체
            </Button>
            <Button
              variant={filter === "draft" ? "outline" : "ghost"}
              size="sm"
              onClick={() => setFilter("draft")}
            >
              초안
            </Button>
            <Button
              variant={filter === "running" ? "outline" : "ghost"}
              size="sm"
              onClick={() => setFilter("running")}
            >
              실행 중
            </Button>
            <Button
              variant={filter === "completed" ? "outline" : "ghost"}
              size="sm"
              onClick={() => setFilter("completed")}
            >
              완료
            </Button>
            <Button
              variant={filter === "failed" ? "outline" : "ghost"}
              size="sm"
              onClick={() => setFilter("failed")}
            >
              실패
            </Button>
          </div>
          <Link href="/audits/new">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              새 감사 신청
            </Button>
          </Link>
        </div>

        {/* Audit List */}
        {loading ? (
          <div className="flex items-center justify-center p-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-muted-foreground">불러오는 중...</span>
          </div>
        ) : audits.length === 0 ? (
          <Card>
            <CardContent className="p-12 text-center">
              <Clock className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium">감사 내역이 없습니다</h3>
              <p className="text-muted-foreground mt-2">
                새 감사를 신청하여 시작하세요.
              </p>
              <Link href="/audits/new">
                <Button className="mt-4">
                  <Plus className="h-4 w-4 mr-2" />
                  새 감사 신청
                </Button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-3">
            {audits.map((audit) => {
              const config = statusConfig[audit.status] || statusConfig.pending;
              const Icon = config.icon;
              const passCount = audit.total_passed ?? 0;
              const failCount = audit.total_failed ?? 0;
              const reviewCount = audit.total_review ?? 0;

              return (
                <Link key={audit.id} href={`/audits/${audit.id}`}>
                  <Card className="hover:border-primary/50 transition-colors cursor-pointer">
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <Icon
                            className={`h-5 w-5 ${config.color} ${
                              config.animate ? "animate-spin" : ""
                            }`}
                          />
                          <div>
                            <div className="flex items-center gap-2">
                              <p className="font-medium">{audit.name}</p>
                              {audit.files.length > 0 && (
                                <span className="text-xs text-muted-foreground flex items-center gap-1">
                                  <Files className="h-3 w-3" />
                                  {audit.files.length}개 파일
                                </span>
                              )}
                            </div>
                            <p className="text-sm text-muted-foreground">
                              {audit.compliance_ids.join(", ") || "규정 미선택"}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-4">
                          {audit.status === "completed" && (
                            <div className="flex gap-2">
                              <Badge variant="success">{passCount} 통과</Badge>
                              {failCount > 0 && (
                                <Badge variant="error">{failCount} 실패</Badge>
                              )}
                              {reviewCount > 0 && (
                                <Badge variant="warning">{reviewCount} 검토</Badge>
                              )}
                            </div>
                          )}
                          {audit.status === "draft" && (
                            <Badge variant="secondary">초안</Badge>
                          )}
                          {audit.status === "running" && (
                            <Badge variant="warning">실행 중</Badge>
                          )}
                          {audit.status === "failed" && (
                            <Badge variant="error">실패</Badge>
                          )}
                          <span className="text-sm text-muted-foreground">
                            {formatDate(audit.created_at)}
                          </span>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
