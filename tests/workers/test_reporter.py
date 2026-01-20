"""Tests for ReporterWorker with markdown and byeolji5 format support."""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime

from kompline.workers.reporter import ReporterWorker


class TestReporterWorker:
    """Tests for ReporterWorker class."""

    def test_generates_report_when_all_results_complete(self):
        """Report is generated when all scan results are complete (no pending)."""
        mock_store = MagicMock()
        mock_store.list_active_scans.return_value = [
            {"id": "scan-1", "repo_url": "https://github.com/test/repo", "status": "PROCESSING"}
        ]
        mock_store.count_pending_results.return_value = 0
        mock_store.list_scan_results.return_value = [
            {"id": "result-1", "compliance_item_id": 1, "status": "PASS", "reasoning": "OK", "evidence": "found"}
        ]

        with patch.object(ReporterWorker, "_save_report", return_value=Path("reports/scan-scan-1.md")):
            worker = ReporterWorker(mock_store)
            processed = worker.run_once()

        assert processed == 1
        mock_store.update_scan_status.assert_called()
        # Should be called twice: once for REPORT_GENERATING, once for COMPLETED
        assert mock_store.update_scan_status.call_count == 2

    def test_skips_scan_with_pending_results(self):
        """Scans with pending results should not have reports generated."""
        mock_store = MagicMock()
        mock_store.list_active_scans.return_value = [
            {"id": "scan-1", "repo_url": "https://github.com/test/repo", "status": "PROCESSING"}
        ]
        mock_store.count_pending_results.return_value = 5

        worker = ReporterWorker(mock_store)
        processed = worker.run_once()

        assert processed == 0
        mock_store.list_scan_results.assert_not_called()

    def test_returns_zero_when_no_active_scans(self):
        """Returns 0 when there are no active scans."""
        mock_store = MagicMock()
        mock_store.list_active_scans.return_value = []

        worker = ReporterWorker(mock_store)
        processed = worker.run_once()

        assert processed == 0
        mock_store.count_pending_results.assert_not_called()

    def test_updates_status_to_report_generating_then_completed(self):
        """Status transitions from PROCESSING to REPORT_GENERATING to COMPLETED."""
        mock_store = MagicMock()
        mock_store.list_active_scans.return_value = [
            {"id": "scan-1", "repo_url": "https://github.com/test/repo", "status": "PROCESSING"}
        ]
        mock_store.count_pending_results.return_value = 0
        mock_store.list_scan_results.return_value = [
            {"id": "result-1", "compliance_item_id": 1, "status": "PASS", "reasoning": "OK", "evidence": None}
        ]

        with patch.object(ReporterWorker, "_save_report", return_value=Path("reports/scan-scan-1.md")):
            worker = ReporterWorker(mock_store)
            worker.run_once()

        calls = mock_store.update_scan_status.call_args_list
        # First call should set REPORT_GENERATING
        assert calls[0][0][1] == "REPORT_GENERATING"
        # Second call should set COMPLETED with report_url and report_markdown
        assert calls[1][0][1] == "COMPLETED"
        assert "report_url" in calls[1][1] or len(calls[1][0]) > 2


