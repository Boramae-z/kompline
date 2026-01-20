from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from agents.config import (
    MAX_CONTEXT_CHARS,
    MAX_EVIDENCE_CHARS,
    MAX_FILE_SAMPLES,
    MAX_SEARCH_HITS,
    RESULT_POLL_INTERVAL,
    WORKER_ID,
)
from agents.database import DatabaseClient
from agents.git_loader import GitLoader
from agents.llm import call_openai_json
from agents.logging_utils import configure_logging
from agents.prompt_loader import load_prompt

logger = logging.getLogger("agents.validator")
VALIDATOR_PROMPT = load_prompt("validator")

LLM_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["PASS", "FAIL", "ERROR"]},
        "reasoning": {"type": "string"},
        "evidence": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["status", "reasoning", "evidence"],
    "additionalProperties": False,
}

LLM_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "search_queries": {"type": "array", "items": {"type": "string"}},
        "file_globs": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "string"},
    },
    "required": ["search_queries", "file_globs", "notes"],
    "additionalProperties": False,
}


def _truncate(text: Optional[str]) -> Optional[str]:
    if text is None:
        return None
    if len(text) <= MAX_EVIDENCE_CHARS:
        return text
    return text[:MAX_EVIDENCE_CHARS] + "...(truncated)"


def _build_repo_context(repo_path: Path) -> str:
    lines = ["Repository file list (truncated):"]
    total = 0
    for path in repo_path.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".exe", ".dll"}:
            continue
        try:
            rel = path.relative_to(repo_path)
        except ValueError:
            rel = path
        entry = f"- {rel}"
        if total + len(entry) + 1 > MAX_CONTEXT_CHARS:
            break
        lines.append(entry)
        total += len(entry) + 1
    return "\n".join(lines)


def _search_repo(repo_path: Path, query: str, max_hits: int) -> List[str]:
    hits: List[str] = []
    if not query.strip():
        return hits
    for path in repo_path.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".exe", ".dll"}:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if query not in content:
            continue
        for line_no, line in enumerate(content.splitlines(), start=1):
            if query not in line:
                continue
            snippet = line.strip()
            try:
                rel = path.relative_to(repo_path)
            except ValueError:
                rel = path
            hits.append(f"{rel}:{line_no}: {snippet}")
            if len(hits) >= max_hits:
                return hits
        if len(hits) >= max_hits:
            return hits
    return hits


def _sample_files(repo_path: Path, globs: List[str], limit: int) -> List[str]:
    samples: List[str] = []
    seen = set()
    for pattern in globs:
        for path in repo_path.rglob(pattern):
            if not path.is_file():
                continue
            if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip", ".exe", ".dll"}:
                continue
            if path in seen:
                continue
            seen.add(path)
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            snippet = content[:600].replace("\n", " ").strip()
            try:
                rel = path.relative_to(repo_path)
            except ValueError:
                rel = path
            samples.append(f"{rel}: {snippet}")
            if len(samples) >= limit:
                return samples
    return samples


def _request_plan(compliance_text: str, repo_context: str) -> Dict[str, Any]:
    plan_prompt = (
        "Plan which keyword searches and file globs to inspect before deciding. "
        "Return only JSON with search_queries and file_globs."
    )
    input_text = f"Compliance item:\n{compliance_text}\n\nRepository context:\n{repo_context}\n"
    return call_openai_json(plan_prompt, input_text, LLM_PLAN_SCHEMA)


def validate_item(repo_path: Path, compliance_text: str) -> Tuple[str, str, Optional[str]]:
    repo_context = _build_repo_context(repo_path)
    plan = _request_plan(compliance_text, repo_context)
    queries = plan.get("search_queries", [])[:5]
    globs = plan.get("file_globs", [])[:5]

    search_hits: List[str] = []
    for query in queries:
        search_hits.extend(_search_repo(repo_path, query, MAX_SEARCH_HITS))
        if len(search_hits) >= MAX_SEARCH_HITS:
            search_hits = search_hits[:MAX_SEARCH_HITS]
            break

    sampled_files = _sample_files(repo_path, globs, MAX_FILE_SAMPLES)

    context_lines = [
        "Compliance item:",
        compliance_text,
        "",
        "Repository context:",
        repo_context,
        "",
        "Search hits (path:line: text):",
        *search_hits,
        "",
        "Sampled files:",
        *sampled_files,
    ]
    input_text = "\n".join(context_lines)

    result = call_openai_json(VALIDATOR_PROMPT, input_text, LLM_SCHEMA)
    status = result.get("status", "ERROR")
    reasoning = result.get("reasoning", "No reasoning.")
    evidence_items = result.get("evidence", [])
    evidence_text = None
    if evidence_items:
        evidence_text = "\n".join(evidence_items)
    return status, reasoning, _truncate(evidence_text)


def run_once(db: DatabaseClient, loader: GitLoader) -> int:
    pending = db.list_pending_results(limit=1)
    if not pending:
        return 0

    processed = 0
    for result in pending:
        result_id = result["id"]
        scan_id = result["scan_id"]
        compliance_item_id = result["compliance_item_id"]

        scan = db.get_scan(scan_id)
        if not scan:
            db.update_scan_result(result_id, "ERROR", "Scan not found.", None)
            processed += 1
            continue

        repo_url = scan.get("repo_url") or ""
        if not repo_url:
            db.update_scan_result(result_id, "ERROR", "Scan repo_url is empty.", None)
            processed += 1
            continue

        compliance_item = db.get_compliance_item(compliance_item_id)
        if not compliance_item:
            db.update_scan_result(result_id, "ERROR", "Compliance item not found.", None)
            processed += 1
            continue

        compliance_text = compliance_item.get("item_text") or ""
        try:
            repo_path = loader.load(repo_url)
        except Exception as exc:
            db.update_scan_result(result_id, "ERROR", f"Repo load failed: {exc}", None)
            processed += 1
            continue

        status, reasoning, evidence = validate_item(repo_path, compliance_text)
        tagged_reasoning = f"[{WORKER_ID}] {reasoning}"
        db.update_scan_result(result_id, status, tagged_reasoning, evidence)
        processed += 1

    return processed


def run_loop() -> None:
    configure_logging()
    db = DatabaseClient.from_env()
    loader = GitLoader()
    logger.info("Validator started (LLM-only)")
    while True:
        try:
            count = run_once(db, loader)
            if count == 0:
                time.sleep(RESULT_POLL_INTERVAL)
        except Exception:
            logger.exception("Validator error")
            time.sleep(RESULT_POLL_INTERVAL)


if __name__ == "__main__":
    run_loop()
