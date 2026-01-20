import io
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pdfplumber
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from supabase import Client, create_client

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s %(message)s",
)
logger = logging.getLogger("compliance_extractor")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4o-mini")

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_KEY = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY

MAX_CHARS_PER_REQUEST = int(os.getenv("MAX_CHARS_PER_REQUEST", "60000"))

_supabase_client: Optional[Client] = None

app = FastAPI(title="Compliance Extractor API")


def get_supabase() -> Client:
    global _supabase_client
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise HTTPException(status_code=500, detail="Supabase is not configured")
    if _supabase_client is None:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client


def _bytes_to_bytea_literal(data: bytes) -> str:
    return "\\x" + data.hex()


def detect_language(text: str) -> str:
    if re.search(r"[\uac00-\ud7a3]", text):
        return "ko"
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh"
    if re.search(r"[\u3040-\u30ff]", text):
        return "ja"
    return "unknown"


def pdf_to_markdown(pdf_bytes: bytes, filename: str) -> Tuple[str, int]:
    if not pdf_bytes:
        return "", 0

    pages_text: List[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for idx, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            text = text.strip()
            pages_text.append(f"## Page {idx}\n\n{text}\n")

    header = f"# {filename}\n\n"
    markdown = header + "\n".join(pages_text)
    return markdown.strip(), len(pages_text)


def split_markdown_by_pages(markdown: str) -> List[Tuple[Tuple[int, int], str]]:
    chunks: List[Tuple[Tuple[int, int], str]] = []
    if not markdown:
        return chunks

    pages = re.split(r"(?=^## Page \d+)", markdown, flags=re.MULTILINE)
    current: List[str] = []
    page_start = None
    page_end = None
    current_len = 0

    def flush():
        nonlocal current, page_start, page_end, current_len
        if current:
            chunks.append(((page_start or 1, page_end or page_start or 1), "".join(current)))
        current = []
        page_start = None
        page_end = None
        current_len = 0

    for block in pages:
        if not block.strip():
            continue
        match = re.search(r"^## Page (\d+)", block, flags=re.MULTILINE)
        page_num = int(match.group(1)) if match else None
        block_len = len(block)

        if current_len + block_len > MAX_CHARS_PER_REQUEST and current:
            flush()

        if page_num is not None:
            if page_start is None:
                page_start = page_num
            page_end = page_num

        current.append(block)
        current_len += block_len

    flush()
    return chunks


def _extract_response_text(payload: Dict[str, Any]) -> str:
    if payload.get("output_text"):
        return payload["output_text"]
    texts: List[str] = []
    for item in payload.get("output", []):
        if item.get("type") != "message":
            continue
        for part in item.get("content", []):
            if part.get("type") == "output_text" and part.get("text"):
                texts.append(part["text"])
    return "\n".join(texts).strip()


def call_openai_json(instructions: str, input_text: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")

    payload = {
        "model": GPT_MODEL,
        "instructions": instructions,
        "input": input_text,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "compliance_extract",
                "schema": schema,
                "strict": True,
            }
        },
        "temperature": 0,
    }

    last_error: Optional[str] = None
    for attempt in range(3):
        logger.debug(
            "OpenAI request attempt=%s model=%s input_chars=%s schema_keys=%s",
            attempt + 1,
            GPT_MODEL,
            len(input_text),
            list(schema.get("properties", {}).keys()),
        )
        response = requests.post(
            f"{OPENAI_BASE_URL}/responses",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=180,
        )

        logger.debug(
            "OpenAI response status=%s headers=%s body=%s",
            response.status_code,
            dict(response.headers),
            response.text[:4000],
        )

        if response.status_code == 200:
            payload_json = response.json()
            text = _extract_response_text(payload_json)
            try:
                return json.loads(text)
            except json.JSONDecodeError as exc:
                last_error = f"Invalid JSON from model: {exc}"
                break

        last_error = f"OpenAI responses error: {response.status_code} {response.text}"
        if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
            time.sleep(2 * (attempt + 1))
            continue
        break

    raise HTTPException(status_code=502, detail=last_error or "OpenAI responses error")


