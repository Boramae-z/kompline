"""Artifact models representing audit targets."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ArtifactType(str, Enum):
    """Type of artifact being audited."""

    CODE = "code"  # Source code (Python, JS, etc.)
    PDF = "pdf"  # PDF documents
    LOG = "log"  # Log files
    DATABASE = "database"  # Database/query results
    CONFIG = "config"  # Configuration files (YAML, JSON, etc.)
    API = "api"  # API specifications/responses
    DOCUMENT = "document"  # General documents (markdown, text)


class AccessMethod(str, Enum):
    """Method used to access the artifact."""

    FILE_READ = "file_read"  # Local file system
    GIT_CLONE = "git_clone"  # Git repository
    API_CALL = "api_call"  # HTTP API
    DB_QUERY = "db_query"  # Database query
    S3_FETCH = "s3_fetch"  # S3/cloud storage


@dataclass
class Provenance:
    """Provenance information for traceability.

    Tracks the origin and version of artifacts and evidence.
    """

    source: str  # Original source (file path, URL, etc.)
    version: str | None = None  # Git commit, file hash, version number
    retrieved_at: datetime = field(default_factory=datetime.now)
    retrieved_by: str = "system"  # Agent or user who retrieved
    checksum: str | None = None  # SHA256 or similar
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Artifact:
    """An artifact to be audited.

    Examples:
    - A Python code repository
    - A PDF regulation document
    - Database query results
    - Configuration files
    """

    id: str  # e.g., "user-service-repo", "deposit-algorithm"
    name: str  # Human-readable name
    type: ArtifactType
    locator: str  # How to find it: "github://org/repo", "/path/to/file"
    access_method: AccessMethod
    description: str = ""
    extraction_schema: dict[str, Any] = field(default_factory=dict)  # What to extract
    provenance: Provenance | None = None
    tags: list[str] = field(default_factory=list)  # For filtering/grouping
    metadata: dict[str, Any] = field(default_factory=dict)

    def with_provenance(self, provenance: Provenance) -> "Artifact":
        """Return a copy with updated provenance."""
        return Artifact(
            id=self.id,
            name=self.name,
            type=self.type,
            locator=self.locator,
            access_method=self.access_method,
            description=self.description,
            extraction_schema=self.extraction_schema,
            provenance=provenance,
            tags=self.tags,
            metadata=self.metadata,
        )

    @property
    def is_code(self) -> bool:
        """Check if artifact is source code."""
        return self.type == ArtifactType.CODE

    @property
    def is_document(self) -> bool:
        """Check if artifact is a document (PDF or general)."""
        return self.type in (ArtifactType.PDF, ArtifactType.DOCUMENT)
