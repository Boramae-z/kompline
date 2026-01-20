"""Compliance Registry for managing compliance definitions."""

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

from kompline.models import (
    Compliance,
    EvidenceRequirement,
    Rule,
    RuleCategory,
    RuleSeverity,
)


class ComplianceRegistry:
    """Registry for compliance frameworks.

    Manages loading, storing, and retrieving compliance definitions.
    Supports loading from YAML files or programmatic registration.
    """

    def __init__(self):
        self._compliances: dict[str, Compliance] = {}

    def register(self, compliance: Compliance) -> None:
        """Register a compliance framework.

        Args:
            compliance: The compliance framework to register.

        Raises:
            ValueError: If compliance with same ID already exists.
        """
        if compliance.id in self._compliances:
            raise ValueError(f"Compliance '{compliance.id}' already registered")
        self._compliances[compliance.id] = compliance

    def get(self, compliance_id: str) -> Compliance | None:
        """Get a compliance framework by ID.

        Args:
            compliance_id: The compliance ID.

        Returns:
            The compliance framework, or None if not found.
        """
        return self._compliances.get(compliance_id)

    def get_or_raise(self, compliance_id: str) -> Compliance:
        """Get a compliance framework by ID, raising if not found.

        Args:
            compliance_id: The compliance ID.

        Returns:
            The compliance framework.

        Raises:
            KeyError: If compliance not found.
        """
        if compliance_id not in self._compliances:
            raise KeyError(f"Compliance '{compliance_id}' not found")
        return self._compliances[compliance_id]

    def list_all(self) -> list[Compliance]:
        """List all registered compliances."""
        return list(self._compliances.values())

    def list_ids(self) -> list[str]:
        """List all compliance IDs."""
        return list(self._compliances.keys())

    def filter_by_jurisdiction(self, jurisdiction: str) -> list[Compliance]:
        """Get compliances for a specific jurisdiction."""
        return [c for c in self._compliances.values() if c.jurisdiction == jurisdiction]

    def filter_by_scope(self, scope: str) -> list[Compliance]:
        """Get compliances that cover a specific scope."""
        return [c for c in self._compliances.values() if scope in c.scope]

    def unregister(self, compliance_id: str) -> bool:
        """Remove a compliance from the registry.

        Args:
            compliance_id: The compliance ID to remove.

        Returns:
            True if removed, False if not found.
        """
        if compliance_id in self._compliances:
            del self._compliances[compliance_id]
            return True
        return False

    def clear(self) -> None:
        """Clear all registered compliances."""
        self._compliances.clear()

    def load_from_yaml(self, path: str | Path) -> Compliance:
        """Load a compliance definition from a YAML file.

        Args:
            path: Path to the YAML file.

        Returns:
            The loaded compliance framework.

        Raises:
            ImportError: If pyyaml is not installed.
        """
        if yaml is None:
            raise ImportError("pyyaml is required for YAML loading: pip install pyyaml")
        path = Path(path)
        with open(path) as f:
            data = yaml.safe_load(f)

        compliance = self._parse_compliance(data)
        self.register(compliance)
        return compliance

    def load_from_directory(self, directory: str | Path) -> list[Compliance]:
        """Load all compliance definitions from a directory.

        Args:
            directory: Directory containing YAML files.

        Returns:
            List of loaded compliance frameworks.
        """
        directory = Path(directory)
        loaded = []
        for yaml_file in directory.glob("*.yaml"):
            compliance = self.load_from_yaml(yaml_file)
            loaded.append(compliance)
        for yml_file in directory.glob("*.yml"):
            compliance = self.load_from_yaml(yml_file)
            loaded.append(compliance)
        return loaded

    def _parse_compliance(self, data: dict[str, Any]) -> Compliance:
        """Parse compliance data from dictionary."""
        rules = []
        for rule_data in data.get("rules", []):
            evidence_reqs = []
            for req_data in rule_data.get("evidence_requirements", []):
                evidence_reqs.append(
                    EvidenceRequirement(
                        id=req_data["id"],
                        description=req_data["description"],
                        artifact_types=req_data.get("artifact_types", []),
                        extraction_hints=req_data.get("extraction_hints", []),
                        required=req_data.get("required", True),
                    )
                )

            rules.append(
                Rule(
                    id=rule_data["id"],
                    title=rule_data["title"],
                    description=rule_data.get("description", ""),
                    category=RuleCategory(rule_data.get("category", "algorithm_fairness")),
                    severity=RuleSeverity(rule_data.get("severity", "high")),
                    check_points=rule_data.get("check_points", []),
                    pass_criteria=rule_data.get("pass_criteria", ""),
                    fail_examples=rule_data.get("fail_examples", []),
                    evidence_requirements=evidence_reqs,
                    metadata=rule_data.get("metadata", {}),
                )
            )

        evidence_requirements = []
        for req_data in data.get("evidence_requirements", []):
            evidence_requirements.append(
                EvidenceRequirement(
                    id=req_data["id"],
                    description=req_data["description"],
                    artifact_types=req_data.get("artifact_types", []),
                    extraction_hints=req_data.get("extraction_hints", []),
                    required=req_data.get("required", True),
                )
            )

        return Compliance(
            id=data["id"],
            name=data["name"],
            version=data.get("version", "1.0"),
            jurisdiction=data.get("jurisdiction", "global"),
            scope=data.get("scope", []),
            rules=rules,
            evidence_requirements=evidence_requirements,
            report_template=data.get("report_template", "default"),
            description=data.get("description", ""),
            effective_date=data.get("effective_date"),
            metadata=data.get("metadata", {}),
        )

    def __len__(self) -> int:
        return len(self._compliances)

    def __contains__(self, compliance_id: str) -> bool:
        return compliance_id in self._compliances


# Global registry instance
_default_registry: ComplianceRegistry | None = None


def get_compliance_registry() -> ComplianceRegistry:
    """Get the default compliance registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ComplianceRegistry()
    return _default_registry
