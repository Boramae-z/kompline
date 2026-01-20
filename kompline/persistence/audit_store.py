"""Persistence helpers for audit runs."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from kompline.db import get_sessionmaker, get_async_engine
from kompline.models import AuditRelation
from kompline.persistence.models import (
    Base,
    AuditRunRecord,
    AuditRelationRecord,
    EvidenceRecord,
    FindingRecord,
)


async def ensure_schema() -> None:
    """Create tables if they do not exist."""
    async with get_async_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def save_audit_result(
    run_id: str,
    compliance_ids: list[str],
    artifact_ids: list[str],
    relations: list[AuditRelation],
    metadata: dict[str, Any] | None = None,
) -> None:
    """Persist audit run results."""
    await ensure_schema()
    async_session = get_sessionmaker()
    async with async_session() as session:
        await _save_run(
            session,
            run_id=run_id,
            compliance_ids=compliance_ids,
            artifact_ids=artifact_ids,
            metadata=metadata or {},
        )
        for rel in relations:
            await _save_relation(session, run_id, rel)
        await session.commit()


async def _save_run(
    session: AsyncSession,
    run_id: str,
    compliance_ids: list[str],
    artifact_ids: list[str],
    metadata: dict[str, Any],
) -> None:
    record = AuditRunRecord(
        id=run_id,
        created_at=datetime.utcnow(),
        status="completed",
        compliance_ids=compliance_ids,
        artifact_ids=artifact_ids,
        metadata=metadata,
    )
    await session.merge(record)


async def _save_relation(session: AsyncSession, run_id: str, rel: AuditRelation) -> None:
    rel_record = AuditRelationRecord(
        id=f"{run_id}:{rel.id}",
        audit_run_id=run_id,
        relation_id=rel.id,
        compliance_id=rel.compliance_id,
        compliance_item_id=rel.compliance_item_id,
        artifact_id=rel.artifact_id,
        status=rel.status.value,
        started_at=rel.started_at,
        completed_at=rel.completed_at,
        error_message=rel.error_message,
        evidence_count=len(rel.evidence_collected),
        finding_count=len(rel.findings),
    )
    await session.merge(rel_record)

    for ev in rel.evidence_collected:
        ev_record = EvidenceRecord(
            id=ev.id,
            audit_relation_id=rel_record.id,
            artifact_id=rel.artifact_id,
            type=ev.type.value,
            source=ev.source,
            content=ev.content,
            metadata=ev.metadata,
            line_number=ev.line_number,
            line_end=ev.line_end,
            page_number=ev.page_number,
            relevance_score=ev.relevance_score,
            rule_ids=ev.rule_ids,
            collected_at=ev.collected_at,
        )
        await session.merge(ev_record)

    for finding in rel.findings:
        find_record = FindingRecord(
            id=finding.id,
            audit_relation_id=rel_record.id,
            rule_id=finding.rule_id,
            status=finding.status.value,
            confidence=finding.confidence,
            reasoning=finding.reasoning,
            recommendation=finding.recommendation,
            evidence_refs=finding.evidence_refs,
            requires_human_review=finding.requires_human_review,
            review_status=finding.review_status.value if finding.review_status else None,
            created_at=finding.created_at,
        )
        await session.merge(find_record)
