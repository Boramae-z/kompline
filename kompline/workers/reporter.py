"""Reporter worker - generates compliance reports."""

import logging
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kompline.persistence.scan_store import ScanStore
from kompline.workers.config import REPORTER_POLL_INTERVAL, REPORT_OUTPUT_DIR

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReporterWorker:
    """Generates reports for completed scans."""

    def __init__(self, store: ScanStore):
        self.store = store

    def _generate_markdown(
        self,
        scan: dict[str, Any],
        results: list[dict[str, Any]],
    ) -> str:
        """Generate a markdown report.

        Args:
            scan: The scan record with id and repo_url
            results: List of scan result records

        Returns:
            Markdown formatted report string
        """
        status_counts = Counter(r.get("status", "UNKNOWN") for r in results)

        lines = [
            "# Kompline Compliance Report",
            "",
            f"- **Scan ID**: {scan.get('id')}",
            f"- **Repository**: {scan.get('repo_url')}",
            f"- **Generated**: {_utc_now()}",
            "",
            "## Summary",
            "",
        ]

        for status, count in sorted(status_counts.items()):
            emoji = {"PASS": "\u2705", "FAIL": "\u274c", "ERROR": "\u26a0\ufe0f"}.get(status, "\u2753")
            lines.append(f"- {emoji} **{status}**: {count}")

        lines.extend(["", "## Detailed Results", ""])

        for result in results:
            status = result.get("status", "UNKNOWN")
            emoji = {"PASS": "\u2705", "FAIL": "\u274c", "ERROR": "\u26a0\ufe0f"}.get(status, "\u2753")

            lines.append(f"### {emoji} Item {result.get('compliance_item_id')}")
            lines.append(f"- **Status**: {status}")
            lines.append(f"- **Reasoning**: {result.get('reasoning', 'N/A')}")

            evidence = result.get("evidence")
            if evidence:
                lines.append("- **Evidence**:")
                lines.append("  ```")
                lines.append(f"  {evidence}")
                lines.append("  ```")
            lines.append("")

        return "\n".join(lines)

    def _generate_byeolji5(
        self,
        scan: dict[str, Any],
        results: list[dict[str, Any]],
    ) -> str:
        """Generate byeolji5 format report (Korean regulatory format).

        This format is based on the Korean regulatory self-assessment form
        commonly used for algorithm fairness and compliance auditing.

        Args:
            scan: The scan record with id and repo_url
            results: List of scan result records

        Returns:
            Korean regulatory format report string
        """
        status_counts = Counter(r.get("status", "UNKNOWN") for r in results)
        is_compliant = status_counts.get("FAIL", 0) == 0 and status_counts.get("ERROR", 0) == 0

        lines = [
            "=" * 60,
            "알고리즘 공정성 자가평가서 (별지5 양식)",
            "=" * 60,
            "",
            f"보고서 ID: {scan.get('id')}",
            f"대상 저장소: {scan.get('repo_url')}",
            f"생성일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "-" * 40,
            "1. 평가 요약",
            "-" * 40,
            f"  - 종합 판정: {'적합' if is_compliant else '부적합'}",
            f"  - 총 점검 항목: {len(results)}개",
            f"  - 적합: {status_counts.get('PASS', 0)}개",
            f"  - 부적합: {status_counts.get('FAIL', 0)}개",
            f"  - 검토 필요: {status_counts.get('ERROR', 0)}개",
            "",
            "-" * 40,
            "2. 상세 점검 결과",
            "-" * 40,
        ]

        for i, result in enumerate(results, 1):
            status = result.get("status", "UNKNOWN")
            status_kr = {"PASS": "적합", "FAIL": "부적합", "ERROR": "검토필요"}.get(status, "미정")

            lines.append(f"\n[{i}] 항목 {result.get('compliance_item_id')}")
            lines.append(f"    판정: {status_kr}")
            lines.append(f"    근거: {result.get('reasoning', 'N/A')}")

            evidence = result.get("evidence")
            if evidence:
                # Truncate evidence to 200 characters as per spec
                truncated = evidence[:200] + "..." if len(evidence) > 200 else evidence
                lines.append(f"    증거: {truncated}")

        lines.extend([
            "",
            "=" * 60,
            "끝",
            "=" * 60,
        ])

        return "\n".join(lines)

    def _save_report(self, scan_id: str, content: str) -> Path:
        """Save report to file.

        Args:
            scan_id: The scan ID for filename
            content: Report content to write

        Returns:
            Path to the saved report file
        """
        REPORT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORT_OUTPUT_DIR / f"scan-{scan_id}.md"
        report_path.write_text(content, encoding="utf-8")
        return report_path

    def run_once(self) -> int:
        """Process completed scans and generate reports.

        Looks for scans in PROCESSING or REPORT_GENERATING status
        where all results are complete (no pending), generates reports
        in both Markdown and byeolji5 formats, and updates scan status.

        Returns:
            Number of scans processed
        """
        active = self.store.list_active_scans(["PROCESSING", "REPORT_GENERATING"])
        if not active:
            return 0

        processed = 0
        for scan in active:
            scan_id = scan["id"]

            # Check if all results are complete
            pending = self.store.count_pending_results(scan_id)
            if pending > 0:
                continue

            # Mark as generating report
            self.store.update_scan_status(scan_id, "REPORT_GENERATING")

            # Get all results
            results = self.store.list_scan_results(scan_id)

            # Generate reports in both formats
            markdown = self._generate_markdown(scan, results)
            byeolji5 = self._generate_byeolji5(scan, results)

            # Save to file
            report_path = self._save_report(scan_id, markdown)

            # Update scan with report
            try:
                self.store.update_scan_status(
                    scan_id,
                    "COMPLETED",
                    report_url=str(report_path),
                    report_markdown=markdown,
                )
            except Exception:
                logger.exception("Failed to store report for scan=%s", scan_id)
                self.store.update_scan_status(scan_id, "COMPLETED", report_url=str(report_path))

            logger.info("Report generated for scan=%s path=%s", scan_id, report_path)
            processed += 1

        return processed

    def run_loop(self) -> None:
        """Run the reporter in a continuous loop.

        Polls for completed scans and generates reports continuously
        until interrupted.
        """
        logger.info("Reporter worker started")
        while True:
            try:
                count = self.run_once()
                if count == 0:
                    time.sleep(REPORTER_POLL_INTERVAL)
            except Exception:
                logger.exception("Reporter error")
                time.sleep(REPORTER_POLL_INTERVAL)
