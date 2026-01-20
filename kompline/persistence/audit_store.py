"""Persistence helpers for audit runs using Supabase REST API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from kompline.models import AuditRelation
from kompline.supabase_client import get_async_supabase_client


async def save_audit_result(
    run_id: str,
    compliance_ids: list[str],
    artifact_ids: list[str],
    relations: list[AuditRelation],
    metadata: dict[str, Any] | None = None,
) -> None:
    """Persist audit run results."""
    client = await get_async_supabase_client()

    # Save audit run
    run_data = {
        "id": run_id,
        "created_at": datetime.utcnow().isoformat(),
        "status": "completed",
        "compliance_ids": compliance_ids,
        "artifact_ids": artifact_ids,
        "extra_data": metadata or {},
    }
    await client.table("audit_run").upsert(run_data).execute()

    # Save relations, evidence, and findings
    for rel in relations:
        await _save_relation(client, run_id, rel)


async def _save_relation(client: Any, run_id: str, rel: AuditRelation) -> None:
    """Save a single audit relation with its evidence and findings."""
    rel_id = f"{run_id}:{rel.id}"

    rel_data = {
        "id": rel_id,
        "audit_run_id": run_id,
        "relation_id": rel.id,
        "compliance_id": rel.compliance_id,
        "compliance_item_id": rel.compliance_item_id,
        "artifact_id": rel.artifact_id,
        "status": rel.status.value,
        "started_at": rel.started_at.isoformat() if rel.started_at else None,
        "completed_at": rel.completed_at.isoformat() if rel.completed_at else None,
        "error_message": rel.error_message,
        "evidence_count": len(rel.evidence_collected),
        "finding_count": len(rel.findings),
    }
    await client.table("audit_relation").upsert(rel_data).execute()

    # Save evidence
    for ev in rel.evidence_collected:
        ev_data = {
            "id": ev.id,
            "audit_relation_id": rel_id,
            "artifact_id": rel.artifact_id,
            "type": ev.type.value,
            "source": ev.source,
            "content": ev.content,
            "extra_data": ev.metadata,
            "line_number": ev.line_number,
            "line_end": ev.line_end,
            "page_number": ev.page_number,
            "relevance_score": ev.relevance_score,
            "rule_ids": ev.rule_ids,
            "collected_at": ev.collected_at.isoformat(),
        }
        await client.table("evidence").upsert(ev_data).execute()

    # Save findings
    for finding in rel.findings:
        find_data = {
            "id": finding.id,
            "audit_relation_id": rel_id,
            "rule_id": finding.rule_id,
            "status": finding.status.value,
            "confidence": finding.confidence,
            "reasoning": finding.reasoning,
            "recommendation": finding.recommendation,
            "evidence_refs": finding.evidence_refs,
            "requires_human_review": finding.requires_human_review,
            "review_status": finding.review_status.value if finding.review_status else None,
            "created_at": finding.created_at.isoformat(),
        }
        await client.table("finding").upsert(find_data).execute()
