import os
from pathlib import Path

from dotenv import load_dotenv


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent

load_dotenv(ROOT_DIR / ".env")
load_dotenv(BASE_DIR / ".env")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_KEY = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4o-mini")

SCAN_POLL_INTERVAL = _get_int("SCAN_POLL_INTERVAL", 5)
RESULT_POLL_INTERVAL = _get_int("RESULT_POLL_INTERVAL", 5)
REPORT_POLL_INTERVAL = _get_int("REPORT_POLL_INTERVAL", 5)

WORKER_ID = os.getenv("WORKER_ID", "validator-1")

REPO_CACHE_DIR = Path(os.getenv("REPO_CACHE_DIR", str(BASE_DIR / "repo_cache")))
REPO_CLONE_DEPTH = _get_int("REPO_CLONE_DEPTH", 1)

REPORT_OUTPUT_DIR = Path(os.getenv("REPORT_OUTPUT_DIR", str(BASE_DIR / "reports")))

MAX_EVIDENCE_CHARS = _get_int("MAX_EVIDENCE_CHARS", 4000)
MAX_CONTEXT_CHARS = _get_int("MAX_CONTEXT_CHARS", 12000)
MAX_SEARCH_HITS = _get_int("MAX_SEARCH_HITS", 50)
MAX_FILE_SAMPLES = _get_int("MAX_FILE_SAMPLES", 10)
