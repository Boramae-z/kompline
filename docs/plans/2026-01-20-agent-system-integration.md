# Agent System Integration Plan (main + giopaik)

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** giopaik 브랜치의 Worker 기반 폴링 아키텍처를 main 브랜치의 kompline 패키지에 통합하여 수평 확장 가능한 에이전트 시스템 구축

**Architecture:** Supabase를 Message Broker로 사용하는 Dispatcher-Worker-Reporter 패턴. main의 Retry/Fallback 로직과 ReportTemplate 시스템을 유지하면서 giopaik의 독립 프로세스 Worker 모델을 채택.

**Tech Stack:** Python 3.11+, Supabase (PostgreSQL), OpenAI API, FastAPI

---

## Phase 1: Database Schema & Client

### Task 1: Supabase 스키마 마이그레이션 파일 생성

**Files:**
- Create: `supabase/migrations/001_scan_tables.sql`

**Step 1: 마이그레이션 파일 작성**

```sql
-- 001_scan_tables.sql
-- Scan 요청 테이블
CREATE TABLE IF NOT EXISTS scans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    repo_url TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'QUEUED'
        CHECK (status IN ('QUEUED', 'PROCESSING', 'REPORT_GENERATING', 'COMPLETED', 'FAILED')),
    report_url TEXT,
    report_markdown TEXT
);

-- Scan과 Document 연결 테이블
CREATE TABLE IF NOT EXISTS scan_documents (
    scan_id UUID REFERENCES scans(id) ON DELETE CASCADE,
    document_id UUID NOT NULL,
    PRIMARY KEY (scan_id, document_id)
);

-- 개별 검증 결과 테이블
CREATE TABLE IF NOT EXISTS scan_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_id UUID REFERENCES scans(id) ON DELETE CASCADE,
    compliance_item_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'PASS', 'FAIL', 'ERROR')),
    reasoning TEXT,
    evidence TEXT,
    worker_id TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_scans_status ON scans(status);
CREATE INDEX IF NOT EXISTS idx_scan_results_status ON scan_results(status);
CREATE INDEX IF NOT EXISTS idx_scan_results_scan_id ON scan_results(scan_id);
```

**Step 2: 커밋**

```bash
git add supabase/migrations/001_scan_tables.sql
git commit -m "feat: add scan tables migration for worker architecture"
```

---

### Task 2: DatabaseClient 클래스 구현

**Files:**
- Create: `kompline/persistence/scan_store.py`
- Modify: `kompline/persistence/__init__.py`

**Step 1: ScanStore 테스트 작성**

```python
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
```

**Step 2: 테스트 실행하여 실패 확인**

```bash
pytest tests/persistence/test_scan_store.py -v
```
Expected: FAIL with "No module named 'kompline.persistence.scan_store'"

**Step 3: ScanStore 구현**

