"""AuditRelation and RunConfig models for audit workflow."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kompline.models.evidence import Evidence
    from kompline.models.finding import Finding


class AuditStatus(str, Enum):
    """Status of an audit relation."""

    PENDING = "pending"  # Not yet started
    RUNNING = "running"  # In progress
    COMPLETED = "completed"  # Finished successfully
    FAILED = "failed"  # Failed with error
    CANCELLED = "cancelled"  # Manually cancelled


@dataclass
class RunConfig:
    """Configuration for an audit run."""

    max_iterations: int = 3  # Max feedback loop iterations
    timeout_seconds: int = 300  # Timeout for the audit
    parallel_readers: bool = True  # Allow parallel reader execution
    confidence_threshold: float = 0.7  # Min confidence for auto-pass
    require_human_review_on_fail: bool = True  # FAIL findings need review
    trace_enabled: bool = True  # Enable detailed tracing
    use_llm: bool = True  # Use LLM for rule evaluation when available
    llm_model: str | None = None  # Optional model override
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditRelation:
    """Represents a (Compliance, Artifact) audit relationship.

    This is the core unit of audit. Each relation spawns one Audit Agent
    that evaluates all rules in the compliance against the artifact.
    """

    id: str  # Unique identifier: "rel-001"
    compliance_id: str  # Reference to Compliance
    artifact_id: str  # Reference to Artifact
    compliance_item_id: str | None = None  # Reference to ComplianceItem (optional)
    status: AuditStatus = AuditStatus.PENDING
    run_config: RunConfig = field(default_factory=RunConfig)
    evidence_collected: list[Any] = field(default_factory=list)  # Evidence objects
    findings: list[Any] = field(default_factory=list)  # Finding objects
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def start(self) -> None:
        """Mark the relation as started."""
        self.status = AuditStatus.RUNNING
        self.started_at = datetime.now()

    def complete(self) -> None:
        """Mark the relation as completed."""
        self.status = AuditStatus.COMPLETED
        self.completed_at = datetime.now()

    def fail(self, error: str) -> None:
        """Mark the relation as failed."""
        self.status = AuditStatus.FAILED
        self.completed_at = datetime.now()
        self.error_message = error

    def add_evidence(self, evidence: Evidence) -> None:
        """Add collected evidence."""
        self.evidence_collected.append(evidence)

    def add_finding(self, finding: Finding) -> None:
        """Add an evaluation finding."""
        self.findings.append(finding)

    @property
    def is_complete(self) -> bool:
        """Check if audit is complete (success or failure)."""
        return self.status in (AuditStatus.COMPLETED, AuditStatus.FAILED)

    @property
    def duration_seconds(self) -> float | None:
        """Calculate audit duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def get_findings_by_status(self, status: str) -> list[Any]:
        """Get findings filtered by status."""
        return [f for f in self.findings if f.status.value == status]


def create_audit_relations(
    compliance_ids: list[str],
    artifact_ids: list[str],
    run_config: RunConfig | None = None,
) -> list[AuditRelation]:
    """Create audit relations from compliance and artifact IDs.

    Creates Cartesian product of (compliance, artifact) pairs.

    Args:
        compliance_ids: List of compliance IDs to audit against.
        artifact_ids: List of artifact IDs to audit.
        run_config: Optional shared run configuration.

    Returns:
        List of AuditRelation objects.
    """
    config = run_config or RunConfig()
    relations = []

    for i, (comp_id, art_id) in enumerate(
        [(c, a) for c in compliance_ids for a in artifact_ids]
    ):
        relation = AuditRelation(
            id=f"rel-{i + 1:03d}",
            compliance_id=comp_id,
            artifact_id=art_id,
            run_config=config,
        )
        relations.append(relation)

    return relations
