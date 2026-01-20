"""Database helpers for Kompline (Supabase REST API)."""

from __future__ import annotations

from kompline.supabase_client import get_async_supabase_client, ping_supabase


async def ping_db() -> bool:
    """Return True if database connection succeeds."""
    return await ping_supabase()


# Legacy exports for compatibility (no longer used with Supabase REST API)
def get_async_engine():
    """Legacy function - not used with Supabase REST API."""
    raise NotImplementedError("Direct SQL engine not available with Supabase REST API")


def get_sessionmaker():
    """Legacy function - not used with Supabase REST API."""
    raise NotImplementedError("Direct SQL sessions not available with Supabase REST API")
