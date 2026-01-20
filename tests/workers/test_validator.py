"""Tests for ValidatorWorker with retry logic."""

import pytest
from unittest.mock import MagicMock, patch

from kompline.workers.validator import ValidatorWorker, RetryConfig


class TestRetryConfig:
    """Tests for RetryConfig class."""

    def test_default_values(self):
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1
        assert config.max_delay == 30
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_exponential_backoff_without_jitter(self):
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)

        assert config.get_delay(0) == 1.0
        assert config.get_delay(1) == 2.0
        assert config.get_delay(2) == 4.0
        assert config.get_delay(3) == 8.0

    def test_max_delay_cap(self):
        config = RetryConfig(base_delay=10.0, max_delay=15.0, exponential_base=2.0, jitter=False)

        # 10 * 2^0 = 10
        assert config.get_delay(0) == 10.0
        # 10 * 2^1 = 20, but capped at 15
        assert config.get_delay(1) == 15.0
        # 10 * 2^2 = 40, but capped at 15
        assert config.get_delay(2) == 15.0

    def test_jitter_adds_randomness(self):
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=True)

        delays = [config.get_delay(0) for _ in range(10)]
        # With jitter, delays should vary (multiply by 0.5 to 1.5)
        # Base delay 1.0 * (0.5 + random()) should be between 0.5 and 1.5
        assert all(0.5 <= d <= 1.5 for d in delays)
        # At least some variation should exist
        assert len(set(delays)) > 1


