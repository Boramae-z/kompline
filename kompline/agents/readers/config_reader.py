"""Config Reader Agent for extracting evidence from configuration files."""

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

try:
    from agents import function_tool
except ImportError:
    def function_tool(func):
        func.func = func
        return func

if TYPE_CHECKING:
    from agents import Agent

from kompline.agents.readers.base_reader import BaseReader
from kompline.models import (
    Artifact,
    ArtifactType,
    EvidenceCollection,
    EvidenceRequirement,
    EvidenceType,
    Provenance,
)

# Optional YAML support
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

# Optional TOML support (Python 3.11+)
try:
    import tomllib
    HAS_TOML = True
except ImportError:
    try:
        import tomli as tomllib
        HAS_TOML = True
    except ImportError:
        HAS_TOML = False


CONFIG_READER_INSTRUCTIONS = """You are the Config Reader Agent for Kompline.

Your role is to extract evidence from configuration files for compliance auditing.
This includes YAML, JSON, TOML, and INI files.

## What to Extract

Based on evidence requirements, extract:
1. **Configuration values**: Specific settings and their values
2. **Weight/factor configurations**: Any numerical weights or factors
3. **Feature flags**: Toggles that might affect behavior
4. **API keys/secrets**: Identify (but don't expose) sensitive data

## Tools Available

- `parse_config_file`: Parse and extract config values
- `search_config_keys`: Search for specific configuration keys
- `get_config_value`: Get a specific configuration value by path

## Output Format

For each piece of evidence, provide:
- Configuration file path
- Key path (e.g., "ranking.weights.interest_rate")
- The value
- Why this is relevant to the compliance check

## Important Guidelines

- Include full key paths for all findings
- Note the data types of values
- Flag any suspicious configuration patterns
- Identify both documented AND undocumented settings
"""


@function_tool
def parse_config_file(file_path: str) -> dict[str, Any]:
    """Parse a configuration file and return its contents.

    Supports JSON, YAML, and TOML formats.

    Args:
        file_path: Path to the configuration file.

    Returns:
        Dictionary with parsed configuration.
    """
    path = Path(file_path)
    if not path.exists():
        return {"success": False, "error": f"File not found: {file_path}"}

    suffix = path.suffix.lower()
    content = path.read_text()

    try:
        if suffix == ".json":
            data = json.loads(content)
        elif suffix in (".yaml", ".yml"):
            if not HAS_YAML:
                return {"success": False, "error": "pyyaml not installed"}
            data = yaml.safe_load(content)
        elif suffix == ".toml":
            if not HAS_TOML:
                return {"success": False, "error": "tomllib/tomli not installed"}
            data = tomllib.loads(content)
        else:
            # Try to parse as JSON first, then YAML
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                if HAS_YAML:
                    data = yaml.safe_load(content)
                else:
                    return {"success": False, "error": f"Unknown format: {suffix}"}

        return {"success": True, "data": data, "format": suffix}
    except Exception as e:
        return {"success": False, "error": str(e)}


