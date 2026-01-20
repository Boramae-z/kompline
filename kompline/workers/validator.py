"""Validator worker - validates compliance items against repositories."""

import logging
import random
import time
from dataclasses import dataclass

from kompline.persistence.scan_store import ScanStore
from kompline.workers.config import (
    MAX_RETRIES,
    RETRY_BASE_DELAY,
    RETRY_MAX_DELAY,
    VALIDATOR_POLL_INTERVAL,
    WORKER_ID,
    MAX_CONTEXT_CHARS,
    MAX_EVIDENCE_CHARS,
)

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior with exponential backoff."""

    max_retries: int = MAX_RETRIES
    base_delay: float = RETRY_BASE_DELAY
    max_delay: float = RETRY_MAX_DELAY
    exponential_base: float = 2.0
    jitter: bool = True

    def get_delay(self, attempt: int) -> float:
        """Calculate delay using exponential backoff.

        Args:
            attempt: The attempt number (0-indexed).

        Returns:
            Delay in seconds before next retry.
        """
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        if self.jitter:
            # Add jitter by multiplying with random value between 0.5 and 1.5
            delay = delay * (0.5 + random.random())
        return delay


def validate_compliance_item(
    repo_url: str,
    compliance_text: str,
) -> tuple[str, str, str | None]:
    """Validate a compliance item against a repository.

    This is a stub function that can be mocked in tests. In production,
    this should integrate with actual compliance validation agents.

    Args:
        repo_url: URL of the repository to validate against.
        compliance_text: The compliance requirement text to check.

    Returns:
        Tuple of (status, reasoning, evidence) where:
        - status: One of "PASS", "FAIL", or "ERROR"
        - reasoning: Explanation of the validation result
        - evidence: Supporting evidence (code snippets, etc.)
    """
    # Stub implementation - in production, this would integrate with
    # agents like AuditAgent and CodeSearchAgent
    #
    # Example production implementation:
    # from kompline.agents.audit_agent import AuditAgent
    # from kompline.agents.code_search_agent import CodeSearchAgent
    #
    # search_agent = CodeSearchAgent()
    # search_results = search_agent.search(repo_url, compliance_text)
    #
    # audit_agent = AuditAgent()
    # result = audit_agent.evaluate_text(
    #     compliance_text=compliance_text,
    #     code_context=search_results,
    #     max_context=MAX_CONTEXT_CHARS,
    # )
    #
    # evidence = result.get("evidence", "")
    # if evidence and len(evidence) > MAX_EVIDENCE_CHARS:
    #     evidence = evidence[:MAX_EVIDENCE_CHARS] + "...(truncated)"
    #
    # return (
    #     result.get("status", "ERROR"),
    #     result.get("reasoning", "No reasoning provided"),
    #     evidence or None,
    # )

    raise NotImplementedError(
        "validate_compliance_item is a stub. "
        "Mock this function in tests or implement actual validation logic."
    )


class ValidatorWorker:
    """Validates pending scan results with retry logic."""

    def __init__(
        self,
        store: ScanStore,
        retry_config: RetryConfig | None = None,
    ):
        """Initialize the validator worker.

        Args:
            store: ScanStore instance for database operations.
            retry_config: Optional retry configuration. Uses defaults if not provided.
        """
        self.store = store
        self.retry_config = retry_config or RetryConfig()

    def _validate_with_retry(
        self,
        repo_url: str,
        compliance_text: str,
    ) -> tuple[str, str, str | None]:
        """Validate with retry logic.

        Args:
            repo_url: URL of the repository to validate against.
            compliance_text: The compliance requirement text to check.

        Returns:
            Tuple of (status, reasoning, evidence).
        """
        last_error: Exception | None = None

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                return validate_compliance_item(repo_url, compliance_text)
            except Exception as e:
                last_error = e
                if attempt < self.retry_config.max_retries:
                    delay = self.retry_config.get_delay(attempt)
                    logger.warning(
                        "Validation failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1,
                        self.retry_config.max_retries + 1,
                        delay,
                        e
                    )
                    time.sleep(delay)
                else:
                    logger.error(
                        "Validation failed after %d attempts: %s",
                        self.retry_config.max_retries + 1,
                        e
                    )

        return ("ERROR", f"Validation failed: {last_error}", None)

    def run_once(self) -> int:
        """Process one pending result.

        Returns:
            Number of results processed (0 or 1).
        """
        pending = self.store.list_pending_results(limit=1)
        if not pending:
            return 0

        processed = 0
        for result in pending:
            result_id = result["id"]
            scan_id = result["scan_id"]
            compliance_item_id = result["compliance_item_id"]

            # Get scan info
            scan = self.store.get_scan(scan_id)
            if not scan:
                self.store.update_scan_result(
                    result_id, "ERROR", "Scan not found", None, WORKER_ID
                )
                processed += 1
                continue

            repo_url = scan.get("repo_url", "")
            if not repo_url:
                self.store.update_scan_result(
                    result_id, "ERROR", "Scan repo_url is empty", None, WORKER_ID
                )
                processed += 1
                continue

            # Get compliance item
            compliance_item = self.store.get_compliance_item(compliance_item_id)
            if not compliance_item:
                self.store.update_scan_result(
                    result_id, "ERROR", "Compliance item not found", None, WORKER_ID
                )
                processed += 1
                continue

            compliance_text = compliance_item.get("item_text", "")

            # Validate with retry
            status, reasoning, evidence = self._validate_with_retry(
                repo_url, compliance_text
            )

            self.store.update_scan_result(
                result_id,
                status,
                f"[{WORKER_ID}] {reasoning}",
                evidence,
                WORKER_ID
            )
            processed += 1

        return processed

    def run_loop(self) -> None:
        """Run the validator in a continuous loop."""
        logger.info("Validator worker started (id=%s)", WORKER_ID)
        while True:
            try:
                count = self.run_once()
                if count == 0:
                    time.sleep(VALIDATOR_POLL_INTERVAL)
            except Exception:
                logger.exception("Validator error")
                time.sleep(VALIDATOR_POLL_INTERVAL)
