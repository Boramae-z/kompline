"""Code Search Agent for locating compliance-relevant regions in code."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from kompline.models import Artifact, ArtifactType, ComplianceItem, Evidence, EvidenceType, Provenance, Rule


class CodeSearchAgent:
    """Search code for compliance-item related snippets."""

    def __init__(self, max_snippets: int = 5, context_lines: int = 2):
        self.max_snippets = max_snippets
        self.context_lines = context_lines

    async def search(self, artifact: Artifact, rule: Rule | ComplianceItem, relation_id: str) -> list[Evidence]:
        """Search an artifact for rule-relevant snippets."""
        if artifact.type != ArtifactType.CODE:
            return []
        source_path = Path(artifact.locator)
        if not source_path.exists():
            return []
        source_code = source_path.read_text()
        return self.search_text(source_code, source_path, rule, relation_id)

    def search_text(
        self,
        source_code: str,
        source_path: Path,
        rule: Rule | ComplianceItem,
        relation_id: str,
    ) -> list[Evidence]:
        """Search a code string for rule-relevant snippets."""
        keywords = _build_keywords(rule)
        if not keywords:
            return []

        lines = source_code.splitlines()
        hits: list[tuple[int, int, int, str]] = []
        seen: set[tuple[int, int]] = set()

        for idx, line in enumerate(lines, start=1):
            line_lower = line.lower()
            score = sum(1 for kw in keywords if kw in line_lower)
            if score == 0:
                continue
            start = max(1, idx - self.context_lines)
            end = min(len(lines), idx + self.context_lines)
            key = (start, end)
            if key in seen:
                continue
            seen.add(key)
            context = "\n".join(lines[start - 1 : end])
            hits.append((score, start, end, context))

        hits.sort(key=lambda h: (-h[0], h[1]))
        hits = hits[: self.max_snippets]

        provenance = Provenance(source=str(source_path))
        evidence_list: list[Evidence] = []
        for score, start, end, context in hits:
            evidence_list.append(
                Evidence(
                    id=_new_evidence_id(),
                    relation_id=relation_id,
                    source=str(source_path),
                    type=EvidenceType.CODE_SNIPPET,
                    content=context,
                    provenance=provenance,
                    line_number=start,
                    line_end=end,
                    relevance_score=min(1.0, 0.4 + 0.1 * score),
                    rule_ids=[rule.id],
                    metadata={
                        "category": "code_search",
                        "score": score,
                        "keywords": keywords,
                    },
                )
            )

        return evidence_list


def _build_keywords(rule: Rule | ComplianceItem) -> list[str]:
    tokens: list[str] = []
    raw_parts: Iterable[str] = [
        rule.id,
        rule.title,
        rule.description,
        " ".join(rule.check_points or []),
    ]
    for req in rule.evidence_requirements or []:
        raw_parts = list(raw_parts) + req.extraction_hints
    raw_parts = list(raw_parts) + rule.metadata.get("keywords", [])

    for part in raw_parts:
        for tok in re.split(r"[^a-zA-Z0-9_]+", part):
            tok = tok.strip().lower()
            if len(tok) >= 3:
                tokens.append(tok)

    # Deduplicate while preserving order
    seen = set()
    keywords = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            keywords.append(t)
    return keywords


def _new_evidence_id() -> str:
    import uuid

    return f"ev-{uuid.uuid4().hex[:8]}"
