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


def _format_evidence(evidence: str | None) -> str:
    if not evidence:
        return "  - Evidence: (none)"
    lines = [line for line in evidence.splitlines() if line.strip()]
    if len(lines) == 1:
        return f"  - Evidence: {lines[0]}"
    joined = "\n".join(lines)
    return "  - Evidence:\n\n```text\n" + joined + "\n```\n"


def _render_result_row(result: Dict) -> str:
    evidence_block = _format_evidence(result.get("evidence"))
    return (
        f"- Result ID: {result.get('id')}\n"
        f"  - Status: {result.get('status')}\n"
        f"  - Compliance Item: {result.get('compliance_item_id')}\n"
        f"  - Reasoning: {result.get('reasoning')}\n"
        f"{evidence_block}\n"
    )


def _write_report(scan_id: str, content: str) -> Path:
    REPORT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_OUTPUT_DIR / f"scan-{scan_id}.md"
    report_path.write_text(content, encoding="utf-8")
    return report_path


def generate_report(scan: Dict, results: List[Dict]) -> Tuple[str, Path]:
    summary = _summarize_status(results)
    lines = [
        f"# Kompline Scan Report",
        "",
        f"- Scan ID: {scan.get('id')}",
        f"- Repo URL: {scan.get('repo_url')}",
        f"- Generated At: {_utc_now()}",
        "",
        "## Summary",
        "",
    ]
    for status, count in sorted(summary.items()):
        lines.append(f"- {status}: {count}")

    lines.extend(["", "## Results", ""])
    for result in results:
        lines.append(_render_result_row(result))

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
        content, report_path = generate_report(scan, results)
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
