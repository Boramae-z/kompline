# tests/persistence/test_scan_store.py
import pytest
from unittest.mock import MagicMock, patch
from kompline.persistence.scan_store import ScanStore


class TestScanStore:
    def test_list_queued_scans_returns_queued_only(self):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"id": "scan-1", "status": "QUEUED", "repo_url": "https://github.com/test/repo"}
        ]

        store = ScanStore(mock_client)
        result = store.list_queued_scans(limit=10)

        assert len(result) == 1
        assert result[0]["status"] == "QUEUED"
        mock_client.table.assert_called_with("scans")

    def test_update_scan_status(self):
        mock_client = MagicMock()
        store = ScanStore(mock_client)

        store.update_scan_status("scan-1", "PROCESSING")

        mock_client.table.assert_called_with("scans")

    def test_list_pending_results(self):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"id": "result-1", "status": "PENDING", "scan_id": "scan-1"}
        ]

        store = ScanStore(mock_client)
        result = store.list_pending_results(limit=1)

        assert len(result) == 1
        assert result[0]["status"] == "PENDING"

    def test_get_scan_returns_scan_by_id(self):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = [
            {"id": "scan-1", "status": "QUEUED", "repo_url": "https://github.com/test/repo"}
        ]

        store = ScanStore(mock_client)
        result = store.get_scan("scan-1")

        assert result is not None
        assert result["id"] == "scan-1"

    def test_get_scan_returns_none_when_not_found(self):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value.data = []

        store = ScanStore(mock_client)
        result = store.get_scan("nonexistent")

        assert result is None

    def test_get_scan_documents_returns_document_ids(self):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"document_id": "doc-1"},
            {"document_id": "doc-2"}
        ]

        store = ScanStore(mock_client)
        result = store.get_scan_documents("scan-1")

        assert len(result) == 2
        assert "doc-1" in result
        assert "doc-2" in result

    def test_create_scan_results_inserts_rows(self):
        mock_client = MagicMock()
        store = ScanStore(mock_client)

        compliance_items = [
            {"id": 1, "item_text": "Check encryption"},
            {"id": 2, "item_text": "Check logging"}
        ]
        count = store.create_scan_results("scan-1", compliance_items)

        assert count == 2
        mock_client.table.assert_called_with("scan_results")

    def test_create_scan_results_returns_zero_for_empty_items(self):
        mock_client = MagicMock()
        store = ScanStore(mock_client)

        count = store.create_scan_results("scan-1", [])

        assert count == 0

    def test_update_scan_result(self):
        mock_client = MagicMock()
        store = ScanStore(mock_client)

        store.update_scan_result(
            result_id="result-1",
            status="PASS",
            reasoning="Encryption found",
            evidence="AES-256 in config",
            worker_id="worker-1"
        )

        mock_client.table.assert_called_with("scan_results")

    def test_list_active_scans_returns_scans_in_statuses(self):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.in_.return_value.order.return_value.execute.return_value.data = [
            {"id": "scan-1", "status": "PROCESSING"},
            {"id": "scan-2", "status": "REPORT_GENERATING"}
        ]

        store = ScanStore(mock_client)
        result = store.list_active_scans(["PROCESSING", "REPORT_GENERATING"])

        assert len(result) == 2

    def test_list_active_scans_returns_empty_for_empty_statuses(self):
        mock_client = MagicMock()
        store = ScanStore(mock_client)

        result = store.list_active_scans([])

        assert result == []

    def test_list_scan_results(self):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"id": "result-1", "status": "PASS"},
            {"id": "result-2", "status": "FAIL"}
        ]

        store = ScanStore(mock_client)
        result = store.list_scan_results("scan-1")

        assert len(result) == 2

    def test_count_pending_results(self):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.count = 5

        store = ScanStore(mock_client)
        count = store.count_pending_results("scan-1")

        assert count == 5
