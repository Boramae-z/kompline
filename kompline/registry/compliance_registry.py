"""Compliance Registry for managing compliance definitions."""

from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

from kompline.models import (
    Compliance,
    ComplianceItem,
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

    def register_or_update(self, compliance: Compliance) -> None:
        """Register or update a compliance framework.

        Args:
            compliance: The compliance framework to register or update.
        """
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

        items = []
        for item_data in data.get("items", []):
            evidence_reqs = []
            for req_data in item_data.get("evidence_requirements", []):
                evidence_reqs.append(
                    EvidenceRequirement(
                        id=req_data["id"],
                        description=req_data["description"],
                        artifact_types=req_data.get("artifact_types", []),
                        extraction_hints=req_data.get("extraction_hints", []),
                        required=req_data.get("required", True),
                    )
                )

            items.append(
                ComplianceItem(
                    id=item_data["id"],
                    compliance_id=data["id"],
                    title=item_data["title"],
                    description=item_data.get("description", ""),
                    category=RuleCategory(item_data.get("category", "algorithm_fairness")),
                    severity=RuleSeverity(item_data.get("severity", "high")),
                    check_points=item_data.get("check_points", []),
                    pass_criteria=item_data.get("pass_criteria", ""),
                    fail_examples=item_data.get("fail_examples", []),
                    evidence_requirements=evidence_reqs,
                    metadata=item_data.get("metadata", {}),
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
            items=items,
            evidence_requirements=evidence_requirements,
            report_template=data.get("report_template", "default"),
            description=data.get("description", ""),
            effective_date=data.get("effective_date"),
            metadata=data.get("metadata", {}),
        )

    async def load_from_supabase(
        self,
        document_id: int | None = None,
        item_type: str | None = None,
        language: str | None = None,
        compliance_id: str | None = None,
        compliance_name: str | None = None,
    ) -> Compliance:
        """Load compliance rules from Supabase database.

        Args:
            document_id: Filter by specific document.
            item_type: Filter by item type (maps to category).
            language: Filter by language ('ko', 'en').
            compliance_id: ID for the created Compliance object.
            compliance_name: Name for the created Compliance object.

        Returns:
            Compliance object with rules from database.

        Raises:
            ValueError: If no items found.
        """
        from kompline.providers.supabase_provider import SupabaseProvider

        provider = SupabaseProvider()

        if document_id:
            rows = await provider.fetch_items_by_document(document_id, language)
        elif item_type:
            rows = await provider.fetch_items_by_type(item_type, language)
        else:
            rows = await provider.fetch_all_items(language)

        if not rows:
            raise ValueError("No compliance items found matching criteria")

        rules = provider.map_rows_to_rules(rows)
        first_row = rows[0]

        compliance = Compliance(
            id=compliance_id or f"supabase-{first_row.document_id}",
            name=compliance_name or first_row.document_title or "Supabase Compliance",
            version="db",
            jurisdiction="KR",
            scope=list({r.category.value for r in rules}),
            rules=rules,
            evidence_requirements=[],
            report_template="default",
            description=f"Loaded from Supabase: {first_row.document_title}",
            metadata={
                "source": "supabase",
                "document_id": first_row.document_id,
                "loaded_at": datetime.now().isoformat(),
                "item_count": len(rules),
            },
        )

        self.register_or_update(compliance)
        return compliance

    def load_from_supabase_sync(
        self,
        document_id: int | None = None,
        item_type: str | None = None,
        language: str | None = None,
        compliance_id: str | None = None,
        compliance_name: str | None = None,
    ) -> Compliance:
        """Synchronous wrapper for load_from_supabase."""
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(
                self.load_from_supabase(
                    document_id=document_id,
                    item_type=item_type,
                    language=language,
                    compliance_id=compliance_id,
                    compliance_name=compliance_name,
                )
            )
        finally:
            loop.close()

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