@function_tool
def search_config_keys(file_path: str, search_term: str) -> dict[str, Any]:
    """Search for keys containing a term in configuration.

    Args:
        file_path: Path to the configuration file.
        search_term: Term to search for in key names.

    Returns:
        Dictionary with matching keys and their values.
    """
    result = parse_config_file.func(file_path)
    if not result.get("success"):
        return result

    matches = []
    data = result.get("data", {})

    def search_recursive(obj: Any, path: str = "") -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                if search_term.lower() in key.lower():
                    matches.append({"path": current_path, "value": value})
                search_recursive(value, current_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                search_recursive(item, f"{path}[{i}]")

    search_recursive(data)

    return {"success": True, "search_term": search_term, "matches": matches}


@function_tool
def get_config_value(file_path: str, key_path: str) -> dict[str, Any]:
    """Get a specific configuration value by its path.

    Args:
        file_path: Path to the configuration file.
        key_path: Dot-separated path to the value (e.g., "ranking.weights.interest_rate").

    Returns:
        Dictionary with the value.
    """
    result = parse_config_file.func(file_path)
    if not result.get("success"):
        return result

    data = result.get("data", {})
    keys = key_path.split(".")

    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return {"success": False, "error": f"Key not found: {key_path}"}

    return {"success": True, "path": key_path, "value": current}


class ConfigReader(BaseReader):
    """Reader agent for configuration file artifacts."""

    supported_types = [ArtifactType.CONFIG]

    def __init__(self):
        super().__init__("ConfigReader")

    def _get_instructions(self) -> str:
        return CONFIG_READER_INSTRUCTIONS

    def _get_tools(self) -> list:
        return [parse_config_file, search_config_keys, get_config_value]

    def _create_agent(self) -> "Agent":
        from agents import Agent
        return Agent(
            name=self.name,
            instructions=self._get_instructions(),
            tools=self._get_tools(),
        )

    async def extract_evidence(
        self,
        artifact: Artifact,
        requirements: list[EvidenceRequirement],
        relation_id: str,
    ) -> EvidenceCollection:
        """Extract evidence from configuration file.

        Args:
            artifact: The config artifact to read.
            requirements: Evidence requirements to satisfy.
            relation_id: The audit relation ID.

        Returns:
            Collection of extracted evidence.
        """
        collection = EvidenceCollection(relation_id=relation_id)

        source_path = Path(artifact.locator)
        if not source_path.exists():
            return collection

        provenance = Provenance(
            source=str(source_path),
            retrieved_by=self.name,
        )

        # Parse the configuration
        result = parse_config_file.func(str(source_path))

        if not result.get("success"):
            return collection

        data = result.get("data", {})

        # Create evidence for the full config structure
        evidence = self._create_evidence(
            relation_id=relation_id,
            source=str(source_path),
            evidence_type=EvidenceType.CONFIG_VALUE,
            content=json.dumps(data, indent=2, default=str)[:2000],
            provenance=provenance,
            metadata={"format": result.get("format"), "structure": "full"},
        )
        collection.add(evidence)

        # Search for requirement-specific content
        for req in requirements:
            # Extract keywords from requirement
            keywords = self._extract_keywords(req.description)
            for keyword in keywords:
                search_result = search_config_keys.func(str(source_path), keyword)
                if search_result.get("success"):
                    for match in search_result.get("matches", []):
                        evidence = self._create_evidence(
                            relation_id=relation_id,
                            source=str(source_path),
                            evidence_type=EvidenceType.CONFIG_VALUE,
                            content=f"{match['path']} = {json.dumps(match['value'], default=str)}",
                            provenance=provenance,
                            metadata={
                                "key_path": match["path"],
                                "value": match["value"],
                                "search_term": keyword,
                            },
                        )
                        evidence.rule_ids = [req.id]
                        collection.add(evidence)

        # Look for common compliance-relevant patterns
        self._extract_weight_configs(data, "", collection, relation_id, str(source_path), provenance)

        return collection

    def _extract_keywords(self, description: str) -> list[str]:
        """Extract search keywords from a requirement description."""
        keywords = []
        important_terms = [
            "weight", "factor", "score", "rank", "priority",
            "threshold", "limit", "max", "min", "rate",
            "affiliate", "sponsor", "preferred", "boost",
        ]

        desc_lower = description.lower()
        for term in important_terms:
            if term in desc_lower:
                keywords.append(term)

        return keywords[:5]

    def _extract_weight_configs(
        self,
        data: Any,
        path: str,
        collection: EvidenceCollection,
        relation_id: str,
        source: str,
        provenance: Provenance,
    ) -> None:
        """Recursively extract weight/factor configurations."""
        weight_keywords = ["weight", "factor", "score", "priority", "boost", "rate"]

        if isinstance(data, dict):
            for key, value in data.items():
                current_path = f"{path}.{key}" if path else key
                key_lower = key.lower()

                # Check if key suggests weight/factor
                if any(kw in key_lower for kw in weight_keywords):
                    evidence = self._create_evidence(
                        relation_id=relation_id,
                        source=source,
                        evidence_type=EvidenceType.CONFIG_VALUE,
                        content=f"{current_path} = {json.dumps(value, default=str)}",
                        provenance=provenance,
                        metadata={
                            "key_path": current_path,
                            "value": value,
                            "category": "weight_factor",
                        },
                    )
                    collection.add(evidence)

                # Recurse
                self._extract_weight_configs(
                    value, current_path, collection, relation_id, source, provenance
                )
        elif isinstance(data, list):
            for i, item in enumerate(data):
                self._extract_weight_configs(
                    item, f"{path}[{i}]", collection, relation_id, source, provenance
                )
