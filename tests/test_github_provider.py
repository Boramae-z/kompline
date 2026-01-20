"""GitHub Provider tests."""

import pytest
from kompline.providers.github_provider import GitHubProvider, GitHubFile


class TestGitHubProvider:
    """GitHub Provider unit tests."""

    def test_parse_github_url_https(self):
        """Test HTTPS URL parsing."""
        provider = GitHubProvider()
        owner, repo = provider.parse_github_url("https://github.com/owner/repo")
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_github_url_with_path(self):
        """Test URL parsing with path."""
        provider = GitHubProvider()
        owner, repo = provider.parse_github_url("https://github.com/owner/repo/tree/main/src")
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_github_url_with_git_suffix(self):
        """Test URL parsing with .git suffix."""
        provider = GitHubProvider()
        owner, repo = provider.parse_github_url("https://github.com/owner/repo.git")
        assert owner == "owner"
        assert repo == "repo"

    def test_parse_github_url_invalid(self):
        """Test invalid URL raises ValueError."""
        provider = GitHubProvider()
        with pytest.raises(ValueError):
            provider.parse_github_url("https://gitlab.com/owner/repo")

    def test_is_python_file(self):
        """Test Python file filtering."""
        provider = GitHubProvider()
        assert provider.is_python_file("main.py") is True
        assert provider.is_python_file("test.js") is False
        assert provider.is_python_file("README.md") is False
        assert provider.is_python_file("src/utils/helpers.py") is True

    def test_github_file_dataclass(self):
        """Test GitHubFile dataclass."""
        file = GitHubFile(
            path="src/main.py",
            name="main.py",
            content="print('hello')",
            sha="abc123",
            size=15,
            url="https://github.com/owner/repo/blob/main/src/main.py",
        )
        assert file.path == "src/main.py"
        assert file.name == "main.py"
        assert file.content == "print('hello')"

    def test_get_headers_without_token(self):
        """Test headers generation without token."""
        provider = GitHubProvider()
        headers = provider._get_headers()
        assert "Authorization" not in headers
        assert headers["Accept"] == "application/vnd.github.v3+json"

    def test_get_headers_with_token(self):
        """Test headers generation with token."""
        provider = GitHubProvider(token="ghp_test123")
        headers = provider._get_headers()
        assert headers["Authorization"] == "Bearer ghp_test123"
