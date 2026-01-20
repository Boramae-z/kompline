"""Finding models for audit results."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


@dataclass
class Citation:
    """A citation from the compliance knowledge base.

    Citations provide traceable references to the source documents
    that support a finding's evaluation.
    """

    source: str  # Document/regulation reference (e.g., "알고리즘 공정성 자가평가 제3조")
    text: str  # Relevant text excerpt
    relevance: float  # 0.0 to 1.0 relevance score
    page: int | None = None  # Page number if applicable
    section: str | None = None  # Section/article reference
    document_id: str | None = None  # Internal document ID

    def to_dict(self) -> dict[str, Any]:
        """Convert citation to dictionary for serialization."""
        return {
            "source": self.source,
            "text": self.text,
            "relevance": self.relevance,
            "page": self.page,
            "section": self.section,
            "document_id": self.document_id,
        }


class FindingStatus(str, Enum):
    """Status of a compliance finding."""

    PASS = "pass"  # Rule requirements met
    FAIL = "fail"  # Rule requirements not met
    REVIEW = "review"  # Needs human review
    NOT_APPLICABLE = "not_applicable"  # Rule doesn't apply to this artifact


class ReviewStatus(str, Enum):
    """Status of human review for a finding."""

    PENDING = "pending"  # Awaiting review
    APPROVED = "approved"  # Human confirmed the finding
    REJECTED = "rejected"  # Human rejected the finding
    MODIFIED = "modified"  # Human modified the finding


@dataclass
class Finding:
    """Result of evaluating a compliance rule against an artifact.

    A Finding represents the Audit Agent's assessment of whether
    a specific rule is satisfied by the artifact.
    """

    id: str  # Unique identifier
    relation_id: str  # AuditRelation this finding belongs to
    rule_id: str  # Rule being evaluated
    status: FindingStatus
    confidence: float  # 0.0 to 1.0
    evidence_refs: list[str]  # Evidence IDs supporting this finding
    reasoning: str  # Explanation of the judgment
    recommendation: str | None = None  # For FAIL: remediation steps
    citations: list[Citation] = field(default_factory=list)  # Source citations from RAG
    requires_human_review: bool = False
    review_status: ReviewStatus | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_notes: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Set review requirements based on status and confidence."""
        if self.status == FindingStatus.REVIEW:
            self.requires_human_review = True
            self.review_status = ReviewStatus.PENDING
        elif self.status == FindingStatus.FAIL:
            self.requires_human_review = True
            self.review_status = ReviewStatus.PENDING
        elif self.confidence < 0.7:
            self.requires_human_review = True
            self.review_status = ReviewStatus.PENDING

    def approve(self, reviewer: str, notes: str | None = None) -> None:
        """Mark finding as approved by human reviewer."""
        self.review_status = ReviewStatus.APPROVED
        self.reviewed_by = reviewer
        self.reviewed_at = datetime.now()
        self.review_notes = notes

    def reject(self, reviewer: str, notes: str) -> None:
        """Mark finding as rejected by human reviewer."""
        self.review_status = ReviewStatus.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = datetime.now()
        self.review_notes = notes

    def modify(self, reviewer: str, new_status: FindingStatus, notes: str) -> None:
        """Modify finding status based on human review."""
        self.status = new_status
        self.review_status = ReviewStatus.MODIFIED
        self.reviewed_by = reviewer
        self.reviewed_at = datetime.now()
        self.review_notes = notes

    @property
    def is_passing(self) -> bool:
        """Check if finding indicates compliance."""
        return self.status in (FindingStatus.PASS, FindingStatus.NOT_APPLICABLE)

    @property
    def needs_attention(self) -> bool:
        """Check if finding needs action."""
        return self.status in (FindingStatus.FAIL, FindingStatus.REVIEW)

    @property
    def is_reviewed(self) -> bool:
        """Check if human review is complete."""
        if not self.requires_human_review:
            return True
        return self.review_status in (
            ReviewStatus.APPROVED,
            ReviewStatus.REJECTED,
            ReviewStatus.MODIFIED,
        )


@dataclass
class FindingSummary:
    """Summary of findings for an audit relation."""

    relation_id: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    review: int = 0
    not_applicable: int = 0
    pending_review: int = 0
    avg_confidence: float = 0.0

    @classmethod
    def from_findings(cls, relation_id: str, findings: list[Finding]) -> "FindingSummary":
        """Create summary from list of findings."""
        summary = cls(relation_id=relation_id, total=len(findings))

        if not findings:
            return summary

        confidences = []
        for f in findings:
            confidences.append(f.confidence)
            if f.status == FindingStatus.PASS:
                summary.passed += 1
            elif f.status == FindingStatus.FAIL:
                summary.failed += 1
            elif f.status == FindingStatus.REVIEW:
                summary.review += 1
            else:
                summary.not_applicable += 1

            if f.requires_human_review and not f.is_reviewed:
                summary.pending_review += 1

        summary.avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        return summary

    @property
    def compliance_rate(self) -> float:
        """Calculate compliance rate (pass + n/a) / total."""
        applicable = self.total - self.not_applicable
        if applicable == 0:
            return 1.0
        return self.passed / applicable

    @property
    def is_compliant(self) -> bool:
        """Check if all applicable rules pass."""
        return self.failed == 0 and self.review == 0
