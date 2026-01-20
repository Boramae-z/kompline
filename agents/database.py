from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from supabase import Client, create_client

from agents.config import SUPABASE_KEY, SUPABASE_URL


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class DatabaseClient:
    client: Client

    @classmethod
    def from_env(cls) -> "DatabaseClient":
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError("Supabase is not configured")
        return cls(create_client(SUPABASE_URL, SUPABASE_KEY))

    def list_queued_scans(self, limit: int = 10) -> List[Dict[str, Any]]:
        response = (
            self.client.table("scans")
            .select("*")
            .eq("status", "QUEUED")
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return response.data or []

    def get_scan(self, scan_id: str) -> Optional[Dict[str, Any]]:
        response = self.client.table("scans").select("*").eq("id", scan_id).limit(1).execute()
        if response.data:
            return response.data[0]
        return None

    def get_scan_documents(self, scan_id: str) -> List[str]:
        response = (
            self.client.table("scan_documents")
            .select("document_id")
            .eq("scan_id", scan_id)
            .execute()
        )
        return [row["document_id"] for row in (response.data or [])]

    def get_compliance_items(self, document_ids: Iterable[str]) -> List[Dict[str, Any]]:
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

    def get_compliance_item(self, compliance_item_id: int) -> Optional[Dict[str, Any]]:
        response = (
            self.client.table("compliance_items")
            .select("id, document_id, item_text, item_type, section, page")
            .eq("id", compliance_item_id)
            .limit(1)
            .execute()
        )
        if response.data:
            return response.data[0]
        return None

    def create_scan_results(self, scan_id: str, compliance_items: Iterable[Dict[str, Any]]) -> int:
        rows: List[Dict[str, Any]] = []
        for item in compliance_items:
            rows.append(
                {
                    "scan_id": scan_id,
                    "compliance_item_id": item["id"],
                    "status": "PENDING",
                    "reasoning": None,
                    "evidence": None,
                    "updated_at": _utc_now_iso(),
                }
            )
        if not rows:
            return 0
        self.client.table("scan_results").insert(rows).execute()
        return len(rows)

    def update_scan_status(
        self,
        scan_id: str,
        status: str,
        report_url: Optional[str] = None,
        report_markdown: Optional[str] = None,
    ) -> None:
        payload: Dict[str, Any] = {"status": status}
        if report_url is not None:
            payload["report_url"] = report_url
        if report_markdown is not None:
            payload["report_markdown"] = report_markdown
        self.client.table("scans").update(payload).eq("id", scan_id).execute()

    def list_pending_results(self, limit: int = 1) -> List[Dict[str, Any]]:
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
        reasoning: Optional[str],
        evidence: Optional[str],
    ) -> None:
        payload = {
            "status": status,
            "reasoning": reasoning,
            "evidence": evidence,
            "updated_at": _utc_now_iso(),
        }
        self.client.table("scan_results").update(payload).eq("id", result_id).execute()

    def list_active_scans(self, statuses: Iterable[str]) -> List[Dict[str, Any]]:
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

    def list_scan_results(self, scan_id: str) -> List[Dict[str, Any]]:
        response = (
            self.client.table("scan_results")
            .select("*")
            .eq("scan_id", scan_id)
            .execute()
        )
        return response.data or []

    def count_pending_results(self, scan_id: str) -> int:
        response = (
            self.client.table("scan_results")
            .select("id", count="exact")
            .eq("scan_id", scan_id)
            .eq("status", "PENDING")
            .execute()
        )
        return response.count or 0
