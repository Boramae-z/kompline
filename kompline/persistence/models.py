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
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)


class ComplianceRecord(Base):
    """Compliance definition stored in DB."""

    __tablename__ = "compliance"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    version: Mapped[str] = mapped_column(String(64))
    jurisdiction: Mapped[str] = mapped_column(String(32))
    scope: Mapped[list] = mapped_column(JSON, default=list)
    report_template: Mapped[str] = mapped_column(String(64))
    description: Mapped[str] = mapped_column(Text, default="")
    effective_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)


class ComplianceItemRecord(Base):
    """Compliance item (granular check) stored in DB."""

    __tablename__ = "compliance_item"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    compliance_id: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(32))
    check_points: Mapped[list] = mapped_column(JSON, default=list)
    pass_criteria: Mapped[str] = mapped_column(Text, default="")
    fail_examples: Mapped[list] = mapped_column(JSON, default=list)
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)


class EvidenceRequirementRecord(Base):
    """Evidence requirement stored in DB."""

    __tablename__ = "evidence_requirement"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    owner_type: Mapped[str] = mapped_column(String(32))  # "compliance" or "item"
    owner_id: Mapped[str] = mapped_column(String(128), index=True)
    description: Mapped[str] = mapped_column(Text)
    artifact_types: Mapped[list] = mapped_column(JSON, default=list)
    extraction_hints: Mapped[list] = mapped_column(JSON, default=list)
    required: Mapped[bool] = mapped_column(default=True)


class ArtifactRecord(Base):
    """Artifact definition stored in DB."""

    __tablename__ = "artifact"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    type: Mapped[str] = mapped_column(String(32))
    locator: Mapped[str] = mapped_column(Text)
    access_method: Mapped[str] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(Text, default="")
    extraction_schema: Mapped[dict] = mapped_column(JSON, default=dict)
    provenance: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)


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
    extra_data: Mapped[dict] = mapped_column(JSON, default=dict)
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
