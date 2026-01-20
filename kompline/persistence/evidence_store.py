"""Evidence caching utilities backed by Postgres."""

from __future__ import annotations

import hashlib
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select

from kompline.db import get_sessionmaker, get_async_engine
from kompline.models import Artifact, Evidence, EvidenceCollection, EvidenceType, Provenance
from kompline.persistence.models import Base, EvidenceCache


async def ensure_schema() -> None:
    """Create tables if they do not exist."""
    async with get_async_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def compute_fingerprint(artifact: Artifact) -> str | None:
    """Compute a stable fingerprint for file-based artifacts."""
    if not artifact.locator:
        return None
    path = Path(artifact.locator)
    if not path.exists() or not path.is_file():
        return None
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest()


def evidence_to_dict(evidence: Evidence) -> dict[str, Any]:
    """Serialize Evidence into JSON-friendly dict."""
    data = asdict(evidence)
    data["type"] = evidence.type.value
    data["provenance"]["retrieved_at"] = evidence.provenance.retrieved_at.isoformat()
    data["collected_at"] = evidence.collected_at.isoformat()
    return data


def evidence_from_dict(data: dict[str, Any]) -> Evidence:
    """Deserialize Evidence from dict."""
    provenance = data.get("provenance") or {}
    prov = Provenance(
        source=provenance.get("source", ""),
        version=provenance.get("version"),
        retrieved_at=_parse_dt(provenance.get("retrieved_at")),
        retrieved_by=provenance.get("retrieved_by", "system"),
        checksum=provenance.get("checksum"),
        metadata=provenance.get("metadata", {}),
    )
    return Evidence(
        id=data["id"],
        relation_id=data["relation_id"],
        source=data["source"],
        type=EvidenceType(data["type"]),
        content=data["content"],
        provenance=prov,
        collected_at=_parse_dt(data.get("collected_at")),
        collected_by=data.get("collected_by", "unknown"),
        metadata=data.get("metadata", {}),
        line_number=data.get("line_number"),
        line_end=data.get("line_end"),
        page_number=data.get("page_number"),
        column=data.get("column"),
        relevance_score=data.get("relevance_score", 1.0),
        rule_ids=data.get("rule_ids", []),
    )


async def load_cached_evidence(
    artifact_id: str,
    fingerprint: str,
    relation_id: str,
) -> EvidenceCollection | None:
    """Load cached evidence by artifact fingerprint."""
    await ensure_schema()
    async_session = get_sessionmaker()
    async with async_session() as session:
        stmt = select(EvidenceCache).where(
            EvidenceCache.artifact_id == artifact_id,
            EvidenceCache.fingerprint == fingerprint,
        )
        row = (await session.execute(stmt)).scalars().first()
        if not row:
            return None
        items = row.evidence_json.get("items", [])
        collection = EvidenceCollection(relation_id=relation_id)
        for item in items:
            ev = evidence_from_dict(item)
            ev.relation_id = relation_id
            collection.add(ev)
        return collection


async def save_cached_evidence(
    artifact_id: str,
    fingerprint: str,
    evidence: EvidenceCollection,
) -> None:
    """Save evidence to cache."""
    await ensure_schema()
    async_session = get_sessionmaker()
    async with async_session() as session:
        existing = await session.get(EvidenceCache, _cache_id(artifact_id, fingerprint))
        if existing:
            await session.delete(existing)
        payload = {
            "artifact_id": artifact_id,
            "fingerprint": fingerprint,
            "items": [evidence_to_dict(e) for e in evidence],
        }
        cache = EvidenceCache(
            id=_cache_id(artifact_id, fingerprint),
            artifact_id=artifact_id,
            fingerprint=fingerprint,
            created_at=datetime.utcnow(),
            evidence_json=payload,
        )
        session.add(cache)
        await session.commit()


def _cache_id(artifact_id: str, fingerprint: str) -> str:
    return f"{artifact_id}:{fingerprint}"


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except Exception:
            pass
    return datetime.utcnow()