```python
# kompline/persistence/scan_store.py
"""Scan persistence for worker-based architecture."""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from supabase import Client


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ScanStore:
    """Supabase-backed store for scan operations."""

    client: Client

    def list_queued_scans(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get scans waiting to be processed."""
        response = (
            self.client.table("scans")
            .select("*")
            .eq("status", "QUEUED")
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return response.data or []

    def get_scan(self, scan_id: str) -> dict[str, Any] | None:
        """Get a single scan by ID."""
        response = (
            self.client.table("scans")
            .select("*")
            .eq("id", scan_id)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else None

    def get_scan_documents(self, scan_id: str) -> list[str]:
        """Get document IDs linked to a scan."""
        response = (
            self.client.table("scan_documents")
            .select("document_id")
            .eq("scan_id", scan_id)
            .execute()
        )
        return [row["document_id"] for row in (response.data or [])]

    def create_scan_results(
        self,
        scan_id: str,
        compliance_items: Iterable[dict[str, Any]]
    ) -> int:
        """Create pending scan results for each compliance item."""
        rows = [
            {
                "scan_id": scan_id,
                "compliance_item_id": item["id"],
                "status": "PENDING",
                "updated_at": _utc_now_iso(),
            }
            for item in compliance_items
        ]
        if not rows:
            return 0
        self.client.table("scan_results").insert(rows).execute()
        return len(rows)

    def update_scan_status(
        self,
        scan_id: str,
        status: str,
        report_url: str | None = None,
        report_markdown: str | None = None,
    ) -> None:
        """Update scan status and optional report fields."""
        payload: dict[str, Any] = {"status": status}
        if report_url is not None:
            payload["report_url"] = report_url
        if report_markdown is not None:
            payload["report_markdown"] = report_markdown
        self.client.table("scans").update(payload).eq("id", scan_id).execute()

    def list_pending_results(self, limit: int = 1) -> list[dict[str, Any]]:
        """Get pending scan results for processing."""
        response = (
            self.client.table("scan_results")
            .select("*")
            .eq("status", "PENDING")
            .order("updated_at", desc=False)
            .limit(limit)
            .execute()
        )
        return response.data or []

    def update_scan_result(
        self,
        result_id: str,
        status: str,
        reasoning: str | None,
        evidence: str | None,
        worker_id: str | None = None,
    ) -> None:
        """Update a scan result with validation outcome."""
        payload = {
            "status": status,
            "reasoning": reasoning,
            "evidence": evidence,
            "updated_at": _utc_now_iso(),
        }
        if worker_id:
            payload["worker_id"] = worker_id
        self.client.table("scan_results").update(payload).eq("id", result_id).execute()

    def list_active_scans(self, statuses: Iterable[str]) -> list[dict[str, Any]]:
        """Get scans in specified statuses."""
        status_list = list(statuses)
        if not status_list:
            return []
        response = (
            self.client.table("scans")
            .select("*")
            .in_("status", status_list)
            .order("created_at", desc=False)
            .execute()
        )
        return response.data or []

    def list_scan_results(self, scan_id: str) -> list[dict[str, Any]]:
        """Get all results for a scan."""
        response = (
            self.client.table("scan_results")
            .select("*")
            .eq("scan_id", scan_id)
            .execute()
        )
        return response.data or []

    def count_pending_results(self, scan_id: str) -> int:
        """Count pending results for a scan."""
        response = (
            self.client.table("scan_results")
            .select("id", count="exact")
            .eq("scan_id", scan_id)
            .eq("status", "PENDING")
            .execute()
        )
        return response.count or 0
```

**Step 4: 테스트 실행하여 통과 확인**

```bash
pytest tests/persistence/test_scan_store.py -v
```
Expected: PASS

**Step 5: __init__.py 업데이트**

```python
# kompline/persistence/__init__.py 에 추가
from kompline.persistence.scan_store import ScanStore

__all__ = [..., "ScanStore"]
```

**Step 6: 커밋**

```bash
git add kompline/persistence/scan_store.py tests/persistence/test_scan_store.py kompline/persistence/__init__.py
git commit -m "feat: add ScanStore for worker-based scan persistence"
```

---

## Phase 2: Worker 프로세스 구현

### Task 3: Worker 설정 모듈

**Files:**
- Create: `kompline/workers/config.py`
- Create: `kompline/workers/__init__.py`

**Step 1: config.py 작성**

