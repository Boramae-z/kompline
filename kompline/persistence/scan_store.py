"""Scan persistence for worker-based architecture."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from supabase import Client


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ScanStore:
    """Supabase-backed store for scan operations."""

    client: Client

    def list_queued_scans(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get scans waiting to be processed."""
        response = (
            self.client.table("scans")
            .select("*")
            .eq("status", "QUEUED")
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return response.data or []

    def get_scan(self, scan_id: str) -> dict[str, Any] | None:
        """Get a single scan by ID."""
        response = (
            self.client.table("scans")
            .select("*")
            .eq("id", scan_id)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def get_scan_documents(self, scan_id: str) -> list[str]:
        """Get document IDs linked to a scan."""
        response = (
            self.client.table("scan_documents")
            .select("document_id")
            .eq("scan_id", scan_id)
            .execute()
        )
        return [row["document_id"] for row in (response.data or [])]

    def create_scan_results(
        self,
        scan_id: str,
        compliance_items: Iterable[dict[str, Any]]
    ) -> int:
        """Create pending scan results for each compliance item."""
        rows = [
            {
                "scan_id": scan_id,
                "compliance_item_id": item["id"],
                "status": "PENDING",
                "updated_at": _utc_now_iso(),
            }
            for item in compliance_items
        ]
        if not rows:
            return 0
        self.client.table("scan_results").insert(rows).execute()
        return len(rows)

    def update_scan_status(
        self,
        scan_id: str,
        status: str,
        report_url: str | None = None,
        report_markdown: str | None = None,
    ) -> None:
        """Update scan status and optional report fields."""
        payload: dict[str, Any] = {"status": status}
        if report_url is not None:
            payload["report_url"] = report_url
        if report_markdown is not None:
            payload["report_markdown"] = report_markdown
        self.client.table("scans").update(payload).eq("id", scan_id).execute()

    def list_pending_results(self, limit: int = 1) -> list[dict[str, Any]]:
        """Get pending scan results for processing."""
        response = (
            self.client.table("scan_results")
            .select("*")
            .eq("status", "PENDING")
            .order("updated_at", desc=False)
            .limit(limit)
            .execute()
        )
        return response.data or []

    def update_scan_result(
        self,
        result_id: str,
        status: str,
        reasoning: str | None,
        evidence: str | None,
        worker_id: str | None = None,
    ) -> None:
        """Update a scan result with validation outcome."""
        payload = {
            "status": status,
            "reasoning": reasoning,
            "evidence": evidence,
            "updated_at": _utc_now_iso(),
        }
        if worker_id:
            payload["worker_id"] = worker_id
        self.client.table("scan_results").update(payload).eq("id", result_id).execute()

    def list_active_scans(self, statuses: Iterable[str]) -> list[dict[str, Any]]:
        """Get scans in specified statuses."""
        status_list = list(statuses)
        if not status_list:
            return []
        response = (
            self.client.table("scans")
            .select("*")
            .in_("status", status_list)
            .order("created_at", desc=False)
            .execute()
        )
        return response.data or []

    def list_scan_results(self, scan_id: str) -> list[dict[str, Any]]:
        """Get all results for a scan."""
        response = (
            self.client.table("scan_results")
            .select("*")
            .eq("scan_id", scan_id)
            .execute()
        )
        return response.data or []

    def count_pending_results(self, scan_id: str) -> int:
        """Count pending results for a scan."""
        response = (
            self.client.table("scan_results")
            .select("id", count="exact")
            .eq("scan_id", scan_id)
            .eq("status", "PENDING")
            .execute()
        )
        return response.count or 0

    def get_compliance_items(self, document_ids: Iterable[str]) -> list[dict[str, Any]]:
        """Get compliance items for given documents."""
        ids = list(document_ids)
        if not ids:
            return []
        response = (
            self.client.table("compliance_items")
            .select("id, document_id, item_text, item_type, section, page")
            .in_("document_id", ids)
            .execute()
        )
        return response.data or []

    def get_compliance_item(self, compliance_item_id: int) -> dict[str, Any] | None:
        """Get a single compliance item by ID."""
        response = (
            self.client.table("compliance_items")
            .select("id, document_id, item_text, item_type, section, page")
            .eq("id", compliance_item_id)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def create_scan(self, repo_url: str, document_ids: list[str]) -> str:
        """Create a new scan and link documents."""
        # Insert scan
        response = (
            self.client.table("scans")
            .insert({"repo_url": repo_url, "status": "QUEUED"})
            .execute()
        )
        scan_id = response.data[0]["id"]

        # Link documents
        if document_ids:
            rows = [{"scan_id": scan_id, "document_id": doc_id} for doc_id in document_ids]
            self.client.table("scan_documents").insert(rows).execute()

        return scan_id
