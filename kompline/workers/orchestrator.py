"""Orchestrator worker - dispatches scan tasks to validators."""

import logging
import time

from kompline.persistence.scan_store import ScanStore
from kompline.workers.config import ORCHESTRATOR_POLL_INTERVAL

logger = logging.getLogger(__name__)


class OrchestratorWorker:
    """Monitors QUEUED scans and creates scan_results for validators."""

    def __init__(self, store: ScanStore):
        self.store = store

    def run_once(self) -> int:
        """Process one batch of queued scans."""
        scans = self.store.list_queued_scans()
        if not scans:
            return 0

        processed = 0
        for scan in scans:
            scan_id = scan["id"]
            logger.info("Processing scan=%s", scan_id)

            # Get linked documents
            document_ids = self.store.get_scan_documents(scan_id)
            if not document_ids:
                logger.warning("Scan %s has no documents; marking FAILED", scan_id)
                self.store.update_scan_status(scan_id, "FAILED")
                processed += 1
                continue

            # Get compliance items for documents
            compliance_items = self.store.get_compliance_items(document_ids)
            if not compliance_items:
                logger.warning("Scan %s has no compliance items; marking FAILED", scan_id)
                self.store.update_scan_status(scan_id, "FAILED")
                processed += 1
                continue

            # Create pending results for each item
            inserted = self.store.create_scan_results(scan_id, compliance_items)
            logger.info("Created %d scan_results for scan=%s", inserted, scan_id)

            self.store.update_scan_status(scan_id, "PROCESSING")
            processed += 1

        return processed

    def run_loop(self) -> None:
        """Run the orchestrator in a continuous loop."""
        logger.info("Orchestrator worker started")
        while True:
            try:
                count = self.run_once()
                if count == 0:
                    time.sleep(ORCHESTRATOR_POLL_INTERVAL)
            except Exception:
                logger.exception("Orchestrator error")
                time.sleep(ORCHESTRATOR_POLL_INTERVAL)