```python
# kompline/workers/config.py
"""Configuration for worker processes."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_KEY = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Polling intervals (seconds)
ORCHESTRATOR_POLL_INTERVAL = _get_int("ORCHESTRATOR_POLL_INTERVAL", 5)
VALIDATOR_POLL_INTERVAL = _get_int("VALIDATOR_POLL_INTERVAL", 5)
REPORTER_POLL_INTERVAL = _get_int("REPORTER_POLL_INTERVAL", 5)

# Worker identity
WORKER_ID = os.getenv("WORKER_ID", "worker-1")

# Retry configuration
MAX_RETRIES = _get_int("MAX_RETRIES", 3)
RETRY_BASE_DELAY = _get_int("RETRY_BASE_DELAY", 1)
RETRY_MAX_DELAY = _get_int("RETRY_MAX_DELAY", 30)

# Limits
MAX_EVIDENCE_CHARS = _get_int("MAX_EVIDENCE_CHARS", 4000)
MAX_CONTEXT_CHARS = _get_int("MAX_CONTEXT_CHARS", 12000)

# Paths
REPO_CACHE_DIR = Path(os.getenv("REPO_CACHE_DIR", ".cache/repos"))
REPORT_OUTPUT_DIR = Path(os.getenv("REPORT_OUTPUT_DIR", "reports"))
```

**Step 2: __init__.py 작성**

```python
# kompline/workers/__init__.py
"""Worker processes for distributed compliance auditing."""

from kompline.workers.config import (
    ORCHESTRATOR_POLL_INTERVAL,
    VALIDATOR_POLL_INTERVAL,
    REPORTER_POLL_INTERVAL,
    WORKER_ID,
)

__all__ = [
    "ORCHESTRATOR_POLL_INTERVAL",
    "VALIDATOR_POLL_INTERVAL",
    "REPORTER_POLL_INTERVAL",
    "WORKER_ID",
]
```

**Step 3: 커밋**

```bash
git add kompline/workers/
git commit -m "feat: add worker configuration module"
```

---

### Task 4: Orchestrator Worker 구현

**Files:**
- Create: `kompline/workers/orchestrator.py`
- Create: `tests/workers/test_orchestrator.py`

**Step 1: 테스트 작성**

```python
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
```

**Step 2: 테스트 실행 (실패 확인)**

```bash
pytest tests/workers/test_orchestrator.py -v
```
Expected: FAIL

**Step 3: OrchestratorWorker 구현**

```python
# kompline/workers/orchestrator.py
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
```

**Step 4: ScanStore에 get_compliance_items 메서드 추가**

```python
# kompline/persistence/scan_store.py 에 추가
def get_compliance_items(self, document_ids: Iterable[str]) -> list[dict[str, Any]]:
    """Get compliance items for given documents."""
    ids = list(document_ids)
    if not ids:
        return []
    response = (
        self.client.table("compliance_items")
        .select("id, document_id, item_text, item_type, section, page")
        .in_("document_id", ids)
        .execute()
    )
    return response.data or []
```

**Step 5: 테스트 실행 (통과 확인)**

```bash
pytest tests/workers/test_orchestrator.py -v
```
Expected: PASS

**Step 6: 커밋**

```bash
git add kompline/workers/orchestrator.py tests/workers/test_orchestrator.py kompline/persistence/scan_store.py
git commit -m "feat: add orchestrator worker for scan dispatching"
```

---

### Task 5: Validator Worker 구현 (main의 Retry 로직 통합)

**Files:**
- Create: `kompline/workers/validator.py`
- Create: `tests/workers/test_validator.py`

**Step 1: 테스트 작성**

