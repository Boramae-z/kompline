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
