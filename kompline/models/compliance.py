"""Compliance and Rule models for regulatory requirements."""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from kompline.models.compliance_item import ComplianceItem


class RuleCategory(str, Enum):
    """Category of compliance rule."""

    ALGORITHM_FAIRNESS = "algorithm_fairness"
    DATA_HANDLING = "data_handling"
    TRANSPARENCY = "transparency"
    DISCLOSURE = "disclosure"
    PRIVACY = "privacy"
    SECURITY = "security"


class RuleSeverity(str, Enum):
    """Severity level of a compliance rule."""

    CRITICAL = "critical"  # Must pass, failure blocks
    HIGH = "high"  # Should pass, failure requires remediation
    MEDIUM = "medium"  # Recommended, failure triggers review
    LOW = "low"  # Advisory, failure noted


@dataclass
class EvidenceRequirement:
    """Specification of evidence needed to evaluate a rule."""

    id: str
    description: str
    artifact_types: list[str]  # Types of artifacts that can provide this evidence
    extraction_hints: list[str]  # Hints for readers on what to extract
    required: bool = True


@dataclass
class Rule:
    """A single compliance rule to evaluate."""

    id: str  # e.g., "ALG-001"
    title: str  # e.g., "Algorithm Fairness - Sorting Transparency"
    description: str
    category: RuleCategory
    severity: RuleSeverity
    check_points: list[str]  # Specific items to verify
    pass_criteria: str  # Description of what constitutes passing
    fail_examples: list[str]  # Examples of failures
    evidence_requirements: list[EvidenceRequirement] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Compliance:
    """A compliance framework containing multiple rules.

    Examples:
    - 개인정보보호법 (PIPA)
    - 알고리즘 공정성 자가평가 (Algorithm Fairness Self-Assessment, Form 별지5)
    - SOC2
    """

    id: str  # e.g., "byeolji5-fairness", "pipa-kr-2024"
    name: str  # e.g., "알고리즘 공정성 자가평가"
    version: str  # e.g., "2024.01"
    jurisdiction: str  # e.g., "KR", "global"
    scope: list[str]  # Areas covered: ["algorithm", "data_handling"]
    rules: list[Rule]
    evidence_requirements: list[EvidenceRequirement] = field(default_factory=list)
    report_template: str = "default"  # Template ID for report generation
    items: list["ComplianceItem"] = field(default_factory=list)
    description: str = ""
    effective_date: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_rules_by_category(self, category: RuleCategory) -> list[Rule]:
        """Get all rules in a specific category."""
        return [r for r in self.rules if r.category == category]

    def get_rules_by_severity(self, severity: RuleSeverity) -> list[Rule]:
        """Get all rules of a specific severity."""
        return [r for r in self.rules if r.severity == severity]

    def get_critical_rules(self) -> list[Rule]:
        """Get all critical rules that must pass."""
        return self.get_rules_by_severity(RuleSeverity.CRITICAL)

    def get_items(self) -> list["ComplianceItem"]:
        """Get compliance items (build from rules if needed)."""
        if self.items:
            return self.items
        # Lazy conversion from legacy rules
        from kompline.models.compliance_item import ComplianceItem

        self.items = [
            ComplianceItem(
                id=rule.id,
                compliance_id=self.id,
                title=rule.title,
                description=rule.description,
                category=rule.category,
                severity=rule.severity,
                check_points=rule.check_points,
                pass_criteria=rule.pass_criteria,
                fail_examples=rule.fail_examples,
                evidence_requirements=rule.evidence_requirements,
                metadata=rule.metadata,
            )
            for rule in self.rules
        ]
        return self.items

    def get_item_by_id(self, item_id: str) -> "ComplianceItem | None":
        """Get a compliance item by ID."""
        for item in self.get_items():
            if item.id == item_id:
                return item
        return None