```python
# tests/workers/test_validator.py
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from kompline.workers.validator import ValidatorWorker, RetryConfig


class TestValidatorWorker:
    def test_validates_pending_result(self):
        mock_store = MagicMock()
        mock_store.list_pending_results.return_value = [
            {"id": "result-1", "scan_id": "scan-1", "compliance_item_id": 1}
        ]
        mock_store.get_scan.return_value = {"id": "scan-1", "repo_url": "https://github.com/test/repo"}
        mock_store.get_compliance_item.return_value = {"id": 1, "item_text": "Check encryption"}

        with patch("kompline.workers.validator.validate_compliance_item") as mock_validate:
            mock_validate.return_value = ("PASS", "Encryption found", "AES-256 in config")

            worker = ValidatorWorker(mock_store)
            processed = worker.run_once()

        assert processed == 1
        mock_store.update_scan_result.assert_called_once()

    def test_retry_config_exponential_backoff(self):
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)

        assert config.get_delay(0) == 1.0
        assert config.get_delay(1) == 2.0
        assert config.get_delay(2) == 4.0

    def test_handles_validation_error_with_retry(self):
        mock_store = MagicMock()
        mock_store.list_pending_results.return_value = [
            {"id": "result-1", "scan_id": "scan-1", "compliance_item_id": 1}
        ]
        mock_store.get_scan.return_value = {"id": "scan-1", "repo_url": "https://github.com/test/repo"}
        mock_store.get_compliance_item.return_value = {"id": 1, "item_text": "Check encryption"}

        with patch("kompline.workers.validator.validate_compliance_item") as mock_validate:
            mock_validate.side_effect = [Exception("API error"), ("PASS", "OK", "evidence")]

            worker = ValidatorWorker(mock_store, retry_config=RetryConfig(max_retries=1, jitter=False))
            processed = worker.run_once()

        assert processed == 1
        assert mock_validate.call_count == 2
```

**Step 2: 테스트 실행 (실패 확인)**

```bash
pytest tests/workers/test_validator.py -v
```
Expected: FAIL

**Step 3: ValidatorWorker 구현**

```python
# kompline/workers/validator.py
"""Validator worker - validates compliance items against repositories."""

import logging
import random
import time
from dataclasses import dataclass
from pathlib import Path

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
    """Configuration for retry behavior."""
    max_retries: int = MAX_RETRIES
    base_delay: float = RETRY_BASE_DELAY
    max_delay: float = RETRY_MAX_DELAY
    exponential_base: float = 2.0
    jitter: bool = True

    def get_delay(self, attempt: int) -> float:
        """Calculate delay using exponential backoff."""
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        if self.jitter:
            delay = delay * (0.5 + random.random())
        return delay


def validate_compliance_item(
    repo_url: str,
    compliance_text: str,
) -> tuple[str, str, str | None]:
    """Validate a compliance item against a repository.

    Returns:
        Tuple of (status, reasoning, evidence)
    """
    # Import here to avoid circular dependencies
    from kompline.agents.audit_agent import AuditAgent
    from kompline.agents.code_search_agent import CodeSearchAgent

    # Use code search to find relevant evidence
    search_agent = CodeSearchAgent()
    search_results = search_agent.search(repo_url, compliance_text)

    # Use audit agent to evaluate compliance
    audit_agent = AuditAgent()
    result = audit_agent.evaluate_text(
        compliance_text=compliance_text,
        code_context=search_results,
        max_context=MAX_CONTEXT_CHARS,
    )

    evidence = result.get("evidence", "")
    if evidence and len(evidence) > MAX_EVIDENCE_CHARS:
        evidence = evidence[:MAX_EVIDENCE_CHARS] + "...(truncated)"

    return (
        result.get("status", "ERROR"),
        result.get("reasoning", "No reasoning provided"),
        evidence or None,
    )


class ValidatorWorker:
    """Validates pending scan results."""

    def __init__(
        self,
        store: ScanStore,
        retry_config: RetryConfig | None = None,
    ):
        self.store = store
        self.retry_config = retry_config or RetryConfig()

    def _validate_with_retry(
        self,
        repo_url: str,
        compliance_text: str,
    ) -> tuple[str, str, str | None]:
        """Validate with retry logic."""
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
                        attempt + 1, self.retry_config.max_retries, delay, e
                    )
                    time.sleep(delay)
                else:
                    logger.error("Validation failed after %d retries: %s",
                                self.retry_config.max_retries, e)

        return ("ERROR", f"Validation failed: {last_error}", None)

    def run_once(self) -> int:
        """Process one pending result."""
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
            status, reasoning, evidence = self._validate_with_retry(repo_url, compliance_text)

            self.store.update_scan_result(
                result_id, status, f"[{WORKER_ID}] {reasoning}", evidence, WORKER_ID
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
```