def extract_compliance_items(markdown_text: str) -> Tuple[str, List[Dict[str, Any]]]:
    if not markdown_text.strip():
        return "", []

    instructions = (
        "You extract ALL regulatory and compliance requirements from the provided document. "
        "Do NOT translate or paraphrase. Keep the original language and wording. "
        "Include obligations, prohibitions, permissions, reporting requirements, retention rules, "
        "security controls, audit requirements, penalties, and definitions that function as rules. "
        "Preserve numbering and section references when present. "
        "If a rule spans multiple sentences, include the full text. "
        "If a compliance item references a term that is defined elsewhere (e.g., \"~란 ~를 말한다\"), "
        "include the relevant definition verbatim in the item's notes field so each row is self-contained. "
        "Do NOT create a separate item just for definitions unless the definition itself imposes a rule. "
        "EXCLUDE application forms, cover letters, pledges, signatures, addresses, "
        "applicant/company identification fields, and any template/blank fields "
        "intended to be filled out (e.g., 신청일, 주소, 상호, 대표이사, 인, 서명). "
        "If a section is purely a form or declaration without regulatory requirements, omit it. "
        "Return JSON only."
    )

    schema = {
        "type": "object",
        "properties": {
            "document_title": {"type": ["string", "null"]},
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "type": {
                            "type": "string",
                            "enum": [
                                "obligation",
                                "prohibition",
                                "permission",
                                "definition",
                                "procedure",
                                "other",
                            ],
                        },
                        "page": {"type": ["integer", "null"]},
                        "section": {"type": ["string", "null"]},
                        "notes": {"type": ["string", "null"]},
                    },
                    "required": ["text", "type", "page", "section", "notes"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["document_title", "items"],
        "additionalProperties": False,
    }

    chunks = split_markdown_by_pages(markdown_text)
    all_items: List[Dict[str, Any]] = []
    document_title = ""

    for page_range, chunk in chunks:
        page_label = f"pages {page_range[0]}-{page_range[1]}"
        chunk_input = (
            f"Extract items from {page_label}. "
            "If you can identify page numbers or sections, fill them.\n\n"
            f"{chunk}"
        )
        result = call_openai_json(instructions, chunk_input, schema)
        if not document_title and result.get("document_title"):
            document_title = result.get("document_title", "")
        items = result.get("items", [])
        if items:
            all_items.extend(items)

    deduped: List[Dict[str, Any]] = []
    seen = set()
    for item in all_items:
        text = (item.get("text") or "").strip()
        if not text:
            continue
        key = re.sub(r"\s+", " ", text).strip().lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return document_title, deduped


def insert_document(
    filename: str,
    markdown_text: str,
    pdf_bytes: bytes,
    page_count: int,
    language: str,
) -> Dict[str, Any]:
    supabase = get_supabase()
    payload = {
        "filename": filename,
        "markdown_text": markdown_text,
        "pdf_blob": _bytes_to_bytea_literal(pdf_bytes),
        "page_count": page_count,
        "language": language,
    }
    insert = supabase.table("documents").insert(payload).execute()
    if not insert.data:
        raise HTTPException(status_code=500, detail="Failed to insert document")
    return insert.data[0]


def insert_compliance_items(
    document_id: int,
    document_title: str,
    language: str,
    items: List[Dict[str, Any]],
) -> int:
    supabase = get_supabase()

    rows: List[Dict[str, Any]] = []
    for idx, item in enumerate(items, start=1):
        row = {
            "document_id": document_id,
            "document_title": document_title,
            "item_index": idx,
            "item_type": item.get("type"),
            "item_text": item.get("text"),
            "page": item.get("page"),
            "section": item.get("section"),
            "item_json": item,
            "language": language,
        }
        rows.append(row)

    if rows:
        supabase.table("compliance_items").insert(rows).execute()
    return len(rows)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/upload")
def upload(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    for file in files:
        filename = file.filename or ""
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"Unsupported file: {filename}")

        pdf_bytes = file.file.read()
        if not pdf_bytes:
            raise HTTPException(status_code=400, detail=f"Empty file: {filename}")

        markdown_text, page_count = pdf_to_markdown(pdf_bytes, filename)
        language = detect_language(markdown_text)

        document = insert_document(filename, markdown_text, pdf_bytes, page_count, language)
        document_id = document.get("id")
        if document_id is None:
            raise HTTPException(status_code=500, detail="Document insert missing id")

        document_title, items = extract_compliance_items(markdown_text)
        item_count = insert_compliance_items(
            document_id=document_id,
            document_title=document_title,
            language=language,
            items=items,
        )

        results.append(
            {
                "document_id": document_id,
                "filename": filename,
                "page_count": page_count,
                "language": language,
                "compliance_items": item_count,
            }
        )

    return {"results": results}
