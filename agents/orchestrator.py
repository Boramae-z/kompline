from __future__ import annotations

import logging
import time
from typing import List

from agents.config import SCAN_POLL_INTERVAL
from agents.database import DatabaseClient
from agents.logging_utils import configure_logging
from agents.prompt_loader import load_prompt

logger = logging.getLogger("agents.orchestrator")
ORCHESTRATOR_PROMPT = load_prompt("orchestrator")


def run_once(db: DatabaseClient) -> int:
    scans = db.list_queued_scans()
    if not scans:
        return 0

    processed = 0
    for scan in scans:
        scan_id = scan["id"]
        logger.info("Processing scan=%s", scan_id)

        document_ids = db.get_scan_documents(scan_id)
        if not document_ids:
            logger.warning("Scan %s has no documents; marking FAILED", scan_id)
            db.update_scan_status(scan_id, "FAILED")
            processed += 1
            continue

        compliance_items = db.get_compliance_items(document_ids)
        if not compliance_items:
            logger.warning("Scan %s has no compliance items; marking FAILED", scan_id)
            db.update_scan_status(scan_id, "FAILED")
            processed += 1
            continue

        inserted = db.create_scan_results(scan_id, compliance_items)
        logger.info("Inserted %s scan_results for scan=%s", inserted, scan_id)
        db.update_scan_status(scan_id, "PROCESSING")
        processed += 1

    return processed


def run_loop() -> None:
    configure_logging()
    db = DatabaseClient.from_env()
    logger.info("Orchestrator started")
    while True:
        try:
            count = run_once(db)
            if count == 0:
                time.sleep(SCAN_POLL_INTERVAL)
        except Exception:
            logger.exception("Orchestrator error")
            time.sleep(SCAN_POLL_INTERVAL)


if __name__ == "__main__":
    run_loop()