class TestValidatorWorker:
    """Tests for ValidatorWorker class."""

    def test_validates_pending_result(self):
        mock_store = MagicMock()
        mock_store.list_pending_results.return_value = [
            {"id": "result-1", "scan_id": "scan-1", "compliance_item_id": 1}
        ]
        mock_store.get_scan.return_value = {
            "id": "scan-1",
            "repo_url": "https://github.com/test/repo"
        }
        mock_store.get_compliance_item.return_value = {
            "id": 1,
            "item_text": "Check encryption"
        }

        with patch("kompline.workers.validator.validate_compliance_item") as mock_validate:
            mock_validate.return_value = ("PASS", "Encryption found", "AES-256 in config")

            worker = ValidatorWorker(mock_store)
            processed = worker.run_once()

        assert processed == 1
        mock_store.update_scan_result.assert_called_once()
        call_args = mock_store.update_scan_result.call_args
        assert call_args[0][1] == "PASS"

    def test_returns_zero_when_no_pending_results(self):
        mock_store = MagicMock()
        mock_store.list_pending_results.return_value = []

        worker = ValidatorWorker(mock_store)
        processed = worker.run_once()

        assert processed == 0
        mock_store.get_scan.assert_not_called()

    def test_handles_missing_scan(self):
        mock_store = MagicMock()
        mock_store.list_pending_results.return_value = [
            {"id": "result-1", "scan_id": "scan-1", "compliance_item_id": 1}
        ]
        mock_store.get_scan.return_value = None

        worker = ValidatorWorker(mock_store)
        processed = worker.run_once()

        assert processed == 1
        call_args = mock_store.update_scan_result.call_args
        assert call_args[0][1] == "ERROR"
        assert "Scan not found" in call_args[0][2]

    def test_handles_empty_repo_url(self):
        mock_store = MagicMock()
        mock_store.list_pending_results.return_value = [
            {"id": "result-1", "scan_id": "scan-1", "compliance_item_id": 1}
        ]
        mock_store.get_scan.return_value = {"id": "scan-1", "repo_url": ""}

        worker = ValidatorWorker(mock_store)
        processed = worker.run_once()

        assert processed == 1
        call_args = mock_store.update_scan_result.call_args
        assert call_args[0][1] == "ERROR"
        assert "repo_url is empty" in call_args[0][2]

    def test_handles_missing_compliance_item(self):
        mock_store = MagicMock()
        mock_store.list_pending_results.return_value = [
            {"id": "result-1", "scan_id": "scan-1", "compliance_item_id": 1}
        ]
        mock_store.get_scan.return_value = {
            "id": "scan-1",
            "repo_url": "https://github.com/test/repo"
        }
        mock_store.get_compliance_item.return_value = None

        worker = ValidatorWorker(mock_store)
        processed = worker.run_once()

        assert processed == 1
        call_args = mock_store.update_scan_result.call_args
        assert call_args[0][1] == "ERROR"
        assert "Compliance item not found" in call_args[0][2]

    def test_handles_validation_error_with_retry(self):
        mock_store = MagicMock()
        mock_store.list_pending_results.return_value = [
            {"id": "result-1", "scan_id": "scan-1", "compliance_item_id": 1}
        ]
        mock_store.get_scan.return_value = {
            "id": "scan-1",
            "repo_url": "https://github.com/test/repo"
        }
        mock_store.get_compliance_item.return_value = {
            "id": 1,
            "item_text": "Check encryption"
        }

        with patch("kompline.workers.validator.validate_compliance_item") as mock_validate:
            # First call fails, second succeeds
            mock_validate.side_effect = [
                Exception("API error"),
                ("PASS", "OK", "evidence")
            ]

            worker = ValidatorWorker(
                mock_store,
                retry_config=RetryConfig(max_retries=1, jitter=False, base_delay=0.01)
            )
            processed = worker.run_once()

        assert processed == 1
        assert mock_validate.call_count == 2
        call_args = mock_store.update_scan_result.call_args
        assert call_args[0][1] == "PASS"

    def test_returns_error_after_max_retries_exceeded(self):
        mock_store = MagicMock()
        mock_store.list_pending_results.return_value = [
            {"id": "result-1", "scan_id": "scan-1", "compliance_item_id": 1}
        ]
        mock_store.get_scan.return_value = {
            "id": "scan-1",
            "repo_url": "https://github.com/test/repo"
        }
        mock_store.get_compliance_item.return_value = {
            "id": 1,
            "item_text": "Check encryption"
        }

        with patch("kompline.workers.validator.validate_compliance_item") as mock_validate:
            # All calls fail
            mock_validate.side_effect = Exception("Persistent API error")

            worker = ValidatorWorker(
                mock_store,
                retry_config=RetryConfig(max_retries=2, jitter=False, base_delay=0.01)
            )
            processed = worker.run_once()

        assert processed == 1
        # Initial + 2 retries = 3 calls
        assert mock_validate.call_count == 3
        call_args = mock_store.update_scan_result.call_args
        assert call_args[0][1] == "ERROR"
        assert "Validation failed" in call_args[0][2]

    def test_worker_id_included_in_result(self):
        mock_store = MagicMock()
        mock_store.list_pending_results.return_value = [
            {"id": "result-1", "scan_id": "scan-1", "compliance_item_id": 1}
        ]
        mock_store.get_scan.return_value = {
            "id": "scan-1",
            "repo_url": "https://github.com/test/repo"
        }
        mock_store.get_compliance_item.return_value = {
            "id": 1,
            "item_text": "Check encryption"
        }

        with patch("kompline.workers.validator.validate_compliance_item") as mock_validate:
            mock_validate.return_value = ("PASS", "OK", "evidence")

            worker = ValidatorWorker(mock_store)
            worker.run_once()

        call_args = mock_store.update_scan_result.call_args
        # worker_id should be the last positional or keyword argument
        assert call_args[0][4] is not None or call_args[1].get("worker_id") is not None

    def test_custom_retry_config(self):
        mock_store = MagicMock()
        custom_config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=60.0,
            exponential_base=3.0,
            jitter=False
        )

        worker = ValidatorWorker(mock_store, retry_config=custom_config)

        assert worker.retry_config.max_retries == 5
        assert worker.retry_config.base_delay == 2.0
        assert worker.retry_config.max_delay == 60.0
        assert worker.retry_config.exponential_base == 3.0
        assert worker.retry_config.jitter is False
