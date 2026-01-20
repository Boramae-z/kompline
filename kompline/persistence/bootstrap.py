"""Bootstrap helpers for loading registries from DB using Supabase REST API."""

from __future__ import annotations

from config.settings import settings


async def load_registries_from_db() -> None:
    """Load compliance and artifact registries from DB."""
    # Lazy import to avoid circular dependency
    from kompline.registry import get_artifact_registry, get_compliance_registry

    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is not set")
    await get_compliance_registry().load_from_db()
    await get_artifact_registry().load_from_db()
