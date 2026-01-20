"""Supabase client for Kompline."""

from __future__ import annotations

from supabase import create_client, Client
from supabase._async.client import create_client as create_async_client, AsyncClient

from config.settings import settings

_client: Client | None = None
_async_client: AsyncClient | None = None


def get_supabase_client() -> Client:
    """Return a singleton Supabase client (sync)."""
    global _client
    if _client is None:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is not set")
        _client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
    return _client


async def get_async_supabase_client() -> AsyncClient:
    """Return a singleton Supabase client (async)."""
    global _async_client
    if _async_client is None:
        if not settings.supabase_url or not settings.supabase_service_role_key:
            raise RuntimeError("SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is not set")
        _async_client = await create_async_client(
            settings.supabase_url,
            settings.supabase_service_role_key,
        )
    return _async_client


async def ping_supabase() -> bool:
    """Return True if Supabase connection succeeds."""
    try:
        client = await get_async_supabase_client()
        # Simple query to test connection
        result = await client.table("audit_request").select("id").limit(1).execute()
        return True
    except Exception as e:
        print(f"Supabase ping failed: {e}")
        return False
