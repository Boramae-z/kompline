"""Persistence helpers for audit requests (multi-file workflow) using Supabase REST API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from kompline.supabase_client import get_async_supabase_client


async def save_audit_request(
    request_id: str,
    name: str,
    description: str,
    status: str,
    compliance_ids: list[str],
    use_llm: bool = True,
    require_review: bool = True,
    submitted_at: datetime | None = None,
    completed_at: datetime | None = None,
    is_compliant: bool | None = None,
    total_passed: int = 0,
    total_failed: int = 0,
    total_review: int = 0,
    result_json: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    """Save or update an audit request."""
    client = await get_async_supabase_client()

    data = {
        "id": request_id,
        "name": name,
        "description": description,
        "status": status,
        "compliance_ids": compliance_ids,
        "use_llm": use_llm,
        "require_review": require_review,
        "submitted_at": submitted_at.isoformat() if submitted_at else None,
        "completed_at": completed_at.isoformat() if completed_at else None,
        "is_compliant": is_compliant,
        "total_passed": total_passed,
        "total_failed": total_failed,
        "total_review": total_review,
        "result_json": result_json,
        "error_message": error_message,
    }

    result = await client.table("audit_request").upsert(data).execute()
    return result.data[0] if result.data else data


async def get_audit_request(request_id: str) -> dict[str, Any] | None:
    """Get an audit request by ID, including its files."""
    client = await get_async_supabase_client()

    result = await client.table("audit_request").select("*").eq("id", request_id).execute()
    if not result.data:
        return None

    record = result.data[0]

    # Get associated files
    files_result = await client.table("audit_request_file").select("*").eq("audit_request_id", request_id).execute()
    file_records = files_result.data or []

    return _record_to_dict(record, file_records)


async def list_audit_requests(
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """List audit requests with optional filtering."""
    client = await get_async_supabase_client()

    # Build query
    query = client.table("audit_request").select("*", count="exact")
    if status:
        query = query.eq("status", status)

    # Apply ordering and pagination
    query = query.order("created_at", desc=True).range(offset, offset + limit - 1)

    result = await query.execute()
    records = result.data or []
    total = result.count or len(records)

    # Get files for each request
    requests = []
    for record in records:
        files_result = await client.table("audit_request_file").select("*").eq("audit_request_id", record["id"]).execute()
        file_records = files_result.data or []
        requests.append(_record_to_dict(record, file_records))

    return requests, total


async def delete_audit_request(request_id: str) -> bool:
    """Delete an audit request and its files."""
    client = await get_async_supabase_client()

    # Delete files first
    await client.table("audit_request_file").delete().eq("audit_request_id", request_id).execute()

    # Delete request
    result = await client.table("audit_request").delete().eq("id", request_id).execute()
    return len(result.data or []) > 0


async def save_audit_request_file(
    file_id: str,
    audit_request_id: str,
    filename: str,
    file_type: str,
    size: int,
    content: str,
) -> dict[str, Any]:
    """Save a file for an audit request."""
    client = await get_async_supabase_client()

    data = {
        "id": file_id,
        "audit_request_id": audit_request_id,
        "filename": filename,
        "file_type": file_type,
        "size": size,
        "content": content,
    }

    result = await client.table("audit_request_file").upsert(data).execute()
    return result.data[0] if result.data else data


async def get_audit_request_file(file_id: str) -> dict[str, Any] | None:
    """Get a file by ID."""
    client = await get_async_supabase_client()

    result = await client.table("audit_request_file").select("*").eq("id", file_id).execute()
    if not result.data:
        return None
    return _file_record_to_dict(result.data[0], include_content=True)


async def delete_audit_request_file(audit_request_id: str, file_id: str) -> bool:
    """Delete a file from an audit request."""
    client = await get_async_supabase_client()

    result = await client.table("audit_request_file").delete().eq("id", file_id).eq("audit_request_id", audit_request_id).execute()
    return len(result.data or []) > 0


async def get_audit_request_files(audit_request_id: str) -> list[dict[str, Any]]:
    """Get all files for an audit request (with content for processing)."""
    client = await get_async_supabase_client()

    result = await client.table("audit_request_file").select("*").eq("audit_request_id", audit_request_id).execute()
    return [_file_record_to_dict(r, include_content=True) for r in (result.data or [])]


async def update_audit_request_status(
    request_id: str,
    status: str,
    submitted_at: datetime | None = None,
    completed_at: datetime | None = None,
    is_compliant: bool | None = None,
    total_passed: int = 0,
    total_failed: int = 0,
    total_review: int = 0,
    result_json: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> bool:
    """Update audit request status and results."""
    client = await get_async_supabase_client()

    data: dict[str, Any] = {"status": status}
    if submitted_at is not None:
        data["submitted_at"] = submitted_at.isoformat()
    if completed_at is not None:
        data["completed_at"] = completed_at.isoformat()
    if is_compliant is not None:
        data["is_compliant"] = is_compliant
    data["total_passed"] = total_passed
    data["total_failed"] = total_failed
    data["total_review"] = total_review
    if result_json is not None:
        data["result_json"] = result_json
    if error_message is not None:
        data["error_message"] = error_message

    result = await client.table("audit_request").update(data).eq("id", request_id).execute()
    return len(result.data or []) > 0


def _record_to_dict(
    record: dict[str, Any],
    file_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Convert record to dict format expected by API."""
    return {
        "id": record["id"],
        "name": record["name"],
        "description": record.get("description", ""),
        "status": record["status"],
        "compliance_ids": record.get("compliance_ids", []),
        "use_llm": record.get("use_llm", True),
        "require_review": record.get("require_review", True),
        "files": [_file_record_to_dict(f) for f in file_records],
        "created_at": record.get("created_at"),
        "submitted_at": record.get("submitted_at"),
        "completed_at": record.get("completed_at"),
        "is_compliant": record.get("is_compliant"),
        "total_passed": record.get("total_passed", 0),
        "total_failed": record.get("total_failed", 0),
        "total_review": record.get("total_review", 0),
        "result": record.get("result_json"),
        "error": record.get("error_message"),
    }


def _file_record_to_dict(
    record: dict[str, Any],
    include_content: bool = False,
) -> dict[str, Any]:
    """Convert file record to dict."""
    d = {
        "id": record["id"],
        "filename": record["filename"],
        "file_type": record["file_type"],
        "size": record.get("size", 0),
        "uploaded_at": record.get("uploaded_at"),
    }
    if include_content:
        d["content"] = record.get("content", "")
    return d
