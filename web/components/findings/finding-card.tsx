"use client";

import { CheckCircle2, XCircle, AlertTriangle, MinusCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Finding } from "@/lib/api";

interface FindingCardProps {
  finding: Finding;
  showActions?: boolean;
  onApprove?: (id: string) => void;
  onReject?: (id: string) => void;
  onRequestContext?: (id: string) => void;
}

const statusConfig = {
  pass: {
    icon: CheckCircle2,
    color: "text-green-500",
    badge: "success" as const,
    label: "PASS",
  },
  fail: {
    icon: XCircle,
    color: "text-red-500",
    badge: "error" as const,
    label: "FAIL",
  },
  review: {
    icon: AlertTriangle,
    color: "text-yellow-500",
    badge: "warning" as const,
    label: "REVIEW",
  },
  not_applicable: {
    icon: MinusCircle,
    color: "text-muted-foreground",
    badge: "secondary" as const,
    label: "N/A",
  },
};

export function FindingCard({
  finding,
  showActions = false,
  onApprove,
  onReject,
  onRequestContext,
}: FindingCardProps) {
  const config = statusConfig[finding.status];
  const Icon = config.icon;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <Icon className={cn("h-5 w-5", config.color)} />
            <CardTitle className="text-base">{finding.rule_id}</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={config.badge}>{config.label}</Badge>
            <Badge variant="outline">{Math.round(finding.confidence * 100)}%</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <p className="text-sm font-medium text-muted-foreground">Reasoning</p>
          <p className="text-sm">{finding.reasoning}</p>
        </div>

        {finding.recommendation && (
          <div className="rounded-md bg-yellow-50 p-3 dark:bg-yellow-950">
            <p className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
              Recommendation
            </p>
            <p className="text-sm text-yellow-700 dark:text-yellow-300">
              {finding.recommendation}
            </p>
          </div>
        )}

        {finding.evidence_refs.length > 0 && (
          <div>
            <p className="text-sm font-medium text-muted-foreground">Evidence</p>
            <div className="mt-1 flex flex-wrap gap-1">
              {finding.evidence_refs.map((ref, i) => (
                <Badge key={i} variant="outline" className="text-xs">
                  {ref}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {showActions && finding.requires_human_review && (
          <div className="flex gap-2 border-t pt-3">
            <Button
              size="sm"
              variant="success"
              onClick={() => onApprove?.(finding.id)}
            >
              Approve
            </Button>
            <Button
              size="sm"
              variant="destructive"
              onClick={() => onReject?.(finding.id)}
            >
              Reject
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => onRequestContext?.(finding.id)}
            >
              Request Context
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
