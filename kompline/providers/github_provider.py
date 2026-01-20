"""GitHub repository source code provider."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from typing import Any

import httpx


@dataclass
class GitHubFile:
    """GitHub file information."""

    path: str
    name: str
    content: str
    sha: str
    size: int
    url: str


@dataclass
class GitHubProvider:
    """GitHub API source code provider.

    Usage:
        provider = GitHubProvider(token="ghp_xxx")  # optional
        files = await provider.list_python_files("owner", "repo")
        content = await provider.get_file_content("owner", "repo", "src/main.py")
    """

    token: str | None = None
    base_url: str = "https://api.github.com"
    _client: httpx.AsyncClient | None = field(default=None, repr=False)

    def _get_headers(self) -> dict[str, str]:
        """Generate API request headers."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Kompline/1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def parse_github_url(self, url: str) -> tuple[str, str]:
        """Extract owner and repo from GitHub URL.

        Args:
            url: GitHub URL (https://github.com/owner/repo)

        Returns:
            (owner, repo) tuple

        Raises:
            ValueError: If URL is invalid
        """
        patterns = [
            r"github\.com/([^/]+)/([^/]+)",
            r"github\.com:([^/]+)/([^/]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                owner = match.group(1)
                repo = match.group(2).replace(".git", "")
                return owner, repo
        raise ValueError(f"Invalid GitHub URL: {url}")

    def is_python_file(self, path: str) -> bool:
        """Check if path is a Python file."""
        return path.endswith(".py")

    async def list_repository_files(
        self,
        owner: str,
        repo: str,
        path: str = "",
        branch: str = "main",
        recursive: bool = True,
    ) -> list[dict[str, Any]]:
        """List files in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            path: Start path (default: root)
            branch: Branch name
            recursive: Include subdirectories

        Returns:
            List of file information dicts
        """
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
            params = {"ref": branch}
            response = await client.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()

            items = response.json()
            if not isinstance(items, list):
                items = [items]

            files = []
            for item in items:
                if item["type"] == "file":
                    files.append(item)
                elif item["type"] == "dir" and recursive:
                    subfiles = await self.list_repository_files(
                        owner, repo, item["path"], branch, recursive
                    )
                    files.extend(subfiles)

            return files

    async def list_python_files(
        self,
        owner: str,
        repo: str,
        path: str = "",
        branch: str = "main",
    ) -> list[dict[str, Any]]:
        """List only Python files in a repository."""
        all_files = await self.list_repository_files(owner, repo, path, branch)
        return [f for f in all_files if self.is_python_file(f["path"])]

    async def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        branch: str = "main",
    ) -> GitHubFile:
        """Get file content.

        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            branch: Branch name

        Returns:
            GitHubFile object
        """
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
            params = {"ref": branch}
            response = await client.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()

            data = response.json()
            content = ""
            if data.get("encoding") == "base64" and data.get("content"):
                content = base64.b64decode(data["content"]).decode("utf-8")

            return GitHubFile(
                path=data["path"],
                name=data["name"],
                content=content,
                sha=data["sha"],
                size=data.get("size", 0),
                url=data.get("html_url", ""),
            )

    async def get_multiple_files(
        self,
        owner: str,
        repo: str,
        paths: list[str],
        branch: str = "main",
    ) -> list[GitHubFile]:
        """Get multiple file contents."""
        files = []
        for path in paths:
            try:
                file = await self.get_file_content(owner, repo, path, branch)
                files.append(file)
            except httpx.HTTPStatusError:
                continue  # Skip files not found
        return files