**Step 4: ScanStore에 get_compliance_item 메서드 추가**

```python
# kompline/persistence/scan_store.py 에 추가
def get_compliance_item(self, compliance_item_id: int) -> dict[str, Any] | None:
    """Get a single compliance item by ID."""
    response = (
        self.client.table("compliance_items")
        .select("id, document_id, item_text, item_type, section, page")
        .eq("id", compliance_item_id)
        .limit(1)
        .execute()
    )
    return response.data[0] if response.data else None
```

**Step 5: 테스트 실행 (통과 확인)**

```bash
pytest tests/workers/test_validator.py -v
```
Expected: PASS

**Step 6: 커밋**

```bash
git add kompline/workers/validator.py tests/workers/test_validator.py kompline/persistence/scan_store.py
git commit -m "feat: add validator worker with retry logic"
```

---

### Task 6: Reporter Worker 구현

**Files:**
- Create: `kompline/workers/reporter.py`
- Create: `tests/workers/test_reporter.py`

**Step 1: 테스트 작성**

```python
# tests/workers/test_reporter.py
import pytest
from unittest.mock import MagicMock, patch
from kompline.workers.reporter import ReporterWorker


class TestReporterWorker:
    def test_generates_report_when_all_results_complete(self):
        mock_store = MagicMock()
        mock_store.list_active_scans.return_value = [
            {"id": "scan-1", "repo_url": "https://github.com/test/repo", "status": "PROCESSING"}
        ]
        mock_store.count_pending_results.return_value = 0
        mock_store.list_scan_results.return_value = [
            {"id": "result-1", "status": "PASS", "reasoning": "OK", "evidence": "found"}
        ]

        worker = ReporterWorker(mock_store)
        processed = worker.run_once()

        assert processed == 1
        mock_store.update_scan_status.assert_called()

    def test_skips_scan_with_pending_results(self):
        mock_store = MagicMock()
        mock_store.list_active_scans.return_value = [
            {"id": "scan-1", "repo_url": "https://github.com/test/repo"}
        ]
        mock_store.count_pending_results.return_value = 5

        worker = ReporterWorker(mock_store)
        processed = worker.run_once()

        assert processed == 0
```

**Step 2: 테스트 실행 (실패 확인)**

```bash
pytest tests/workers/test_reporter.py -v
```
Expected: FAIL

**Step 3: ReporterWorker 구현 (main의 ReportGenerator 활용)**

