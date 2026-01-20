"use client";

import { useState } from "react";
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Clock,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { formatDuration } from "@/lib/utils";

export type StageStatus = "pending" | "running" | "success" | "failed" | "skipped";

interface PipelineStageProps {
  name: string;
  status: StageStatus;
  agent?: string;
  duration?: number;
  logs?: string[];
  children?: React.ReactNode;
}

const statusConfig = {
  pending: {
    icon: Clock,
    color: "text-muted-foreground",
    bg: "bg-muted",
    label: "Pending",
    animate: false,
  },
  running: {
    icon: Loader2,
    color: "text-blue-500",
    bg: "bg-blue-50 dark:bg-blue-950",
    label: "Running",
    animate: true,
  },
  success: {
    icon: CheckCircle2,
    color: "text-green-500",
    bg: "bg-green-50 dark:bg-green-950",
    label: "Success",
    animate: false,
  },
  failed: {
    icon: XCircle,
    color: "text-red-500",
    bg: "bg-red-50 dark:bg-red-950",
    label: "Failed",
    animate: false,
  },
  skipped: {
    icon: Clock,
    color: "text-muted-foreground",
    bg: "bg-muted",
    label: "Skipped",
    animate: false,
  },
};

export function PipelineStage({
  name,
  status,
  agent,
  duration,
  logs,
  children,
}: PipelineStageProps) {
  const [expanded, setExpanded] = useState(status === "running" || status === "failed");
  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <div className={cn("rounded-lg border", config.bg)}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between p-4 text-left"
      >
        <div className="flex items-center gap-3">
          <Icon
            className={cn(
              "h-5 w-5",
              config.color,
              config.animate && "animate-spin"
            )}
          />
          <div>
            <div className="font-medium">{name}</div>
            {agent && (
              <div className="text-xs text-muted-foreground">Agent: {agent}</div>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
          {duration !== undefined && (
            <span className="text-sm text-muted-foreground">
              {formatDuration(duration)}
            </span>
          )}
          {(logs?.length || children) && (
            expanded ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )
          )}
        </div>
      </button>

      {expanded && (logs?.length || children) && (
        <div className="border-t bg-background/50 p-4">
          {logs && logs.length > 0 && (
            <pre className="overflow-x-auto rounded bg-muted p-3 text-xs font-mono">
              {logs.join("\n")}
            </pre>
          )}
          {children}
        </div>
      )}
    </div>
  );
}
