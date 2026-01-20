from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from agents.config import REPO_CACHE_DIR, REPO_CLONE_DEPTH

logger = logging.getLogger("agents.git_loader")


def _is_local_path(repo_url: str) -> bool:
    path = Path(repo_url)
    return path.exists()


class GitLoader:
    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        self.cache_dir = cache_dir or REPO_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def load(self, repo_url: str) -> Path:
        if _is_local_path(repo_url):
            return Path(repo_url)
        return self._clone(repo_url)

    def _clone(self, repo_url: str) -> Path:
        target = self.cache_dir / self._safe_repo_name(repo_url)
        if target.exists():
            return target
        target.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Cloning repo %s -> %s", repo_url, target)
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                str(REPO_CLONE_DEPTH),
                repo_url,
                str(target),
            ],
            check=True,
        )
        return target

    @staticmethod
    def _safe_repo_name(repo_url: str) -> str:
        cleaned = repo_url.replace("://", "_").replace("/", "_").replace(":", "_")
        return cleaned.strip("_")

    def clear_cache(self) -> None:
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
