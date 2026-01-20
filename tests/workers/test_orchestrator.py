# tests/workers/test_orchestrator.py
import pytest
from unittest.mock import MagicMock, patch
from kompline.workers.orchestrator import OrchestratorWorker


class TestOrchestratorWorker:
    def test_process_queued_scan_creates_results(self):
        mock_store = MagicMock()
        mock_store.list_queued_scans.return_value = [
            {"id": "scan-1", "repo_url": "https://github.com/test/repo"}
        ]
        mock_store.get_scan_documents.return_value = ["doc-1"]
        mock_store.get_compliance_items.return_value = [
            {"id": 1, "item_text": "Check encryption"}
        ]
        mock_store.create_scan_results.return_value = 1

        worker = OrchestratorWorker(mock_store)
        processed = worker.run_once()

        assert processed == 1
        mock_store.update_scan_status.assert_called_with("scan-1", "PROCESSING")

    def test_skips_scan_without_documents(self):
        mock_store = MagicMock()
        mock_store.list_queued_scans.return_value = [
            {"id": "scan-1", "repo_url": "https://github.com/test/repo"}
        ]
        mock_store.get_scan_documents.return_value = []

        worker = OrchestratorWorker(mock_store)
        processed = worker.run_once()

        assert processed == 1
        mock_store.update_scan_status.assert_called_with("scan-1", "FAILED")

    def test_skips_scan_without_compliance_items(self):
        """Test that scans with documents but no compliance items are marked FAILED."""
        mock_store = MagicMock()
        mock_store.list_queued_scans.return_value = [
            {"id": "scan-1", "repo_url": "https://github.com/test/repo"}
        ]
        mock_store.get_scan_documents.return_value = ["doc-1"]
        mock_store.get_compliance_items.return_value = []

        worker = OrchestratorWorker(mock_store)
        processed = worker.run_once()

        assert processed == 1
        mock_store.update_scan_status.assert_called_with("scan-1", "FAILED")

    def test_returns_zero_when_no_queued_scans(self):
        """Test that run_once returns 0 when there are no queued scans."""
        mock_store = MagicMock()
        mock_store.list_queued_scans.return_value = []

        worker = OrchestratorWorker(mock_store)
        processed = worker.run_once()

        assert processed == 0
        mock_store.update_scan_status.assert_not_called()

    def test_processes_multiple_queued_scans(self):
        """Test that multiple scans are processed in a single run_once call."""
        mock_store = MagicMock()
        mock_store.list_queued_scans.return_value = [
            {"id": "scan-1", "repo_url": "https://github.com/test/repo1"},
            {"id": "scan-2", "repo_url": "https://github.com/test/repo2"},
        ]
        mock_store.get_scan_documents.side_effect = [["doc-1"], ["doc-2"]]
        mock_store.get_compliance_items.side_effect = [
            [{"id": 1, "item_text": "Check 1"}],
            [{"id": 2, "item_text": "Check 2"}],
        ]
        mock_store.create_scan_results.return_value = 1

        worker = OrchestratorWorker(mock_store)
        processed = worker.run_once()

        assert processed == 2
        assert mock_store.update_scan_status.call_count == 2
