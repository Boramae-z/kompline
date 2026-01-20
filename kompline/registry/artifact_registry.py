"""Artifact Registry for managing audit targets."""

from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

from kompline.models import (
    AccessMethod,
    Artifact,
    ArtifactType,
    Provenance,
)
from kompline.supabase_client import get_async_supabase_client

def _parse_dt(value: Any):
    from datetime import datetime
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return datetime.now()
    return datetime.now()


class ArtifactRegistry:
    """Registry for artifacts (audit targets).

    Manages storing and retrieving artifact definitions.
    Supports programmatic registration and YAML loading.
    """

    def __init__(self):
        self._artifacts: dict[str, Artifact] = {}

    def register(self, artifact: Artifact) -> None:
        """Register an artifact.

        Args:
            artifact: The artifact to register.

        Raises:
            ValueError: If artifact with same ID already exists.
        """
        if artifact.id in self._artifacts:
            raise ValueError(f"Artifact '{artifact.id}' already registered")
        self._artifacts[artifact.id] = artifact

    def register_or_update(self, artifact: Artifact) -> None:
        """Register an artifact, updating if it exists."""
        self._artifacts[artifact.id] = artifact

    def get(self, artifact_id: str) -> Artifact | None:
        """Get an artifact by ID.

        Args:
            artifact_id: The artifact ID.

        Returns:
            The artifact, or None if not found.
        """
        return self._artifacts.get(artifact_id)

    def get_or_raise(self, artifact_id: str) -> Artifact:
        """Get an artifact by ID, raising if not found.

        Args:
            artifact_id: The artifact ID.

        Returns:
            The artifact.

        Raises:
            KeyError: If artifact not found.
        """
        if artifact_id not in self._artifacts:
            raise KeyError(f"Artifact '{artifact_id}' not found")
        return self._artifacts[artifact_id]

    def list_all(self) -> list[Artifact]:
        """List all registered artifacts."""
        return list(self._artifacts.values())

    def list_ids(self) -> list[str]:
        """List all artifact IDs."""
        return list(self._artifacts.keys())

    def filter_by_type(self, artifact_type: ArtifactType) -> list[Artifact]:
        """Get artifacts of a specific type."""
        return [a for a in self._artifacts.values() if a.type == artifact_type]

    def filter_by_tag(self, tag: str) -> list[Artifact]:
        """Get artifacts with a specific tag."""
        return [a for a in self._artifacts.values() if tag in a.tags]

    def unregister(self, artifact_id: str) -> bool:
        """Remove an artifact from the registry.

        Args:
            artifact_id: The artifact ID to remove.

        Returns:
            True if removed, False if not found.
        """
        if artifact_id in self._artifacts:
            del self._artifacts[artifact_id]
            return True
        return False

    def clear(self) -> None:
        """Clear all registered artifacts."""
        self._artifacts.clear()

    def register_file(
        self,
        file_path: str | Path,
        artifact_id: str | None = None,
        name: str | None = None,
        tags: list[str] | None = None,
    ) -> Artifact:
        """Register a local file as an artifact.

        Automatically determines artifact type from file extension.

        Args:
            file_path: Path to the file.
            artifact_id: Optional ID (defaults to filename).
            name: Optional human-readable name.
            tags: Optional tags for the artifact.

        Returns:
            The registered artifact.
        """
        path = Path(file_path)
        artifact_type = self._infer_type_from_extension(path.suffix)

        artifact = Artifact(
            id=artifact_id or path.stem,
            name=name or path.name,
            type=artifact_type,
            locator=str(path.absolute()),
            access_method=AccessMethod.FILE_READ,
            provenance=Provenance(
                source=str(path.absolute()),
                retrieved_at=datetime.now(),
            ),
            tags=tags or [],
        )

        self.register(artifact)
        return artifact

    def register_repository(
        self,
        repo_url: str,
        artifact_id: str,
        name: str | None = None,
        tags: list[str] | None = None,
    ) -> Artifact:
        """Register a git repository as an artifact.

        Args:
            repo_url: Git repository URL.
            artifact_id: ID for the artifact.
            name: Optional human-readable name.
            tags: Optional tags.

        Returns:
            The registered artifact.
        """
        artifact = Artifact(
            id=artifact_id,
            name=name or artifact_id,
            type=ArtifactType.CODE,
            locator=repo_url,
            access_method=AccessMethod.GIT_CLONE,
            tags=tags or [],
        )

        self.register(artifact)
        return artifact

    def register_github_repository(
        self,
        github_url: str,
        artifact_id: str,
        name: str | None = None,
        branch: str = "main",
        tags: list[str] | None = None,
        file_patterns: list[str] | None = None,
    ) -> Artifact:
        """Register a GitHub repository as an artifact.

        Args:
            github_url: GitHub repository URL.
            artifact_id: Artifact ID.
            name: Display name (optional).
            branch: Target branch (default: main).
            tags: Tag list.
            file_patterns: File patterns to include (default: *.py).

        Returns:
            Registered Artifact.
        """
        artifact = Artifact(
            id=artifact_id,
            name=name or artifact_id,
            type=ArtifactType.CODE,
            locator=github_url,
            access_method=AccessMethod.GIT_CLONE,
            provenance=Provenance(
                source=github_url,
                version=branch,
                retrieved_at=datetime.now(),
            ),
            tags=tags or ["github"],
            metadata={
                "branch": branch,
                "file_patterns": file_patterns or ["*.py"],
                "source_type": "github",
            },
        )

        self.register_or_update(artifact)
        return artifact

    def load_from_yaml(self, path: str | Path) -> Artifact:
        """Load an artifact definition from YAML.

        Args:
            path: Path to the YAML file.

        Returns:
            The loaded artifact.

        Raises:
            ImportError: If pyyaml is not installed.
        """
        if yaml is None:
            raise ImportError("pyyaml is required for YAML loading: pip install pyyaml")
        path = Path(path)
        with open(path) as f:
            data = yaml.safe_load(f)

        artifact = self._parse_artifact(data)
        self.register(artifact)
        return artifact

    async def load_from_db(self) -> list[Artifact]:
        """Load artifact definitions from DB using Supabase REST API."""
        self.clear()
        client = await get_async_supabase_client()

        result = await client.table("artifact").select("*").execute()
        artifacts = result.data or []

        loaded: list[Artifact] = []
        for rec in artifacts:
            provenance = None
            prov_data = rec.get("provenance")
            if prov_data:
                provenance = Provenance(
                    source=prov_data.get("source", ""),
                    version=prov_data.get("version"),
                    retrieved_at=_parse_dt(prov_data.get("retrieved_at")),
                    retrieved_by=prov_data.get("retrieved_by", "system"),
                    checksum=prov_data.get("checksum"),
                    metadata=prov_data.get("metadata", {}),
                )
            artifact = Artifact(
                id=rec["id"],
                name=rec["name"],
                type=ArtifactType(rec["type"]),
                locator=rec["locator"],
                access_method=AccessMethod(rec["access_method"]),
                description=rec.get("description") or "",
                extraction_schema=rec.get("extraction_schema") or {},
                provenance=provenance,
                tags=rec.get("tags") or [],
                metadata=rec.get("extra_data") or {},
            )
            self.register_or_update(artifact)
            loaded.append(artifact)

        return loaded

    def load_from_directory(self, directory: str | Path) -> list[Artifact]:
        """Load all artifact definitions from a directory.

        Args:
            directory: Directory containing YAML files.

        Returns:
            List of loaded artifacts.
        """
        directory = Path(directory)
        loaded = []
        for yaml_file in directory.glob("*.yaml"):
            artifact = self.load_from_yaml(yaml_file)
            loaded.append(artifact)
        for yml_file in directory.glob("*.yml"):
            artifact = self.load_from_yaml(yml_file)
            loaded.append(artifact)
        return loaded

    def _parse_artifact(self, data: dict[str, Any]) -> Artifact:
        """Parse artifact data from dictionary."""
        provenance_data = data.get("provenance", {})
        provenance = None
        if provenance_data:
            provenance = Provenance(
                source=provenance_data.get("source", ""),
                version=provenance_data.get("version"),
                checksum=provenance_data.get("checksum"),
                metadata=provenance_data.get("metadata", {}),
            )

        return Artifact(
            id=data["id"],
            name=data.get("name", data["id"]),
            type=ArtifactType(data.get("type", "code")),
            locator=data["locator"],
            access_method=AccessMethod(data.get("access_method", "file_read")),
            description=data.get("description", ""),
            extraction_schema=data.get("extraction_schema", {}),
            provenance=provenance,
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )

    def _infer_type_from_extension(self, extension: str) -> ArtifactType:
        """Infer artifact type from file extension."""
        extension = extension.lower()
        type_mapping = {
            ".py": ArtifactType.CODE,
            ".js": ArtifactType.CODE,
            ".ts": ArtifactType.CODE,
            ".java": ArtifactType.CODE,
            ".go": ArtifactType.CODE,
            ".rs": ArtifactType.CODE,
            ".pdf": ArtifactType.PDF,
            ".log": ArtifactType.LOG,
            ".yaml": ArtifactType.CONFIG,
            ".yml": ArtifactType.CONFIG,
            ".json": ArtifactType.CONFIG,
            ".toml": ArtifactType.CONFIG,
            ".ini": ArtifactType.CONFIG,
            ".md": ArtifactType.DOCUMENT,
            ".txt": ArtifactType.DOCUMENT,
        }
        return type_mapping.get(extension, ArtifactType.DOCUMENT)

    def __len__(self) -> int:
        return len(self._artifacts)

    def __contains__(self, artifact_id: str) -> bool:
        return artifact_id in self._artifacts


# Global registry instance
_default_registry: ArtifactRegistry | None = None


def get_artifact_registry() -> ArtifactRegistry:
    """Get the default artifact registry."""
    global _default_registry
    if _default_registry is None:
        _default_registry = ArtifactRegistry()
    return _default_registry
