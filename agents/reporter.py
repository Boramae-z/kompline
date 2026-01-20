from __future__ import annotations

import logging
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

from agents.config import REPORT_OUTPUT_DIR, REPORT_POLL_INTERVAL
from agents.database import DatabaseClient
from agents.logging_utils import configure_logging
from agents.prompt_loader import load_prompt

logger = logging.getLogger("agents.reporter")
REPORTER_PROMPT = load_prompt("reporter")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _summarize_status(results: List[Dict]) -> Dict[str, int]:
    counter = Counter(result.get("status", "UNKNOWN") for result in results)
    return dict(counter)


def _format_evidence(evidence: str | None, indent: str = "") -> str:
    if not evidence:
        return f"{indent}- Evidence: (none)"
    lines = [line for line in evidence.splitlines() if line.strip()]
    if len(lines) == 1:
        return f"{indent}- Evidence: {lines[0]}"
    joined = "\n".join(lines)
    return f"{indent}- Evidence:\n\n```text\n{joined}\n```\n"


def _render_result_row(result: Dict, compliance_item: Dict | None) -> str:
    status = result.get("status") or "UNKNOWN"
    reasoning = result.get("reasoning") or "No reasoning provided."
    evidence_text = result.get("evidence")
    item_text = (compliance_item or {}).get("item_text") or "(item text not available)"
    section = (compliance_item or {}).get("section")
    page = (compliance_item or {}).get("page")

    item_meta = []
    if section:
        item_meta.append(f"Section: {section}")
    if page:
        item_meta.append(f"Page: {page}")
    item_meta_text = ", ".join(item_meta) if item_meta else "Section/Page: (not provided)"

    if status == "PASS":
        explanation = (
            "The validator found this requirement satisfied based on the reasoning and evidence below."
        )
        recommendation = "No action required."
    elif status == "FAIL":
        explanation = (
            "This requirement is not satisfied. The validator indicates a compliance gap and cites the evidence below."
        )
        recommendation = (
            "Update the implementation to satisfy this requirement, then re-run the scan. "
            f"Focus on the gap described in the reasoning: {reasoning}"
        )
    else:
        explanation = (
            "The scan could not complete successfully for this item. See reasoning and evidence below."
        )
        recommendation = "Resolve the scan error described in the reasoning, then re-run the scan."

    evidence_block = _format_evidence(evidence_text)

    return (
        f"### Compliance Item {result.get('compliance_item_id')}\n"
        f"- Status: {status}\n"
        f"- Requirement: {item_text}\n"
        f"- {item_meta_text}\n"
        f"- Explanation: {explanation}\n"
        f"- Reasoning: {reasoning}\n"
        f"{evidence_block}\n"
        f"- Recommendation: {recommendation}\n"
    )


def _write_report(scan_id: str, content: str) -> Path:
    REPORT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_OUTPUT_DIR / f"scan-{scan_id}.md"
    report_path.write_text(content, encoding="utf-8")
    return report_path


def generate_report(
    scan: Dict,
    results: List[Dict],
    compliance_items: Dict[int, Dict],
) -> Tuple[str, Path]:
    summary = _summarize_status(results)
    total_results = sum(summary.values())
    failures = summary.get("FAIL", 0) + summary.get("ERROR", 0)
    lines = [
        "# Kompline Compliance Report",
        "",
        "## Scan Metadata",
        "",
        f"- Scan ID: {scan.get('id')}",
        f"- Repo URL: {scan.get('repo_url')}",
        f"- Generated At (UTC): {_utc_now()}",
        "",
        "## Executive Summary",
        "",
    ]
    for status, count in sorted(summary.items()):
        lines.append(f"- {status}: {count}")

    lines.extend(
        [
            "",
            f"- Total Checks: {total_results}",
            f"- Findings Requiring Action: {failures}",
            "",
            "## Findings",
            "",
        ]
    )
    for result in results:
        compliance_item = compliance_items.get(result.get("compliance_item_id"))
        lines.append(_render_result_row(result, compliance_item))

    content = "\n".join(lines).strip() + "\n"
    report_path = _write_report(scan["id"], content)
    return content, report_path


def run_once(db: DatabaseClient) -> int:
    active = db.list_active_scans(["PROCESSING", "REPORT_GENERATING"])
    if not active:
        return 0

    processed = 0
    for scan in active:
        scan_id = scan["id"]
        pending = db.count_pending_results(scan_id)
        if pending > 0:
            continue

        db.update_scan_status(scan_id, "REPORT_GENERATING")
        results = db.list_scan_results(scan_id)
        compliance_items: Dict[int, Dict] = {}
        for result in results:
            item_id = result.get("compliance_item_id")
            if item_id is None or item_id in compliance_items:
                continue
            compliance_items[item_id] = db.get_compliance_item(item_id) or {}
        content, report_path = generate_report(scan, results, compliance_items)
        try:
            db.update_scan_status(
                scan_id,
                "COMPLETED",
                report_url=str(report_path),
                report_markdown=content,
            )
        except Exception:
            logger.exception("Failed to store report_markdown for scan=%s", scan_id)
            db.update_scan_status(scan_id, "COMPLETED", report_url=str(report_path))
        logger.info("Report generated for scan=%s path=%s", scan_id, report_path)
        processed += 1

    return processed


def run_loop() -> None:
    configure_logging()
    db = DatabaseClient.from_env()
    logger.info("Reporter started")
    while True:
        try:
            count = run_once(db)
            if count == 0:
                time.sleep(REPORT_POLL_INTERVAL)
        except Exception:
            logger.exception("Reporter error")
            time.sleep(REPORT_POLL_INTERVAL)


if __name__ == "__main__":
    run_loop()
