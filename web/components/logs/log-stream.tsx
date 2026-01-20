"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import type { LogEvent } from "@/lib/api";

interface LogStreamProps {
  events: LogEvent[];
  autoScroll?: boolean;
  maxHeight?: string;
}

const agentColors: Record<string, string> = {
  orchestrator: "text-blue-400",
  audit_orchestrator: "text-blue-400",
  code_analyzer: "text-green-400",
  audit_agent: "text-green-400",
  code_reader: "text-orange-400",
  pdf_reader: "text-orange-400",
  config_reader: "text-orange-400",
  rule_matcher: "text-yellow-400",
  rule_evaluator: "text-yellow-400",
  report_generator: "text-purple-400",
  system: "text-gray-400",
};

const agentIcons: Record<string, string> = {
  orchestrator: "🟦",
  audit_orchestrator: "🟦",
  code_analyzer: "🟩",
  audit_agent: "🟩",
  code_reader: "🟧",
  pdf_reader: "🟧",
  config_reader: "🟧",
  rule_matcher: "🟨",
  rule_evaluator: "🟨",
  report_generator: "🟪",
  system: "⬜",
};

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function LogStream({
  events,
  autoScroll = true,
  maxHeight = "400px",
}: LogStreamProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [events, autoScroll]);

  if (events.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-lg bg-muted/50 p-8 text-muted-foreground"
        style={{ minHeight: "200px" }}
      >
        Waiting for logs...
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className="overflow-auto rounded-lg bg-slate-950 p-4 font-mono text-sm"
      style={{ maxHeight }}
    >
      {events.map((event, index) => {
        const icon = agentIcons[event.agent] || "⬜";
        const colorClass = agentColors[event.agent] || "text-gray-400";
        const timestamp = event.timestamp ? formatTimestamp(event.timestamp) : "";

        return (
          <div key={index} className="flex gap-2 py-0.5 hover:bg-slate-900">
            <span className="text-slate-500 select-none">{timestamp}</span>
            <span className="select-none">{icon}</span>
            <span className={cn("font-medium", colorClass)}>
              [{event.agent}]
            </span>
            <span className="text-slate-400">{event.event_type}:</span>
            <span className="text-slate-200">{event.message}</span>
          </div>
        );
      })}
    </div>
  );
}
