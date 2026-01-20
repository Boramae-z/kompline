"""Supabase database provider for compliance items using REST API."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import httpx

from kompline.models import (
    EvidenceRequirement,
    Rule,
    RuleCategory,
    RuleSeverity,
)


class SupabaseConnectionError(Exception):
    """Raised when Supabase connection fails."""

    pass


class ComplianceItemNotFoundError(Exception):
    """Raised when no compliance items match criteria."""

    pass


@dataclass
class ComplianceItemRow:
    """Row from compliance_items table."""

    id: int
    document_id: int
    document_title: str | None
    item_index: int
    item_type: str
    item_text: str
    page: int | None
    section: str | None
    item_json: dict[str, Any] | None
    language: str | None
    created_at: datetime


class SupabaseProvider:
    """Provider for fetching compliance items from Supabase via REST API."""

    ITEM_TYPE_MAPPING: dict[str, RuleCategory] = {
        "algorithm_fairness": RuleCategory.ALGORITHM_FAIRNESS,
        "fairness": RuleCategory.ALGORITHM_FAIRNESS,
        "data_handling": RuleCategory.DATA_HANDLING,
        "transparency": RuleCategory.TRANSPARENCY,
        "disclosure": RuleCategory.DISCLOSURE,
        "privacy": RuleCategory.PRIVACY,
        "security": RuleCategory.SECURITY,
    }

    def __init__(
        self,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        cache_ttl_seconds: int = 300,
    ):
        self._url = supabase_url or os.getenv("SUPABASE_URL")
        self._key = supabase_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not self._url or not self._key:
            raise SupabaseConnectionError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"
            )

        self._rest_url = f"{self._url}/rest/v1"
        self._cache: dict[str, tuple[datetime, Any]] = {}
        self._cache_ttl = timedelta(seconds=cache_ttl_seconds)

    def _get_headers(self) -> dict[str, str]:
        return {
            "apikey": self._key,
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def _cache_key(self, method: str, **kwargs) -> str:
        params_str = "&".join(f"{k}={v}" for k, v in sorted(kwargs.items()) if v is not None)
        return hashlib.md5(f"{method}:{params_str}".encode()).hexdigest()

    def _get_cached(self, key: str) -> Any | None:
        if key in self._cache:
            cached_at, value = self._cache[key]
            if datetime.now() - cached_at < self._cache_ttl:
                return value
            del self._cache[key]
        return None

    def _set_cached(self, key: str, value: Any) -> None:
        self._cache[key] = (datetime.now(), value)

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()

    async def _execute_query(
        self,
        table: str,
        params: dict[str, str] | None = None,
        max_retries: int = 3,
    ) -> list[dict[str, Any]]:
        url = f"{self._rest_url}/{table}"
        headers = self._get_headers()

        last_error = None
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        url,
                        headers=headers,
                        params=params,
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    return response.json()
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code >= 500:
                    continue
                raise SupabaseConnectionError(f"HTTP {e.response.status_code}: {e.response.text}")
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    continue

        raise SupabaseConnectionError(
            f"Failed to connect after {max_retries} attempts: {last_error}"
        )

    def _row_to_item(self, row: dict[str, Any]) -> ComplianceItemRow:
        created_at = row.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))

        return ComplianceItemRow(
            id=row["id"],
            document_id=row["document_id"],
            document_title=row.get("document_title"),
            item_index=row["item_index"],
            item_type=row["item_type"],
            item_text=row["item_text"],
            page=row.get("page"),
            section=row.get("section"),
            item_json=row.get("item_json"),
            language=row.get("language"),
            created_at=created_at or datetime.now(),
        )

    async def fetch_items_by_document(
        self, document_id: int, language: str | None = None
    ) -> list[ComplianceItemRow]:
        """Fetch compliance items by document ID."""
        cache_key = self._cache_key("by_doc", document_id=document_id, language=language)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        params = {
            "document_id": f"eq.{document_id}",
            "order": "item_index",
        }
        if language:
            params["language"] = f"eq.{language}"

        rows = await self._execute_query("compliance_items", params)
        items = [self._row_to_item(r) for r in rows]
        self._set_cached(cache_key, items)
        return items

    async def fetch_items_by_type(
        self, item_type: str, language: str | None = None
    ) -> list[ComplianceItemRow]:
        """Fetch compliance items by item type."""
        cache_key = self._cache_key("by_type", item_type=item_type, language=language)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        params = {
            "item_type": f"eq.{item_type}",
            "order": "document_id,item_index",
        }
        if language:
            params["language"] = f"eq.{language}"

        rows = await self._execute_query("compliance_items", params)
        items = [self._row_to_item(r) for r in rows]
        self._set_cached(cache_key, items)
        return items

    async def fetch_all_items(
        self, language: str | None = None
    ) -> list[ComplianceItemRow]:
        """Fetch all compliance items."""
        cache_key = self._cache_key("all", language=language)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        params = {"order": "document_id,item_index"}
        if language:
            params["language"] = f"eq.{language}"

        rows = await self._execute_query("compliance_items", params)
        items = [self._row_to_item(r) for r in rows]
        self._set_cached(cache_key, items)
        return items

    async def fetch_document_metadata(
        self, document_id: int
    ) -> dict[str, Any] | None:
        """Fetch document metadata by ID."""
        params = {"id": f"eq.{document_id}"}
        rows = await self._execute_query("documents", params)
        return rows[0] if rows else None

    def map_item_type_to_category(self, item_type: str) -> RuleCategory:
        """Map item type string to RuleCategory enum."""
        return self.ITEM_TYPE_MAPPING.get(
            item_type.lower(), RuleCategory.ALGORITHM_FAIRNESS
        )

    def _extract_check_points(self, text: str) -> list[str]:
        """Extract check points from text with bullets or numbers."""
        lines = text.strip().split("\n")
        points = []
        for line in lines:
            line = line.strip()
            if line and (
                line.startswith(("-", "*", "•"))
                or (len(line) > 1 and line[0].isdigit() and "." in line[:3])
            ):
                cleaned = line.lstrip("-*•0123456789. ")
                if cleaned:
                    points.append(cleaned)
        return points if points else [text[:200]]

    def map_row_to_rule(self, row: ComplianceItemRow) -> Rule:
        """Map a ComplianceItemRow to a Rule object."""
        json_data = row.item_json or {}

        rule_id = json_data.get("rule_id") or f"DB-{row.document_id}-{row.item_index:03d}"

        check_points = json_data.get("check_points", [])
        if not check_points and row.item_text:
            check_points = self._extract_check_points(row.item_text)

        severity_str = json_data.get("severity", "high")
        try:
            severity = RuleSeverity(severity_str)
        except ValueError:
            severity = RuleSeverity.HIGH

        evidence_reqs = []
        for req_data in json_data.get("evidence_requirements", []):
            evidence_reqs.append(
                EvidenceRequirement(
                    id=req_data.get("id", f"{rule_id}-ER"),
                    description=req_data.get("description", ""),
                    artifact_types=req_data.get("artifact_types", ["code"]),
                    extraction_hints=req_data.get("extraction_hints", []),
                    required=req_data.get("required", True),
                )
            )

        return Rule(
            id=rule_id,
            title=json_data.get("title") or f"{row.document_title or 'Document'} - Item {row.item_index}",
            description=row.item_text,
            category=self.map_item_type_to_category(row.item_type),
            severity=severity,
            check_points=check_points,
            pass_criteria=json_data.get("pass_criteria", ""),
            fail_examples=json_data.get("fail_examples", []),
            evidence_requirements=evidence_reqs,
            metadata={
                "source": "supabase",
                "source_document_id": row.document_id,
                "source_document_title": row.document_title,
                "page": row.page,
                "section": row.section,
                "language": row.language,
                "item_index": row.item_index,
            },
        )

    def map_rows_to_rules(self, rows: list[ComplianceItemRow]) -> list[Rule]:
        """Map multiple ComplianceItemRows to Rules."""
        return [self.map_row_to_rule(row) for row in rows]

    # Sync wrappers
    def fetch_items_by_document_sync(
        self, document_id: int, language: str | None = None
    ) -> list[ComplianceItemRow]:
        """Synchronous wrapper for fetch_items_by_document."""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self.fetch_items_by_document(document_id, language)
        )

    def fetch_all_items_sync(
        self, language: str | None = None
    ) -> list[ComplianceItemRow]:
        """Synchronous wrapper for fetch_all_items."""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(
            self.fetch_all_items(language)
        )
