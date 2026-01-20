"use client";

import { PipelineStage, type StageStatus } from "./pipeline-stage";
import type { AuditResult, LogEvent } from "@/lib/api";

interface PipelineStage {
  id: string;
  name: string;
  status: StageStatus;
  agent: string;
  duration?: number;
  logs: string[];
}

interface PipelineViewProps {
  auditStatus: "pending" | "running" | "completed" | "failed";
  result?: AuditResult;
  trace: LogEvent[];
}

function deriveStages(
  auditStatus: string,
  trace: LogEvent[],
  result?: AuditResult
): PipelineStage[] {
  const stages: PipelineStage[] = [
    {
      id: "input",
      name: "Input Received",
      status: "success",
      agent: "system",
      logs: ["Source code received", "Validation passed"],
    },
    {
      id: "analyze",
      name: "Code Analysis",
      status: "pending",
      agent: "CodeReader",
      logs: [],
    },
    {
      id: "evaluate",
      name: "Rule Evaluation",
      status: "pending",
      agent: "AuditAgent",
      logs: [],
    },
    {
      id: "report",
      name: "Report Generation",
      status: "pending",
      agent: "ReportGenerator",
      logs: [],
    },
  ];

  // Update stages based on trace events
  const agentToStage: Record<string, string> = {
    code_reader: "analyze",
    code_analyzer: "analyze",
    audit_agent: "evaluate",
    rule_evaluator: "evaluate",
    rule_matcher: "evaluate",
    orchestrator: "analyze",
    audit_orchestrator: "analyze",
    report_generator: "report",
  };

  const stageStartTimes: Record<string, number> = {};
  const stageEndTimes: Record<string, number> = {};

  trace.forEach((event) => {
    const stageId = agentToStage[event.agent];
    if (!stageId) return;

    const stage = stages.find((s) => s.id === stageId);
    if (!stage) return;

    const timestamp = new Date(event.timestamp).getTime();

    // Track times
    if (!stageStartTimes[stageId]) {
      stageStartTimes[stageId] = timestamp;
    }
    stageEndTimes[stageId] = timestamp;

    // Add log
    stage.logs.push(`[${event.agent}] ${event.event_type}: ${event.message}`);

    // Update status based on event type
    if (event.event_type === "start" || event.event_type === "init") {
      if (stage.status === "pending") {
        stage.status = "running";
      }
    } else if (event.event_type === "complete") {
      stage.status = "success";
    } else if (event.event_type === "error") {
      stage.status = "failed";
    }
  });

  // Calculate durations
  stages.forEach((stage) => {
    if (stageStartTimes[stage.id] && stageEndTimes[stage.id]) {
      stage.duration = stageEndTimes[stage.id] - stageStartTimes[stage.id];
    }
  });

  // If audit completed, mark remaining pending stages
  if (auditStatus === "completed" && result) {
    stages.forEach((stage) => {
      if (stage.status === "pending") {
        stage.status = "success";
      }
    });
  }

  // If audit failed, mark running stages as failed
  if (auditStatus === "failed") {
    stages.forEach((stage) => {
      if (stage.status === "running") {
        stage.status = "failed";
      }
    });
  }

  return stages;
}

export function PipelineView({ auditStatus, result, trace }: PipelineViewProps) {
  const stages = deriveStages(auditStatus, trace, result);

  return (
    <div className="space-y-3">
      {stages.map((stage, index) => (
        <div key={stage.id} className="relative">
          {/* Connector line */}
          {index < stages.length - 1 && (
            <div className="absolute left-6 top-full z-0 h-3 w-0.5 bg-border" />
          )}
          <PipelineStage
            name={stage.name}
            status={stage.status}
            agent={stage.agent}
            duration={stage.duration}
            logs={stage.logs.length > 0 ? stage.logs : undefined}
          />
        </div>
      ))}
    </div>
  );
}
