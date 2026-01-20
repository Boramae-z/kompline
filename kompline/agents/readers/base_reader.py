"""Base Reader Agent for extracting evidence from artifacts."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agents import Agent

from kompline.models import (
    Artifact,
    ArtifactType,
    Evidence,
    EvidenceCollection,
    EvidenceRequirement,
    EvidenceType,
    Provenance,
)
from kompline.tracing.logger import log_agent_event


class BaseReader(ABC):
    """Abstract base class for Reader agents.

    Reader agents are responsible for extracting evidence from artifacts.
    Each reader specializes in a specific artifact type (code, PDF, etc.).
    """

    # Artifact types this reader can handle
    supported_types: list[ArtifactType] = []

    def __init__(self, name: str):
        """Initialize the reader.

        Args:
            name: Name of the reader agent.
        """
        self.name = name
        self._agent: "Agent | None" = None

    @property
    def agent(self) -> "Agent":
        """Get or create the underlying agent."""
        if self._agent is None:
            self._agent = self._create_agent()
            log_agent_event("init", self.name.lower(), f"{self.name} Agent initialized")
        return self._agent

    @abstractmethod
    def _create_agent(self) -> "Agent":
        """Create the underlying Agent instance.

        Returns:
            Configured Agent for this reader.
        """
        pass

    @abstractmethod
    def _get_instructions(self) -> str:
        """Get the agent instructions.

        Returns:
            Instructions string for the agent.
        """
        pass

    @abstractmethod
    def _get_tools(self) -> list:
        """Get the tools for this reader.

        Returns:
            List of function tools for evidence extraction.
        """
        pass

    def can_read(self, artifact: Artifact) -> bool:
        """Check if this reader can handle the given artifact.

        Args:
            artifact: The artifact to check.

        Returns:
            True if this reader can handle the artifact type.
        """
        return artifact.type in self.supported_types

    @abstractmethod
    async def extract_evidence(
        self,
        artifact: Artifact,
        requirements: list[EvidenceRequirement],
        relation_id: str,
    ) -> EvidenceCollection:
        """Extract evidence from an artifact.

        Args:
            artifact: The artifact to read.
            requirements: Evidence requirements to satisfy.
            relation_id: The audit relation ID for tracking.

        Returns:
            Collection of extracted evidence.
        """
        pass

    def _create_evidence(
        self,
        relation_id: str,
        source: str,
        evidence_type: EvidenceType,
        content: str,
        provenance: Provenance,
        **kwargs: Any,
    ) -> Evidence:
        """Helper to create Evidence with consistent ID generation.

        Args:
            relation_id: The audit relation ID.
            source: Source of the evidence.
            evidence_type: Type of evidence.
            content: The evidence content.
            provenance: Provenance information.
            **kwargs: Additional evidence fields.

        Returns:
            New Evidence instance.
        """
        import uuid

        return Evidence(
            id=f"ev-{uuid.uuid4().hex[:8]}",
            relation_id=relation_id,
            source=source,
            type=evidence_type,
            content=content,
            provenance=provenance,
            collected_by=self.name,
            **kwargs,
        )


def get_reader_for_artifact(artifact: Artifact) -> BaseReader | None:
    """Get the appropriate reader for an artifact.

    Args:
        artifact: The artifact to read.

    Returns:
        A reader that can handle the artifact, or None.
    """
    # Import here to avoid circular imports
    from kompline.agents.readers.code_reader import CodeReader
    from kompline.agents.readers.config_reader import ConfigReader
    from kompline.agents.readers.pdf_reader import PDFReader

    readers: list[BaseReader] = [
        CodeReader(),
        PDFReader(),
        ConfigReader(),
    ]

    for reader in readers:
        if reader.can_read(artifact):
            return reader

    return None
