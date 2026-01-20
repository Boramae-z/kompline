"""Supabase database provider for compliance items."""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import text

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
    """Provider for fetching compliance items from Supabase."""

    ITEM_TYPE_MAPPING: dict[str, RuleCategory] = {
        "algorithm_fairness": RuleCategory.ALGORITHM_FAIRNESS,
        "fairness": RuleCategory.ALGORITHM_FAIRNESS,
        "data_handling": RuleCategory.DATA_HANDLING,
        "transparency": RuleCategory.TRANSPARENCY,
        "disclosure": RuleCategory.DISCLOSURE,
        "privacy": RuleCategory.PRIVACY,
        "security": RuleCategory.SECURITY,
    }

    # SQL Queries
    FETCH_ITEMS_BY_DOCUMENT = """
    SELECT id, document_id, document_title, item_index, item_type,
           item_text, page, section, item_json, language, created_at
    FROM compliance_items
    WHERE document_id = :document_id
      AND (:language::text IS NULL OR language = :language)
    ORDER BY item_index
    """

    FETCH_ITEMS_BY_TYPE = """
    SELECT id, document_id, document_title, item_index, item_type,
           item_text, page, section, item_json, language, created_at
    FROM compliance_items
    WHERE item_type = :item_type
      AND (:language::text IS NULL OR language = :language)
    ORDER BY document_id, item_index
    """

    FETCH_ALL_ITEMS = """
    SELECT id, document_id, document_title, item_index, item_type,
           item_text, page, section, item_json, language, created_at
    FROM compliance_items
    WHERE (:language::text IS NULL OR language = :language)
    ORDER BY document_id, item_index
    """

    FETCH_DOCUMENT = """
    SELECT id, filename, markdown_text, page_count, language, created_at
    FROM documents
    WHERE id = :document_id
    """

    def __init__(self, cache_ttl_seconds: int = 300):
        self._cache: dict[str, tuple[datetime, Any]] = {}
        self._cache_ttl = timedelta(seconds=cache_ttl_seconds)

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
        query: str,
        params: dict[str, Any],
        max_retries: int = 3,
    ) -> list[dict[str, Any]]:
        from kompline.db import get_sessionmaker

        last_error = None
        for attempt in range(max_retries):
            try:
                sessionmaker = get_sessionmaker()
                async with sessionmaker() as session:
                    result = await session.execute(text(query), params)
                    return [dict(row._mapping) for row in result.fetchall()]
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(1.0 * (attempt + 1))
                    continue

        raise SupabaseConnectionError(
            f"Failed to connect after {max_retries} attempts: {last_error}"
        )

    def _row_to_item(self, row: dict[str, Any]) -> ComplianceItemRow:
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
            created_at=row["created_at"],
        )

    async def fetch_items_by_document(
        self, document_id: int, language: str | None = None
    ) -> list[ComplianceItemRow]:
        """Fetch compliance items by document ID.

        Args:
            document_id: The document ID to filter by.
            language: Optional language filter.

        Returns:
            List of ComplianceItemRow objects.
        """
        cache_key = self._cache_key("by_doc", document_id=document_id, language=language)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        rows = await self._execute_query(
            self.FETCH_ITEMS_BY_DOCUMENT,
            {"document_id": document_id, "language": language},
        )
        items = [self._row_to_item(r) for r in rows]
        self._set_cached(cache_key, items)
        return items

    async def fetch_items_by_type(
        self, item_type: str, language: str | None = None
    ) -> list[ComplianceItemRow]:
        """Fetch compliance items by item type.

        Args:
            item_type: The item type to filter by.
            language: Optional language filter.

        Returns:
            List of ComplianceItemRow objects.
        """
        cache_key = self._cache_key("by_type", item_type=item_type, language=language)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        rows = await self._execute_query(
            self.FETCH_ITEMS_BY_TYPE,
            {"item_type": item_type, "language": language},
        )
        items = [self._row_to_item(r) for r in rows]
        self._set_cached(cache_key, items)
        return items

    async def fetch_all_items(
        self, language: str | None = None
    ) -> list[ComplianceItemRow]:
        """Fetch all compliance items.

        Args:
            language: Optional language filter.

        Returns:
            List of ComplianceItemRow objects.
        """
        cache_key = self._cache_key("all", language=language)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        rows = await self._execute_query(
            self.FETCH_ALL_ITEMS,
            {"language": language},
        )
        items = [self._row_to_item(r) for r in rows]
        self._set_cached(cache_key, items)
        return items

    async def fetch_document_metadata(
        self, document_id: int
    ) -> dict[str, Any] | None:
        """Fetch document metadata by ID.

        Args:
            document_id: The document ID.

        Returns:
            Document metadata dict or None if not found.
        """
        rows = await self._execute_query(
            self.FETCH_DOCUMENT,
            {"document_id": document_id},
        )
        return rows[0] if rows else None

    def map_item_type_to_category(self, item_type: str) -> RuleCategory:
        """Map item type string to RuleCategory enum.

        Args:
            item_type: The item type from database.

        Returns:
            Corresponding RuleCategory, defaults to ALGORITHM_FAIRNESS.
        """
        return self.ITEM_TYPE_MAPPING.get(
            item_type.lower(), RuleCategory.ALGORITHM_FAIRNESS
        )

    def _extract_check_points(self, text: str) -> list[str]:
        """Extract check points from text with bullets or numbers.

        Args:
            text: Text containing potential check points.

        Returns:
            List of extracted check points.
        """
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
        """Map a ComplianceItemRow to a Rule object.

        Args:
            row: The compliance item row from database.

        Returns:
            Rule object with mapped fields.
        """
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
        """Map multiple ComplianceItemRows to Rules.

        Args:
            rows: List of compliance item rows.

        Returns:
            List of Rule objects.
        """
        return [self.map_row_to_rule(row) for row in rows]

    # Sync wrappers
    def fetch_items_by_document_sync(
        self, document_id: int, language: str | None = None
    ) -> list[ComplianceItemRow]:
        """Synchronous wrapper for fetch_items_by_document."""
        return asyncio.get_event_loop().run_until_complete(
            self.fetch_items_by_document(document_id, language)
        )

    def fetch_all_items_sync(
        self, language: str | None = None
    ) -> list[ComplianceItemRow]:
        """Synchronous wrapper for fetch_all_items."""
        return asyncio.get_event_loop().run_until_complete(
            self.fetch_all_items(language)
        )