```python
# kompline/workers/reporter.py
"""Reporter worker - generates compliance reports."""

import logging
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from kompline.persistence.scan_store import ScanStore
from kompline.workers.config import REPORTER_POLL_INTERVAL, REPORT_OUTPUT_DIR
from kompline.models import Finding, FindingStatus, FindingSummary

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _status_to_finding_status(status: str) -> FindingStatus:
    """Convert string status to FindingStatus enum."""
    mapping = {
        "PASS": FindingStatus.PASS,
        "FAIL": FindingStatus.FAIL,
        "ERROR": FindingStatus.REVIEW,
        "PENDING": FindingStatus.REVIEW,
    }
    return mapping.get(status, FindingStatus.REVIEW)


class ReporterWorker:
    """Generates reports for completed scans."""

    def __init__(self, store: ScanStore):
        self.store = store

    def _generate_markdown(
        self,
        scan: dict[str, Any],
        results: list[dict[str, Any]],
    ) -> str:
        """Generate a markdown report."""
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
            emoji = {"PASS": "✅", "FAIL": "❌", "ERROR": "⚠️"}.get(status, "❓")
            lines.append(f"- {emoji} **{status}**: {count}")

        lines.extend(["", "## Detailed Results", ""])

        for result in results:
            status = result.get("status", "UNKNOWN")
            emoji = {"PASS": "✅", "FAIL": "❌", "ERROR": "⚠️"}.get(status, "❓")

            lines.append(f"### {emoji} Item {result.get('compliance_item_id')}")
            lines.append(f"- **Status**: {status}")
            lines.append(f"- **Reasoning**: {result.get('reasoning', 'N/A')}")

            evidence = result.get("evidence")
            if evidence:
                lines.append(f"- **Evidence**:")
                lines.append(f"  ```")
                lines.append(f"  {evidence}")
                lines.append(f"  ```")
            lines.append("")

        return "\n".join(lines)

    def _generate_byeolji5(
        self,
        scan: dict[str, Any],
        results: list[dict[str, Any]],
    ) -> str:
        """Generate 별지5 format report (Korean regulatory format)."""
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
                lines.append(f"    증거: {evidence[:200]}{'...' if len(evidence) > 200 else ''}")

        lines.extend([
            "",
            "=" * 60,
            "끝",
            "=" * 60,
        ])

        return "\n".join(lines)

    def _save_report(self, scan_id: str, content: str) -> Path:
        """Save report to file."""
        REPORT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORT_OUTPUT_DIR / f"scan-{scan_id}.md"
        report_path.write_text(content, encoding="utf-8")
        return report_path

    def run_once(self) -> int:
        """Process completed scans and generate reports."""
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
        """Run the reporter in a continuous loop."""
        logger.info("Reporter worker started")
        while True:
            try:
                count = self.run_once()
                if count == 0:
                    time.sleep(REPORTER_POLL_INTERVAL)
            except Exception:
                logger.exception("Reporter error")
                time.sleep(REPORTER_POLL_INTERVAL)
```

**Step 4: 테스트 실행 (통과 확인)**

```bash
pytest tests/workers/test_reporter.py -v
```
Expected: PASS

**Step 5: 커밋**

```bash
git add kompline/workers/reporter.py tests/workers/test_reporter.py
git commit -m "feat: add reporter worker with byeolji5 format support"
```

---

## Phase 3: CLI 및 진입점

### Task 7: Worker CLI 명령어

**Files:**
- Create: `kompline/cli/workers.py`
- Modify: `kompline/cli/__init__.py` (또는 main CLI)

**Step 1: CLI 구현**

```python
# kompline/cli/workers.py
"""CLI commands for running workers."""

import logging
import click
from supabase import create_client

from kompline.persistence.scan_store import ScanStore
from kompline.workers.config import SUPABASE_URL, SUPABASE_KEY
from kompline.workers.orchestrator import OrchestratorWorker
from kompline.workers.validator import ValidatorWorker
from kompline.workers.reporter import ReporterWorker


def _get_store() -> ScanStore:
    """Create a ScanStore instance."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise click.ClickException("Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY.")
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return ScanStore(client)


@click.group()
def workers():
    """Run worker processes."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )


@workers.command()
def orchestrator():
    """Run the orchestrator worker."""
    store = _get_store()
    worker = OrchestratorWorker(store)
    worker.run_loop()


@workers.command()
def validator():
    """Run the validator worker."""
    store = _get_store()
    worker = ValidatorWorker(store)
    worker.run_loop()


@workers.command()
def reporter():
    """Run the reporter worker."""
    store = _get_store()
    worker = ReporterWorker(store)
    worker.run_loop()