class TestGenerateMarkdown:
    """Tests for _generate_markdown method."""

    def test_markdown_contains_scan_info(self):
        """Markdown report contains scan ID and repo URL."""
        mock_store = MagicMock()
        worker = ReporterWorker(mock_store)

        scan = {"id": "scan-123", "repo_url": "https://github.com/test/repo"}
        results = []

        markdown = worker._generate_markdown(scan, results)

        assert "scan-123" in markdown
        assert "https://github.com/test/repo" in markdown
        assert "# Kompline Compliance Report" in markdown

    def test_markdown_contains_status_summary(self):
        """Markdown report contains summary with status counts."""
        mock_store = MagicMock()
        worker = ReporterWorker(mock_store)

        scan = {"id": "scan-123", "repo_url": "https://github.com/test/repo"}
        results = [
            {"id": "r1", "compliance_item_id": 1, "status": "PASS", "reasoning": "OK", "evidence": None},
            {"id": "r2", "compliance_item_id": 2, "status": "PASS", "reasoning": "OK", "evidence": None},
            {"id": "r3", "compliance_item_id": 3, "status": "FAIL", "reasoning": "Missing", "evidence": None},
        ]

        markdown = worker._generate_markdown(scan, results)

        assert "## Summary" in markdown
        assert "PASS" in markdown
        assert "FAIL" in markdown

    def test_markdown_contains_status_emojis(self):
        """Markdown report contains appropriate emojis for statuses."""
        mock_store = MagicMock()
        worker = ReporterWorker(mock_store)

        scan = {"id": "scan-123", "repo_url": "https://github.com/test/repo"}
        results = [
            {"id": "r1", "compliance_item_id": 1, "status": "PASS", "reasoning": "OK", "evidence": None},
            {"id": "r2", "compliance_item_id": 2, "status": "FAIL", "reasoning": "Missing", "evidence": None},
            {"id": "r3", "compliance_item_id": 3, "status": "ERROR", "reasoning": "Error occurred", "evidence": None},
        ]

        markdown = worker._generate_markdown(scan, results)

        # Check for emojis
        assert "\u2705" in markdown  # checkmark for PASS
        assert "\u274c" in markdown  # X for FAIL
        assert "\u26a0\ufe0f" in markdown or "\u26a0" in markdown  # warning for ERROR

    def test_markdown_contains_detailed_results(self):
        """Markdown report contains detailed results section."""
        mock_store = MagicMock()
        worker = ReporterWorker(mock_store)

        scan = {"id": "scan-123", "repo_url": "https://github.com/test/repo"}
        results = [
            {"id": "r1", "compliance_item_id": 42, "status": "PASS", "reasoning": "Encryption found", "evidence": "AES-256"},
        ]

        markdown = worker._generate_markdown(scan, results)

        assert "## Detailed Results" in markdown
        assert "Item 42" in markdown
        assert "Encryption found" in markdown
        assert "AES-256" in markdown

    def test_markdown_handles_evidence_in_code_block(self):
        """Evidence is wrapped in code blocks."""
        mock_store = MagicMock()
        worker = ReporterWorker(mock_store)

        scan = {"id": "scan-123", "repo_url": "https://github.com/test/repo"}
        results = [
            {"id": "r1", "compliance_item_id": 1, "status": "PASS", "reasoning": "Found", "evidence": "code_snippet()"},
        ]

        markdown = worker._generate_markdown(scan, results)

        assert "```" in markdown
        assert "code_snippet()" in markdown


class TestGenerateByeolji5:
    """Tests for _generate_byeolji5 method (Korean regulatory format)."""

    def test_byeolji5_contains_korean_header(self):
        """Byeolji5 report contains Korean header."""
        mock_store = MagicMock()
        worker = ReporterWorker(mock_store)

        scan = {"id": "scan-123", "repo_url": "https://github.com/test/repo"}
        results = []

        report = worker._generate_byeolji5(scan, results)

        assert "별지5" in report or "알고리즘 공정성 자가평가서" in report

    def test_byeolji5_contains_scan_info(self):
        """Byeolji5 report contains scan ID and repo URL."""
        mock_store = MagicMock()
        worker = ReporterWorker(mock_store)

        scan = {"id": "scan-123", "repo_url": "https://github.com/test/repo"}
        results = []

        report = worker._generate_byeolji5(scan, results)

        assert "scan-123" in report
        assert "https://github.com/test/repo" in report

    def test_byeolji5_shows_compliant_when_all_pass(self):
        """Byeolji5 shows compliant (적합) when all items pass."""
        mock_store = MagicMock()
        worker = ReporterWorker(mock_store)

        scan = {"id": "scan-123", "repo_url": "https://github.com/test/repo"}
        results = [
            {"id": "r1", "compliance_item_id": 1, "status": "PASS", "reasoning": "OK", "evidence": None},
            {"id": "r2", "compliance_item_id": 2, "status": "PASS", "reasoning": "OK", "evidence": None},
        ]

        report = worker._generate_byeolji5(scan, results)

        assert "적합" in report

    def test_byeolji5_shows_non_compliant_when_fail_exists(self):
        """Byeolji5 shows non-compliant (부적합) when any item fails."""
        mock_store = MagicMock()
        worker = ReporterWorker(mock_store)

        scan = {"id": "scan-123", "repo_url": "https://github.com/test/repo"}
        results = [
            {"id": "r1", "compliance_item_id": 1, "status": "PASS", "reasoning": "OK", "evidence": None},
            {"id": "r2", "compliance_item_id": 2, "status": "FAIL", "reasoning": "Missing", "evidence": None},
        ]

        report = worker._generate_byeolji5(scan, results)

        # Should have 부적합 for overall judgment
        assert "부적합" in report

    def test_byeolji5_shows_non_compliant_when_error_exists(self):
        """Byeolji5 shows non-compliant when any item has ERROR status."""
        mock_store = MagicMock()
        worker = ReporterWorker(mock_store)

        scan = {"id": "scan-123", "repo_url": "https://github.com/test/repo"}
        results = [
            {"id": "r1", "compliance_item_id": 1, "status": "PASS", "reasoning": "OK", "evidence": None},
            {"id": "r2", "compliance_item_id": 2, "status": "ERROR", "reasoning": "Error occurred", "evidence": None},
        ]

        report = worker._generate_byeolji5(scan, results)

        # Should have 부적합 for overall judgment due to ERROR
        lines = report.split("\n")
        # Find the line with overall judgment
        judgment_found = False
        for line in lines:
            if "종합 판정" in line:
                assert "부적합" in line
                judgment_found = True
                break
        assert judgment_found, "Overall judgment line not found in report"

    def test_byeolji5_contains_summary_counts(self):
        """Byeolji5 contains summary with counts in Korean."""
        mock_store = MagicMock()
        worker = ReporterWorker(mock_store)

        scan = {"id": "scan-123", "repo_url": "https://github.com/test/repo"}
        results = [
            {"id": "r1", "compliance_item_id": 1, "status": "PASS", "reasoning": "OK", "evidence": None},
            {"id": "r2", "compliance_item_id": 2, "status": "FAIL", "reasoning": "Missing", "evidence": None},
            {"id": "r3", "compliance_item_id": 3, "status": "ERROR", "reasoning": "Error", "evidence": None},
        ]

        report = worker._generate_byeolji5(scan, results)

        # Check for Korean status labels
        assert "점검 항목" in report or "총" in report
        # Summary should include item counts
        assert "3" in report  # total items
        assert "1" in report  # PASS count

    def test_byeolji5_contains_detailed_results_in_korean(self):
        """Byeolji5 contains detailed results with Korean status labels."""
        mock_store = MagicMock()
        worker = ReporterWorker(mock_store)

        scan = {"id": "scan-123", "repo_url": "https://github.com/test/repo"}
        results = [
            {"id": "r1", "compliance_item_id": 42, "status": "PASS", "reasoning": "Encryption found", "evidence": "AES"},
        ]

        report = worker._generate_byeolji5(scan, results)

        assert "42" in report  # compliance_item_id
        assert "Encryption found" in report or "근거" in report

    def test_byeolji5_truncates_long_evidence(self):
        """Byeolji5 truncates evidence longer than 200 characters."""
        mock_store = MagicMock()
        worker = ReporterWorker(mock_store)

        scan = {"id": "scan-123", "repo_url": "https://github.com/test/repo"}
        long_evidence = "x" * 300
        results = [
            {"id": "r1", "compliance_item_id": 1, "status": "PASS", "reasoning": "OK", "evidence": long_evidence},
        ]

        report = worker._generate_byeolji5(scan, results)

        # Evidence should be truncated with ...
        assert "..." in report
        # Should not contain full 300 chars
        assert long_evidence not in report


