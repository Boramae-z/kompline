"""SQLAlchemy models for Kompline persistence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, JSON, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base."""


class EvidenceCache(Base):
    """Cached evidence for an artifact snapshot."""

    __tablename__ = "evidence_cache"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    artifact_id: Mapped[str] = mapped_column(String(128), index=True)
    fingerprint: Mapped[str] = mapped_column(String(128), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    evidence_json: Mapped[dict] = mapped_column(JSON)


class AuditRunRecord(Base):
    """Audit run summary record."""

    __tablename__ = "audit_run"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    compliance_ids: Mapped[list] = mapped_column(JSON)
    artifact_ids: Mapped[list] = mapped_column(JSON)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)


class AuditRelationRecord(Base):
    """Audit relation record (item × artifact)."""

    __tablename__ = "audit_relation"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    audit_run_id: Mapped[str] = mapped_column(String(64), index=True)
    relation_id: Mapped[str] = mapped_column(String(64), index=True)
    compliance_id: Mapped[str] = mapped_column(String(128))
    compliance_item_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    artifact_id: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_count: Mapped[int] = mapped_column(default=0)
    finding_count: Mapped[int] = mapped_column(default=0)


class EvidenceRecord(Base):
    """Persisted evidence item."""

    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    audit_relation_id: Mapped[str] = mapped_column(String(128), index=True)
    artifact_id: Mapped[str] = mapped_column(String(128), index=True)
    type: Mapped[str] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    line_number: Mapped[int | None] = mapped_column(nullable=True)
    line_end: Mapped[int | None] = mapped_column(nullable=True)
    page_number: Mapped[int | None] = mapped_column(nullable=True)
    relevance_score: Mapped[float] = mapped_column(default=1.0)
    rule_ids: Mapped[list] = mapped_column(JSON, default=list)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FindingRecord(Base):
    """Persisted finding item."""

    __tablename__ = "finding"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    audit_relation_id: Mapped[str] = mapped_column(String(128), index=True)
    rule_id: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(default=0.0)
    reasoning: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_refs: Mapped[list] = mapped_column(JSON, default=list)
    requires_human_review: Mapped[bool] = mapped_column(default=False)
    review_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
