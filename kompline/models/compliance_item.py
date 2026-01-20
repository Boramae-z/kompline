"""ComplianceItem model representing a single check within a compliance framework."""

from dataclasses import dataclass, field
from typing import Any

from kompline.models.compliance import EvidenceRequirement, RuleCategory, RuleSeverity


@dataclass
class ComplianceItem:
    """A single compliance item (granular check)."""

    id: str
    compliance_id: str
    title: str
    description: str
    category: RuleCategory
    severity: RuleSeverity
    check_points: list[str]
    pass_criteria: str
    fail_examples: list[str]
    evidence_requirements: list[EvidenceRequirement] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