class TestSaveReport:
    """Tests for _save_report method."""

    def test_save_report_creates_directory(self, tmp_path):
        """Report directory is created if it doesn't exist."""
        mock_store = MagicMock()
        worker = ReporterWorker(mock_store)

        # Patch REPORT_OUTPUT_DIR to use tmp_path
        report_dir = tmp_path / "reports"
        with patch("kompline.workers.reporter.REPORT_OUTPUT_DIR", report_dir):
            path = worker._save_report("scan-123", "# Report Content")

        assert report_dir.exists()
        assert path.exists()

    def test_save_report_returns_correct_path(self, tmp_path):
        """Report is saved with correct filename pattern."""
        mock_store = MagicMock()
        worker = ReporterWorker(mock_store)

        report_dir = tmp_path / "reports"
        with patch("kompline.workers.reporter.REPORT_OUTPUT_DIR", report_dir):
            path = worker._save_report("scan-123", "# Report Content")

        assert path.name == "scan-scan-123.md"
        assert path.parent == report_dir

    def test_save_report_writes_content(self, tmp_path):
        """Report content is correctly written to file."""
        mock_store = MagicMock()
        worker = ReporterWorker(mock_store)

        report_dir = tmp_path / "reports"
        content = "# Test Report\n\nThis is test content."
        with patch("kompline.workers.reporter.REPORT_OUTPUT_DIR", report_dir):
            path = worker._save_report("scan-123", content)

        assert path.read_text(encoding="utf-8") == content


class TestRunLoop:
    """Tests for run_loop method."""

    def test_run_loop_calls_run_once(self):
        """run_loop calls run_once repeatedly."""
        mock_store = MagicMock()
        worker = ReporterWorker(mock_store)

        call_count = 0

        def mock_run_once():
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                raise KeyboardInterrupt()
            return 0

        with patch.object(worker, "run_once", side_effect=mock_run_once):
            with patch("kompline.workers.reporter.time.sleep"):
                try:
                    worker.run_loop()
                except KeyboardInterrupt:
                    pass

        assert call_count == 3

    def test_run_loop_sleeps_when_no_work(self):
        """run_loop sleeps when run_once returns 0."""
        mock_store = MagicMock()
        worker = ReporterWorker(mock_store)

        call_count = 0

        def mock_run_once():
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                raise KeyboardInterrupt()
            return 0

        with patch.object(worker, "run_once", side_effect=mock_run_once):
            with patch("kompline.workers.reporter.time.sleep") as mock_sleep:
                try:
                    worker.run_loop()
                except KeyboardInterrupt:
                    pass

        mock_sleep.assert_called()
