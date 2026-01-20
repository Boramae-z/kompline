"use client";

import Link from "next/link";
import {
  Plus,
  CheckCircle2,
  XCircle,
  Clock,
  Loader2,
} from "lucide-react";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";

// Mock data for demo
const mockAudits = [
  {
    id: "audit-001",
    name: "deposit_ranking.py",
    compliance: "byeolji5-fairness",
    status: "completed" as const,
    result: "pass",
    createdAt: new Date().toISOString(),
    findings: { pass: 4, fail: 0, review: 0 },
  },
  {
    id: "audit-002",
    name: "loan_scoring.py",
    compliance: "byeolji5-fairness",
    status: "completed" as const,
    result: "fail",
    createdAt: new Date(Date.now() - 86400000).toISOString(),
    findings: { pass: 2, fail: 1, review: 1 },
  },
  {
    id: "audit-003",
    name: "user_recommendation.py",
    compliance: "pipa-kr-2024",
    status: "running" as const,
    result: null,
    createdAt: new Date(Date.now() - 3600000).toISOString(),
    findings: { pass: 1, fail: 0, review: 0 },
  },
];

const statusConfig = {
  pending: { icon: Clock, color: "text-muted-foreground", label: "Pending", animate: false },
  running: { icon: Loader2, color: "text-blue-500", label: "Running", animate: true },
  completed: { icon: CheckCircle2, color: "text-green-500", label: "Completed", animate: false },
  failed: { icon: XCircle, color: "text-red-500", label: "Failed", animate: false },
};

export default function AuditsPage() {
  return (
    <div className="min-h-screen">
      <Header
        title="Audits"
        description="View and manage compliance audits"
      />

      <div className="p-6 space-y-6">
        {/* Actions */}
        <div className="flex justify-between items-center">
          <div className="flex gap-2">
            <Button variant="outline" size="sm">All</Button>
            <Button variant="ghost" size="sm">Running</Button>
            <Button variant="ghost" size="sm">Completed</Button>
            <Button variant="ghost" size="sm">Failed</Button>
          </div>
          <Link href="/audits/new">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              New Audit
            </Button>
          </Link>
        </div>

        {/* Audit List */}
        <div className="space-y-3">
          {mockAudits.map((audit) => {
            const config = statusConfig[audit.status];
            const Icon = config.icon;

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
                          <p className="font-medium">{audit.name}</p>
                          <p className="text-sm text-muted-foreground">
                            {audit.compliance}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-4">
                        <div className="flex gap-2">
                          <Badge variant="success">{audit.findings.pass} Pass</Badge>
                          {audit.findings.fail > 0 && (
                            <Badge variant="error">{audit.findings.fail} Fail</Badge>
                          )}
                          {audit.findings.review > 0 && (
                            <Badge variant="warning">{audit.findings.review} Review</Badge>
                          )}
                        </div>
                        <span className="text-sm text-muted-foreground">
                          {formatDate(audit.createdAt)}
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