@workers.command()
@click.option("--orchestrator/--no-orchestrator", default=True, help="Run orchestrator")
@click.option("--validators", default=1, help="Number of validator workers")
@click.option("--reporter/--no-reporter", default=True, help="Run reporter")
def all(orchestrator: bool, validators: int, reporter: bool):
    """Run all workers in separate threads."""
    import threading

    store = _get_store()
    threads = []

    if orchestrator:
        t = threading.Thread(target=OrchestratorWorker(store).run_loop, daemon=True)
        t.start()
        threads.append(t)
        click.echo("Started orchestrator worker")

    for i in range(validators):
        t = threading.Thread(target=ValidatorWorker(store).run_loop, daemon=True)
        t.start()
        threads.append(t)
        click.echo(f"Started validator worker {i+1}")

    if reporter:
        t = threading.Thread(target=ReporterWorker(store).run_loop, daemon=True)
        t.start()
        threads.append(t)
        click.echo("Started reporter worker")

    click.echo(f"Running {len(threads)} workers. Press Ctrl+C to stop.")

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        click.echo("\nShutting down workers...")
```

**Step 2: pyproject.toml에 CLI 진입점 추가**

```toml
# pyproject.toml [project.scripts] 섹션에 추가
[project.scripts]
kompline-workers = "kompline.cli.workers:workers"
```

**Step 3: 커밋**

```bash
git add kompline/cli/workers.py pyproject.toml
git commit -m "feat: add CLI commands for running workers"
```

---

## Phase 4: API 통합

### Task 8: Scan 생성 API 엔드포인트

**Files:**
- Modify: `api/main.py`

**Step 1: 테스트 작성**

```python
# tests/api/test_scan_endpoints.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch


class TestScanEndpoints:
    def test_create_scan_returns_scan_id(self, client):
        with patch("api.main.get_scan_store") as mock_get_store:
            mock_store = MagicMock()
            mock_store.create_scan.return_value = "scan-123"
            mock_get_store.return_value = mock_store

            response = client.post("/scans", json={
                "repo_url": "https://github.com/test/repo",
                "document_ids": ["doc-1", "doc-2"]
            })

            assert response.status_code == 201
            assert response.json()["scan_id"] == "scan-123"

    def test_get_scan_status(self, client):
        with patch("api.main.get_scan_store") as mock_get_store:
            mock_store = MagicMock()
            mock_store.get_scan.return_value = {
                "id": "scan-123",
                "status": "PROCESSING",
                "repo_url": "https://github.com/test/repo"
            }
            mock_get_store.return_value = mock_store

            response = client.get("/scans/scan-123")

            assert response.status_code == 200
            assert response.json()["status"] == "PROCESSING"
```

**Step 2: API 엔드포인트 구현**

```python
# api/main.py 에 추가
from pydantic import BaseModel
from kompline.persistence.scan_store import ScanStore
from kompline.workers.config import SUPABASE_URL, SUPABASE_KEY


class CreateScanRequest(BaseModel):
    repo_url: str
    document_ids: list[str]


class ScanResponse(BaseModel):
    scan_id: str
    status: str
    repo_url: str
    report_url: str | None = None
    report_markdown: str | None = None


def get_scan_store() -> ScanStore:
    from supabase import create_client
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return ScanStore(client)


@app.post("/scans", status_code=201)
async def create_scan(request: CreateScanRequest) -> dict:
    """Create a new compliance scan."""
    store = get_scan_store()
    scan_id = store.create_scan(request.repo_url, request.document_ids)
    return {"scan_id": scan_id, "status": "QUEUED"}


@app.get("/scans/{scan_id}")
async def get_scan(scan_id: str) -> ScanResponse:
    """Get scan status and results."""
    store = get_scan_store()
    scan = store.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return ScanResponse(
        scan_id=scan["id"],
        status=scan["status"],
        repo_url=scan["repo_url"],
        report_url=scan.get("report_url"),
        report_markdown=scan.get("report_markdown"),
    )


@app.get("/scans/{scan_id}/results")
async def get_scan_results(scan_id: str) -> list[dict]:
    """Get detailed results for a scan."""
    store = get_scan_store()
    results = store.list_scan_results(scan_id)
    return results
```

**Step 3: ScanStore에 create_scan 메서드 추가**

```python
# kompline/persistence/scan_store.py 에 추가
def create_scan(self, repo_url: str, document_ids: list[str]) -> str:
    """Create a new scan and link documents."""
    # Insert scan
    response = (
        self.client.table("scans")
        .insert({"repo_url": repo_url, "status": "QUEUED"})
        .execute()
    )
    scan_id = response.data[0]["id"]

    # Link documents
    if document_ids:
        rows = [{"scan_id": scan_id, "document_id": doc_id} for doc_id in document_ids]
        self.client.table("scan_documents").insert(rows).execute()

    return scan_id
