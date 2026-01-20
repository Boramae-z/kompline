"""Artifact Registry tests."""

import pytest
from kompline.registry.artifact_registry import ArtifactRegistry
from kompline.models import ArtifactType, AccessMethod


class TestArtifactRegistry:
    """Artifact Registry unit tests."""

    def test_register_github_repository(self):
        """Test GitHub repository registration."""
        registry = ArtifactRegistry()
        artifact = registry.register_github_repository(
            github_url="https://github.com/example/repo",
            artifact_id="test-repo",
            name="Test Repository",
        )

        assert artifact.id == "test-repo"
        assert artifact.type == ArtifactType.CODE
        assert artifact.access_method == AccessMethod.GIT_CLONE
        assert "github.com" in artifact.locator

    def test_register_github_with_branch(self):
        """Test GitHub registration with branch."""
        registry = ArtifactRegistry()
        artifact = registry.register_github_repository(
            github_url="https://github.com/example/repo",
            artifact_id="test-repo-dev",
            branch="develop",
        )

        assert artifact.metadata.get("branch") == "develop"

    def test_register_github_with_file_patterns(self):
        """Test GitHub registration with file patterns."""
        registry = ArtifactRegistry()
        artifact = registry.register_github_repository(
            github_url="https://github.com/example/repo",
            artifact_id="test-repo",
            file_patterns=["*.py", "*.js"],
        )

        assert artifact.metadata.get("file_patterns") == ["*.py", "*.js"]

    def test_register_github_default_patterns(self):
        """Test GitHub registration uses default Python pattern."""
        registry = ArtifactRegistry()
        artifact = registry.register_github_repository(
            github_url="https://github.com/example/repo",
            artifact_id="test-repo",
        )

        assert artifact.metadata.get("file_patterns") == ["*.py"]
        assert artifact.metadata.get("source_type") == "github"

    def test_register_github_with_tags(self):
        """Test GitHub registration with custom tags."""
        registry = ArtifactRegistry()
        artifact = registry.register_github_repository(
            github_url="https://github.com/example/repo",
            artifact_id="test-repo",
            tags=["production", "python"],
        )

        assert "production" in artifact.tags
        assert "python" in artifact.tags

    def test_registered_github_can_be_retrieved(self):
        """Test registered GitHub artifact can be retrieved."""
        registry = ArtifactRegistry()
        registry.register_github_repository(
            github_url="https://github.com/example/repo",
            artifact_id="my-repo",
        )

        retrieved = registry.get("my-repo")
        assert retrieved is not None
        assert retrieved.id == "my-repo"
