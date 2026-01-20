"""Bootstrap helpers for loading registries from DB."""

from __future__ import annotations

from config.settings import settings


async def load_registries_from_db() -> None:
    """Load compliance and artifact registries from DB."""
    # Lazy import to avoid circular dependency
    from kompline.registry import get_artifact_registry, get_compliance_registry

    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not set")
    await get_compliance_registry().load_from_db()
    await get_artifact_registry().load_from_db()
