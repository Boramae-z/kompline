"""Evidence models for audit trail."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from kompline.models.artifact import Provenance


class EvidenceType(str, Enum):
    """Type of evidence collected."""

    CODE_SNIPPET = "code_snippet"  # Extracted code fragment
    DOCUMENT_EXCERPT = "document_excerpt"  # Text from documents
    LOG_ENTRY = "log_entry"  # Log file entries
    CONFIG_VALUE = "config_value"  # Configuration settings
    QUERY_RESULT = "query_result"  # Database query results
    API_RESPONSE = "api_response"  # API call responses
    AST_PATTERN = "ast_pattern"  # AST analysis results
    METRIC = "metric"  # Numerical measurements


@dataclass
class Evidence:
    """Evidence collected by a Reader agent.

    Evidence represents a piece of information extracted from an artifact
    that is relevant to evaluating a compliance rule.
    """

    id: str  # Unique identifier
    relation_id: str  # AuditRelation this evidence belongs to
    source: str  # Where it came from (file path, URL, etc.)
    type: EvidenceType
    content: str  # The actual evidence content
    provenance: Provenance
    collected_at: datetime = field(default_factory=datetime.now)
    collected_by: str = "unknown"  # Reader Agent ID
    metadata: dict[str, Any] = field(default_factory=dict)

    # Location details
    line_number: int | None = None  # For code
    line_end: int | None = None  # End line for ranges
    page_number: int | None = None  # For documents
    column: int | None = None  # Column position

    # Relevance
    relevance_score: float = 1.0  # How relevant to the rule (0-1)
    rule_ids: list[str] = field(default_factory=list)  # Rules this relates to

    @property
    def location_str(self) -> str:
        """Get human-readable location string."""
        parts = []
        if self.line_number is not None:
            if self.line_end and self.line_end != self.line_number:
                parts.append(f"lines {self.line_number}-{self.line_end}")
            else:
                parts.append(f"line {self.line_number}")
        if self.page_number is not None:
            parts.append(f"page {self.page_number}")
        if self.column is not None:
            parts.append(f"col {self.column}")
        return ", ".join(parts) if parts else "unknown location"

    def to_citation(self) -> str:
        """Generate a citation string for reports."""
        return f"{self.source}:{self.location_str}"


@dataclass
class EvidenceCollection:
    """A collection of evidence for an audit relation."""

    relation_id: str
    items: list[Evidence] = field(default_factory=list)
    collected_at: datetime = field(default_factory=datetime.now)

    def add(self, evidence: Evidence) -> None:
        """Add evidence to the collection."""
        self.items.append(evidence)

    def get_by_type(self, evidence_type: EvidenceType) -> list[Evidence]:
        """Get all evidence of a specific type."""
        return [e for e in self.items if e.type == evidence_type]

    def get_by_rule(self, rule_id: str) -> list[Evidence]:
        """Get all evidence related to a specific rule."""
        return [e for e in self.items if rule_id in e.rule_ids]

    def get_by_source(self, source: str) -> list[Evidence]:
        """Get all evidence from a specific source."""
        return [e for e in self.items if e.source == source]

    @property
    def sources(self) -> set[str]:
        """Get all unique sources."""
        return {e.source for e in self.items}

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self):
        return iter(self.items)