```

**Step 4: 커밋**

```bash
git add api/main.py kompline/persistence/scan_store.py tests/api/test_scan_endpoints.py
git commit -m "feat: add scan creation and status API endpoints"
```

---

## Phase 5: 정리 및 문서화

### Task 9: workers __init__.py 업데이트

**Files:**
- Modify: `kompline/workers/__init__.py`

```python
# kompline/workers/__init__.py
"""Worker processes for distributed compliance auditing."""

from kompline.workers.config import (
    ORCHESTRATOR_POLL_INTERVAL,
    VALIDATOR_POLL_INTERVAL,
    REPORTER_POLL_INTERVAL,
    WORKER_ID,
)
from kompline.workers.orchestrator import OrchestratorWorker
from kompline.workers.validator import ValidatorWorker, RetryConfig
from kompline.workers.reporter import ReporterWorker

__all__ = [
    "OrchestratorWorker",
    "ValidatorWorker",
    "ReporterWorker",
    "RetryConfig",
    "ORCHESTRATOR_POLL_INTERVAL",
    "VALIDATOR_POLL_INTERVAL",
    "REPORTER_POLL_INTERVAL",
    "WORKER_ID",
]
```

### Task 10: 전체 테스트 실행

```bash
pytest tests/ -v --tb=short
```

### Task 11: 최종 커밋

```bash
git add .
git commit -m "feat: complete worker-based agent system integration"
```

---

## 실행 방법

### 개발 환경

```bash
# 1. 환경 변수 설정
export SUPABASE_URL="your-supabase-url"
export SUPABASE_KEY="your-supabase-key"
export OPENAI_API_KEY="your-openai-key"

# 2. 모든 워커 실행
python -m kompline.cli.workers all

# 또는 개별 실행
python -m kompline.cli.workers orchestrator &
python -m kompline.cli.workers validator &
python -m kompline.cli.workers reporter &
```

### 프로덕션 환경 (Docker)

```yaml
# docker-compose.yml
services:
  orchestrator:
    build: .
    command: kompline-workers orchestrator
    environment:
      - SUPABASE_URL
      - SUPABASE_KEY
      - OPENAI_API_KEY

  validator-1:
    build: .
    command: kompline-workers validator
    environment:
      - WORKER_ID=validator-1
      - SUPABASE_URL
      - SUPABASE_KEY
      - OPENAI_API_KEY

  validator-2:
    build: .
    command: kompline-workers validator
    environment:
      - WORKER_ID=validator-2
      - SUPABASE_URL
      - SUPABASE_KEY
      - OPENAI_API_KEY

  reporter:
    build: .
    command: kompline-workers reporter
    environment:
      - SUPABASE_URL
      - SUPABASE_KEY
```

---

## 체크리스트

- [ ] Phase 1: Database Schema & Client
  - [ ] Task 1: Supabase 스키마 마이그레이션
  - [ ] Task 2: ScanStore 클래스 구현
- [ ] Phase 2: Worker 프로세스
  - [ ] Task 3: Worker 설정 모듈
  - [ ] Task 4: Orchestrator Worker
  - [ ] Task 5: Validator Worker (Retry 로직)
  - [ ] Task 6: Reporter Worker
- [ ] Phase 3: CLI
  - [ ] Task 7: Worker CLI 명령어
- [ ] Phase 4: API 통합
  - [ ] Task 8: Scan 생성 API
- [ ] Phase 5: 정리
  - [ ] Task 9: __init__.py 업데이트
  - [ ] Task 10: 전체 테스트
  - [ ] Task 11: 최종 커밋
