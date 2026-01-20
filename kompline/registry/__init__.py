"""Registries for managing compliance and artifact definitions."""

from kompline.registry.artifact_registry import (
    ArtifactRegistry,
    get_artifact_registry,
)
from kompline.registry.compliance_registry import (
    ComplianceRegistry,
    get_compliance_registry,
)

__all__ = [
    "ComplianceRegistry",
    "get_compliance_registry",
    "ArtifactRegistry",
    "get_artifact_registry",
]
