# Frontend Redesign: Production-Grade UI

## Overview

- **Purpose**: Replace Streamlit UI with production-grade Next.js frontend
- **Style**: GitHub Actions/GitLab CI - pipeline view, step progress, log streaming
- **Target Users**: Auditor, Developer (Auditee), Pre-check User
- **Tech Stack**: Next.js + TypeScript + shadcn/ui + Tailwind CSS

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────┐ │
│  │Dashboard│ │ Audits  │ │Pipeline │ │ Review  │ │  Reports  │ │
│  │  Page   │ │  List   │ │  View   │ │  Queue  │ │  Export   │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └───────────┘ │
└─────────────────────────┬───────────────────────────────────────┘
                          │ REST API (polling)
┌─────────────────────────▼───────────────────────────────────────┐
│                    Backend (FastAPI) - Extended                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────────┐ │
│  │ /audits  │ │ /stream  │ │ /reviews │ │ /reports           │ │
│  │  CRUD    │ │  logs    │ │  HITL    │ │  export            │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────────┘ │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                 Kompline Core (Unchanged)                        │
│  AuditOrchestrator → AuditAgent → Readers → Findings            │
└─────────────────────────────────────────────────────────────────┘
```

### Key Principles

- Keep existing `kompline/` core logic unchanged
- Extend FastAPI endpoints to support frontend
- Polling-based MVP → SSE/WebSocket ready architecture

## Page Structure

```
/                       → Dashboard (role-based summary)
/audits                 → Audit list (filter: status, compliance, date)
/audits/new             → New audit (code upload or repo connection)
/audits/[id]            → Pipeline view (GitHub Actions style)
/audits/[id]/logs       → Real-time log streaming
/reviews                → HITL review queue (for auditors)
/reviews/[findingId]    → Review detail (approve/reject/modify)
/reports                → Report list and export
/reports/[id]           → Report detail (Byeolji5 format, etc.)
/settings               → Compliance management, notification settings
```

### User Flows by Role

| Role | Primary Flow |
|------|--------------|
| **Auditor** | Dashboard → Reviews → Approve/Reject → Reports |
| **Auditee** | Audits/new → Pipeline monitoring → Review response |
| **Pre-check** | Audits/new (pre-check) → Immediate result |

### Pipeline View (`/audits/[id]`)

```
┌────────────┐    ┌────────────┐    ┌────────────┐    ┌────────────┐
│ 📥 Input   │───▶│ 🔍 Analyze │───▶│ ⚖️ Evaluate│───▶│ 📋 Report  │
│ Received   │    │ Code       │    │ Rules      │    │ Generate   │
│   ✓ Done   │    │  Running   │    │  Pending   │    │  Pending   │
└────────────┘    └────────────┘    └────────────┘    └────────────┘
                        │
                   ┌────▼────┐
                   │ 📜 Logs │  ← Click for real-time logs
                   └─────────┘
```

## Component Design

### 1. Pipeline Stage Component

```tsx
<PipelineStage
  name="Code Analysis"
  status="running" | "success" | "failed" | "pending"
  duration="12s"
  agent="CodeReader"
  expandable={true}
/>
```

### 2. Finding Card Component

```tsx
<FindingCard
  ruleId="FAIR-001"
  status="fail"
  confidence={0.85}
  reasoning="Undocumented affiliate boost detected"
  evidence={[{ file: "ranking.py", line: 42 }]}
  actions={["approve", "reject", "request-context"]}
/>
```

### 3. Log Stream Component

```tsx
<LogStream auditId={id} autoScroll={true}>
  🟦 [orchestrator] Starting audit: 1 compliance × 1 artifact
  🟩 [code_reader] Extracting evidence from ranking.py
  🟨 [rule_evaluator] Evaluating FAIR-001: Algorithm Fairness
</LogStream>
```

### UI Library

- **shadcn/ui**: Tailwind-based, copy-paste customizable
- **Radix Primitives**: Accessibility guaranteed
- **Lucide Icons**: Lightweight, GitHub Actions-like icons

## Backend API Extensions

### Audit Management

```
POST   /api/audits              # Start new audit (async, returns audit_id)
GET    /api/audits              # Audit list (filtering, pagination)
GET    /api/audits/{id}         # Audit detail (status, progress)
GET    /api/audits/{id}/logs    # Log query (offset-based polling)
DELETE /api/audits/{id}         # Cancel audit
```

### HITL Review

```
GET    /api/reviews             # Pending review list
GET    /api/reviews/{id}        # Review detail
POST   /api/reviews/{id}/approve   # Approve
POST   /api/reviews/{id}/reject    # Reject
POST   /api/reviews/{id}/comment   # Request context
```

### Reports

```
GET    /api/reports             # Report list
GET    /api/reports/{id}        # Report detail
GET    /api/reports/{id}/export # PDF/Markdown download
```

### Metadata

```
GET    /api/compliances         # Registered compliance list
GET    /api/artifacts           # Registered artifact list
```

### Polling Strategy (MVP)

```typescript
const pollAuditStatus = (auditId: string) => {
  return useQuery({
    queryKey: ['audit', auditId],
    queryFn: () => fetchAudit(auditId),
    refetchInterval: (data) =>
      data?.status === 'running' ? 2000 : false,
  });
};
```

### Extension Point (Future SSE)

```
GET /api/audits/{id}/stream    # SSE endpoint
```

## File Structure

### Frontend

```
web/
├── app/                      # Next.js App Router
│   ├── layout.tsx           # Common layout (sidebar, header)
│   ├── page.tsx             # Dashboard
│   ├── audits/
│   │   ├── page.tsx         # Audit list
│   │   ├── new/page.tsx     # New audit
│   │   └── [id]/
│   │       ├── page.tsx     # Pipeline view
│   │       └── logs/page.tsx
│   ├── reviews/
│   │   ├── page.tsx         # Review queue
│   │   └── [id]/page.tsx    # Review detail
│   └── reports/
│       └── [id]/page.tsx
├── components/
│   ├── ui/                  # shadcn/ui components
│   ├── pipeline/            # PipelineStage, PipelineView
│   ├── findings/            # FindingCard, FindingList
│   ├── logs/                # LogStream, LogEntry
│   └── layout/              # Sidebar, Header, Nav
├── lib/
│   ├── api.ts               # API client
│   └── hooks/               # useAudit, useReviews, etc.
├── package.json
└── tailwind.config.js
```

## Implementation Priority (Hackathon MVP)

| Order | Item | Importance |
|-------|------|------------|
| 1 | Pipeline view (`/audits/[id]`) | ⭐⭐⭐ Core demo |
| 2 | New audit (`/audits/new`) | ⭐⭐⭐ User entry point |
| 3 | Log streaming | ⭐⭐ Multi-agent visualization |
| 4 | Review queue (`/reviews`) | ⭐⭐ HITL demo |
| 5 | Dashboard | ⭐ Nice to have |

## Summary

- Next.js + TypeScript + shadcn/ui
- GitHub Actions style pipeline view
- Polling-based MVP (extensible architecture)
- Extend existing FastAPI + keep Kompline core unchanged
