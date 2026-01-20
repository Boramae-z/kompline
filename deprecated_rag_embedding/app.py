import base64
import json
import logging
import os
from pathlib import Path
from typing import List, Dict, Any

import faiss
import numpy as np
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.responses import Response
from supabase import create_client, Client
from threading import Lock

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PDF_ROOT = BASE_DIR
UPLOAD_DIR = BASE_DIR / "uploads"
INDEX_PATH = BASE_DIR / "index.faiss"

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("rag")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4o-mini")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
EMBEDDING_BATCH = int(os.getenv("EMBEDDING_BATCH", "64"))

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")
SUPABASE_KEY = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY
_supabase_client: Client | None = None
_ingest_lock = Lock()
_ingest_in_progress = False

app = FastAPI(title="RAG Embedding API")


def use_supabase() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


def get_supabase() -> Client:
    global _supabase_client
    if not use_supabase():
        raise HTTPException(status_code=500, detail="Supabase is not configured")
    if _supabase_client is None:
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client


def _bytes_to_bytea_literal(data: bytes) -> str:
    return "\\x" + data.hex()


def _decode_bytea(value: Any) -> bytes:
    if value is None:
        return b""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    if isinstance(value, str):
        if value.startswith("\\x"):
            return bytes.fromhex(value[2:])
        try:
            return base64.b64decode(value)
        except Exception:
            return value.encode("utf-8", errors="ignore")
    return b""


def embed_texts(texts: List[str]) -> np.ndarray:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")

    embeddings: List[List[float]] = []
    for i in range(0, len(texts), EMBEDDING_BATCH):
        batch = texts[i : i + EMBEDDING_BATCH]
        response = requests.post(
            f"{OPENAI_BASE_URL}/embeddings",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"model": MODEL_NAME, "input": batch},
            timeout=60,
        )
        if response.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"OpenAI embeddings error: {response.status_code} {response.text}",
            )
        data = response.json().get("data", [])
        data = sorted(data, key=lambda x: x.get("index", 0))
        embeddings.extend([item["embedding"] for item in data])

    vectors = np.asarray(embeddings, dtype="float32")
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.clip(norms, 1e-12, None)


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


def pdf_to_markdown_gpt(pdf_bytes: bytes, filename: str) -> str:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")
    if not pdf_bytes:
        return ""

    logger.info("Converting PDF to markdown: %s (%d bytes)", filename, len(pdf_bytes))
    file_b64 = base64.b64encode(pdf_bytes).decode("ascii")
    base_payload = {
        "model": GPT_MODEL,
        "input": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "filename": filename,
                        "file_data": file_b64,
                    },
                    {
                        "type": "input_text",
                        "text": (
                            "Convert the PDF to clean, structured markdown. "
                            "Preserve headings, lists, and tables when possible. "
                            "If page boundaries are clear, add headings like '## Page N'. "
                            "Return markdown only."
                        ),
                    },
                ],
            }
        ],
    }

    response = requests.post(
        f"{OPENAI_BASE_URL}/responses",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json=base_payload,
        timeout=120,
    )

    if response.status_code == 200:
        logger.info("PDF converted to markdown via file_data: %s", filename)
        return _extract_response_text(response.json())

    # Fallback: upload the PDF and retry with file_id
    if "file_data" in response.text and response.status_code == 400:
        logger.warning("file_data rejected, retrying with file_id: %s", filename)
        upload = requests.post(
            f"{OPENAI_BASE_URL}/files",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            files={"file": (filename, pdf_bytes, "application/pdf")},
            data={"purpose": "user_data"},
            timeout=60,
        )
        if upload.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"OpenAI file upload error: {upload.status_code} {upload.text}",
            )
        file_id = upload.json().get("id")
        if not file_id:
            raise HTTPException(status_code=502, detail="OpenAI file upload returned no id")
        retry_payload = {
            "model": GPT_MODEL,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_file", "file_id": file_id},
                        base_payload["input"][0]["content"][1],
                    ],
                }
            ],
        }
        retry = requests.post(
            f"{OPENAI_BASE_URL}/responses",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json=retry_payload,
            timeout=120,
        )
        if retry.status_code != 200:
            raise HTTPException(
                status_code=502,
                detail=f"OpenAI responses error: {retry.status_code} {retry.text}",
            )
        logger.info("PDF converted to markdown via file_id: %s", filename)
        return _extract_response_text(retry.json())

    raise HTTPException(
        status_code=502,
        detail=f"OpenAI responses error: {response.status_code} {response.text}",
    )


def generate_semantic_markdown(markdown_text: str) -> Dict[str, str]:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")
    if not markdown_text.strip():
        return {"semantic_markdown": "", "summary_markdown": ""}

    logger.info("Generating semantic/summary markdown")
    response = requests.post(
        f"{OPENAI_BASE_URL}/responses",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": GPT_MODEL,
            "instructions": (
                "You extract semantic information and summaries from markdown. "
                "Return valid JSON with keys semantic_markdown and summary_markdown. "
                "Use concise markdown, preserve key entities, dates, numbers, and headings."
            ),
            "input": markdown_text,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "semantic_extract",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "semantic_markdown": {"type": "string"},
                            "summary_markdown": {"type": "string"},
                        },
                        "required": ["semantic_markdown", "summary_markdown"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                }
            },
        },
        timeout=90,
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI responses error: {response.status_code} {response.text}",
        )
    text = _extract_response_text(response.json())
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"Invalid JSON from model: {exc}") from exc
    return {
        "semantic_markdown": data.get("semantic_markdown", ""),
        "summary_markdown": data.get("summary_markdown", ""),
    }


def generate_compliance_markdown(markdown_text: str) -> str:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")
    if not markdown_text.strip():
        return ""

    logger.info("Generating compliance markdown")
    response = requests.post(
        f"{OPENAI_BASE_URL}/responses",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": GPT_MODEL,
            "instructions": (
                "Extract compliance-relevant items from the markdown. "
                "Use the same language as the original document. "
                "Return valid JSON with key compliance_markdown. "
                "Include obligations, controls, data handling requirements, "
                "retention, security measures, and audit evidence cues. "
                "Use concise markdown."
            ),
            "input": markdown_text,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "compliance_extract",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "compliance_markdown": {"type": "string"},
                        },
                        "required": ["compliance_markdown"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                }
            },
        },
        timeout=120,
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI responses error: {response.status_code} {response.text}",
        )
    text = _extract_response_text(response.json())
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail=f"Invalid JSON from model: {exc}") from exc
    return data.get("compliance_markdown", "")


def find_pdfs(root: Path) -> List[Path]:
    return sorted([p for p in root.rglob("*.pdf") if p.is_file()])


def chunk_text(text: str, size: int, overlap: int) -> List[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []
    chunks = []
    start = 0
    while start < len(cleaned):
        end = min(start + size, len(cleaned))
        chunks.append(cleaned[start:end])
        if end == len(cleaned):
            break
        start = max(0, end - overlap)
    return chunks


def build_index(texts: List[str]) -> faiss.IndexFlatIP:
    embeddings = embed_texts(texts)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    return index


def save_index(index: faiss.IndexFlatIP) -> None:
    faiss.write_index(index, str(INDEX_PATH))


def load_index() -> faiss.IndexFlatIP:
    if not INDEX_PATH.exists():
        raise FileNotFoundError("index not found")
    return faiss.read_index(str(INDEX_PATH))


def reset_db() -> None:
    logger.warning("reset_db() is disabled; skipping destructive delete.")


def get_document_list() -> List[Dict[str, Any]]:
    supabase = get_supabase()
    docs = (
        supabase.table("documents")
        .select("id, filename, rel_path, created_at")
        .order("id", desc=True)
        .execute()
        .data
        or []
    )
    chunks = (
        supabase.table("chunks")
        .select("document_id")
        .execute()
        .data
        or []
    )
    counts: Dict[int, int] = {}
    for row in chunks:
        doc_id = row.get("document_id")
        if doc_id is not None:
            counts[doc_id] = counts.get(doc_id, 0) + 1
    return [
        {
            "id": d["id"],
            "filename": d["filename"],
            "rel_path": d["rel_path"],
            "created_at": d.get("created_at"),
            "chunk_count": counts.get(d["id"], 0),
        }
        for d in docs
    ]


def get_document_detail(doc_id: int) -> Dict[str, Any]:
    supabase = get_supabase()
    docs = (
        supabase.table("documents")
        .select(
            "id, filename, rel_path, markdown_text, semantic_markdown, summary_markdown, created_at"
        )
        .eq("id", doc_id)
        .execute()
        .data
    )
    if not docs:
        raise HTTPException(status_code=404, detail="Document not found")
    doc = docs[0]
    chunks = (
        supabase.table("chunks")
        .select("id, page, chunk_index, text")
        .eq("document_id", doc_id)
        .order("page", desc=False)
        .order("chunk_index", desc=False)
        .execute()
        .data
        or []
    )
    compliance = (
        supabase.table("compliance_items")
        .select("regulation_name, compliance_markdown, created_at")
        .eq("document_id", doc_id)
        .order("id", desc=True)
        .execute()
        .data
        or []
    )
    return {"document": doc, "compliance": compliance, "chunks": chunks}


def ingest_all() -> Dict[str, Any]:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    pdfs = find_pdfs(PDF_ROOT)
    if not pdfs:
        raise HTTPException(status_code=404, detail="No PDF files found under rag_embedding")

    global _ingest_in_progress
    with _ingest_lock:
        if _ingest_in_progress:
            raise HTTPException(status_code=409, detail="Ingest already in progress")
        _ingest_in_progress = True

    logger.info("Ingesting %d PDF(s) from %s", len(pdfs), PDF_ROOT)
    texts: List[str] = []
    chunk_ids: List[int] = []

    try:
        supabase = get_supabase()
        for pdf_path in pdfs:
            pdf_bytes = pdf_path.read_bytes()
            markdown_text = pdf_to_markdown_gpt(pdf_bytes, pdf_path.name)
            semantic = generate_semantic_markdown(markdown_text)
            compliance_markdown = generate_compliance_markdown(markdown_text)

            logger.info("Inserting document: %s", pdf_path.name)
            doc_payload = {
                "filename": pdf_path.name,
                "rel_path": str(pdf_path.relative_to(PDF_ROOT)),
                "pdf_blob": _bytes_to_bytea_literal(pdf_bytes),
                "markdown_text": markdown_text,
                "semantic_markdown": semantic["semantic_markdown"],
                "summary_markdown": semantic["summary_markdown"],
            }
            doc_insert = (
                supabase.table("documents").insert(doc_payload).execute().data or []
            )
            if not doc_insert:
                raise HTTPException(status_code=500, detail="Failed to insert document")
            document_id = doc_insert[0]["id"]

            logger.info("Inserting compliance item for document %s", document_id)
            supabase.table("compliance_items").insert(
                {
                    "document_id": document_id,
                    "regulation_name": "",
                    "compliance_markdown": compliance_markdown,
                }
            ).execute()

            for chunk_idx, chunk in enumerate(
                chunk_text(markdown_text, CHUNK_SIZE, CHUNK_OVERLAP), start=1
            ):
                if chunk_idx == 1:
                    logger.info("Inserting chunks for document %s", document_id)
                chunk_payload = {
                    "document_id": document_id,
                    "page": 0,
                    "chunk_index": chunk_idx,
                    "text": chunk,
                }
                chunk_insert = (
                    supabase.table("chunks").insert(chunk_payload).execute().data or []
                )
                if not chunk_insert:
                    raise HTTPException(status_code=500, detail="Failed to insert chunk")
                chunk_id = chunk_insert[0]["id"]
                chunk_ids.append(chunk_id)
                texts.append(chunk)
    finally:
        with _ingest_lock:
            _ingest_in_progress = False

    if not texts:
        raise HTTPException(status_code=400, detail="PDFs found but no extractable text")

    index = build_index(texts)
    save_index(index)

    vector_payload = [
        {"position": pos, "chunk_id": chunk_id}
        for pos, chunk_id in enumerate(chunk_ids)
    ]
    if vector_payload:
        logger.info("Inserting %d vector map entries", len(vector_payload))
        supabase.table("vector_map").insert(vector_payload).execute()

    return {
        "pdf_count": len(pdfs),
        "chunk_count": len(texts),
        "index_path": str(INDEX_PATH),
        "db_path": None,
    }


def ingest_files(pdf_paths: List[Path]) -> Dict[str, Any]:
    if not pdf_paths:
        raise HTTPException(status_code=400, detail="No PDF files provided")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    global _ingest_in_progress
    with _ingest_lock:
        if _ingest_in_progress:
            raise HTTPException(status_code=409, detail="Ingest already in progress")
        _ingest_in_progress = True

    logger.info("Ingesting %d uploaded PDF(s)", len(pdf_paths))
    texts: List[str] = []
    chunk_ids: List[int] = []

    try:
        supabase = get_supabase()
        for pdf_path in pdf_paths:
            pdf_bytes = pdf_path.read_bytes()
            markdown_text = pdf_to_markdown_gpt(pdf_bytes, pdf_path.name)
            semantic = generate_semantic_markdown(markdown_text)
            compliance_markdown = generate_compliance_markdown(markdown_text)

            logger.info("Inserting document: %s", pdf_path.name)
            doc_payload = {
                "filename": pdf_path.name,
                "rel_path": str(pdf_path.relative_to(PDF_ROOT)),
                "pdf_blob": _bytes_to_bytea_literal(pdf_bytes),
                "markdown_text": markdown_text,
                "semantic_markdown": semantic["semantic_markdown"],
                "summary_markdown": semantic["summary_markdown"],
            }
            doc_insert = (
                supabase.table("documents").insert(doc_payload).execute().data or []
            )
            if not doc_insert:
                raise HTTPException(status_code=500, detail="Failed to insert document")
            document_id = doc_insert[0]["id"]

            supabase.table("compliance_items").insert(
                {
                    "document_id": document_id,
                    "regulation_name": "",
                    "compliance_markdown": compliance_markdown,
                }
            ).execute()

            for chunk_idx, chunk in enumerate(
                chunk_text(markdown_text, CHUNK_SIZE, CHUNK_OVERLAP), start=1
            ):
                chunk_payload = {
                    "document_id": document_id,
                    "page": 0,
                    "chunk_index": chunk_idx,
                    "text": chunk,
                }
                chunk_insert = (
                    supabase.table("chunks").insert(chunk_payload).execute().data or []
                )
                if not chunk_insert:
                    raise HTTPException(status_code=500, detail="Failed to insert chunk")
                chunk_id = chunk_insert[0]["id"]
                chunk_ids.append(chunk_id)
                texts.append(chunk)
    finally:
        with _ingest_lock:
            _ingest_in_progress = False

    if not texts:
        raise HTTPException(status_code=400, detail="PDFs found but no extractable text")

    if INDEX_PATH.exists():
        logger.info("Loading existing FAISS index")
        index = load_index()
        new_vectors = embed_texts(texts)
        index.add(new_vectors)
    else:
        logger.info("Building new FAISS index")
        index = build_index(texts)
    save_index(index)

    start_pos = int(index.ntotal) - len(chunk_ids)
    vector_payload = [
        {"position": start_pos + i, "chunk_id": chunk_id}
        for i, chunk_id in enumerate(chunk_ids)
    ]
    if vector_payload:
        supabase.table("vector_map").insert(vector_payload).execute()

    return {
        "pdf_count": len(pdf_paths),
        "chunk_count": len(texts),
        "index_path": str(INDEX_PATH),
        "db_path": None,
    }


@app.post(
    "/ingest",
    summary="PDF 임베딩 인덱싱",
    description=(
        "업로드/폴더 내 PDF를 읽어 텍스트 청크를 만들고 임베딩 생성 후 "
        "FAISS 인덱스를 구축합니다. 원본 PDF, 마크다운 추출 결과, "
        "시맨틱/요약 마크다운, 청크 메타데이터는 Supabase에 저장됩니다."
    ),
)
def ingest() -> Dict[str, Any]:
    return ingest_all()


@app.post(
    "/upload",
    summary="PDF 업로드 및 즉시 인덱싱",
    description=(
        "PDF 파일을 업로드하면 즉시 인덱싱을 수행합니다. 원본 PDF, 마크다운 추출 결과, "
        "시맨틱/요약 마크다운, 청크 메타데이터를 Supabase에 저장하고 FAISS 인덱스를 생성합니다."
    ),
)
def upload(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Upload started: %d file(s) received", len(files))
    saved = []
    skipped = []
    for file in files:
        filename = file.filename or ""
        if not filename.lower().endswith(".pdf"):
            logger.warning("Skipping non-PDF: %s", filename)
            skipped.append(filename)
            continue
        target = UPLOAD_DIR / Path(filename).name
        logger.info("Reading file: %s", filename)
        content = file.file.read()
        logger.info("Saving file: %s (%d bytes)", target.name, len(content))
        target.write_bytes(content)
        saved.append(str(target.relative_to(PDF_ROOT)))

    logger.info("Upload saved %d file(s), skipped %d file(s)", len(saved), len(skipped))
    if not saved:
        raise HTTPException(status_code=400, detail="No PDF files uploaded")

    saved_paths = [PDF_ROOT / p for p in saved]
    logger.info("Starting ingest for uploaded files")
    result = ingest_files(saved_paths)
    logger.info(
        "Upload ingest done: pdf_count=%s chunk_count=%s",
        result.get("pdf_count"),
        result.get("chunk_count"),
    )
    result["uploaded"] = saved
    result["uploaded_count"] = len(saved)
    result["skipped"] = skipped
    result["skipped_count"] = len(skipped)
    return result


@app.post(
    "/query",
    summary="유사 청크 검색",
    description=(
        "질의 문장을 임베딩하여 FAISS에서 유사한 청크를 검색하고 "
        "Supabase에 저장된 청크/문서 정보를 함께 반환합니다."
    ),
)
def query(q: str, top_k: int = 5) -> Dict[str, Any]:
    try:
        index = load_index()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Index not found. Run /ingest first.")

    q_emb = embed_texts([q])

    top_k = max(1, min(top_k, 20))
    scores, indices = index.search(q_emb, top_k)

    results = []
    supabase = get_supabase()
    positions = [int(i) for i in indices[0] if i != -1]
    if positions:
        vm_rows = (
            supabase.table("vector_map")
            .select("position, chunk_id")
            .in_("position", positions)
            .execute()
            .data
            or []
        )
        pos_to_chunk = {row["position"]: row["chunk_id"] for row in vm_rows}
        chunk_ids = [pos_to_chunk.get(pos) for pos in positions if pos in pos_to_chunk]
        chunk_rows = (
            supabase.table("chunks")
            .select("id, text, page, document_id")
            .in_("id", chunk_ids)
            .execute()
            .data
            or []
        )
        chunk_by_id = {row["id"]: row for row in chunk_rows}
        doc_ids = list({row["document_id"] for row in chunk_rows})
        doc_rows = (
            supabase.table("documents")
            .select("id, rel_path, filename, markdown_text")
            .in_("id", doc_ids)
            .execute()
            .data
            or []
        )
        doc_by_id = {row["id"]: row for row in doc_rows}
        comp_rows = (
            supabase.table("compliance_items")
            .select("document_id, regulation_name, compliance_markdown, created_at")
            .in_("document_id", doc_ids)
            .order("id", desc=True)
            .execute()
            .data
            or []
        )
        comp_by_doc: Dict[int, Dict[str, Any]] = {}
        for row in comp_rows:
            doc_id = row["document_id"]
            if doc_id not in comp_by_doc:
                comp_by_doc[doc_id] = row

        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            chunk_id = pos_to_chunk.get(int(idx))
            if not chunk_id:
                continue
            chunk = chunk_by_id.get(chunk_id)
            if not chunk:
                continue
            doc = doc_by_id.get(chunk["document_id"])
            if not doc:
                continue
            compliance = comp_by_doc.get(doc["id"]) or {}
            results.append(
                {
                    "score": float(score),
                    "text": chunk["text"],
                    "source": doc["rel_path"],
                    "page": chunk["page"],
                    "document_id": doc["id"],
                    "document_filename": doc["filename"],
                    "document_markdown": doc["markdown_text"],
                    "compliance_markdown": compliance.get("compliance_markdown"),
                    "regulation_name": compliance.get("regulation_name"),
                    "document_pdf_url": f"/documents/{doc['id']}/pdf",
                }
            )

    return {"query": q, "results": results}


@app.get(
    "/documents",
    summary="문서 목록 조회",
    description="Supabase에 저장된 문서 목록과 청크 개수를 반환합니다.",
)
def documents() -> Dict[str, Any]:
    return {"documents": get_document_list()}


@app.get(
    "/documents/{doc_id}",
    summary="문서 상세 조회",
    description="문서 메타데이터, 마크다운 추출 텍스트, 시맨틱/요약 마크다운, 청크 목록을 반환합니다.",
)
def document_detail(doc_id: int) -> Dict[str, Any]:
    return get_document_detail(doc_id)


@app.get(
    "/documents/{doc_id}/pdf",
    summary="원본 PDF 다운로드",
    description="Supabase에 저장된 원본 PDF 파일을 반환합니다.",
)
def document_pdf(doc_id: int) -> Response:
    supabase = get_supabase()
    rows = (
        supabase.table("documents")
        .select("filename, pdf_blob")
        .eq("id", doc_id)
        .execute()
        .data
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Document not found")
    row = rows[0]
    pdf_bytes = _decode_bytea(row.get("pdf_blob"))
    filename = row.get("filename") or f"document-{doc_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@app.get("/ui", include_in_schema=False)
def ui() -> HTMLResponse:
    html = """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <title>RAG DB Viewer</title>
    <style>
      :root { --bg: #0f1115; --panel: #171a21; --text: #e6e6e6; --muted: #9aa4b2; --accent: #7dd3fc; }
      * { box-sizing: border-box; }
      body { margin: 0; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
             background: radial-gradient(1200px 600px at 20% -10%, #1f2937, transparent), var(--bg);
             color: var(--text); }
      .wrap { max-width: 1200px; margin: 0 auto; padding: 24px; }
      h1 { font-size: 20px; font-weight: 700; margin: 0 0 16px; }
      .grid { display: grid; grid-template-columns: 320px 1fr; gap: 16px; }
      .panel { background: var(--panel); border: 1px solid #2a2f3a; border-radius: 12px; padding: 16px; }
      .list { display: flex; flex-direction: column; gap: 8px; max-height: 70vh; overflow: auto; }
      .item { padding: 10px; border: 1px solid #2a2f3a; border-radius: 10px; cursor: pointer; }
      .item:hover { border-color: var(--accent); }
      .muted { color: var(--muted); font-size: 12px; }
      .badge { background: #0b2730; color: var(--accent); padding: 2px 6px; border-radius: 999px; font-size: 11px; }
      pre { white-space: pre-wrap; word-break: break-word; background: #0b0d12; padding: 12px; border-radius: 8px; border: 1px solid #1f2430; }
      .chunks { max-height: 40vh; overflow: auto; }
      .search { width: 100%; padding: 8px 10px; border-radius: 8px; border: 1px solid #2a2f3a; background: #0b0d12; color: var(--text); }
      @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
    </style>
  </head>
  <body>
    <div class="wrap">
      <h1>RAG DB Viewer</h1>
      <div class="grid">
        <div class="panel">
          <input id="search" class="search" placeholder="Filter by filename..." />
          <div id="doc-list" class="list" style="margin-top:12px;"></div>
        </div>
        <div class="panel">
          <div id="detail">
            <div class="muted">Select a document to view details.</div>
          </div>
        </div>
      </div>
    </div>
    <script>
      const listEl = document.getElementById("doc-list");
      const detailEl = document.getElementById("detail");
      const searchEl = document.getElementById("search");
      let docs = [];

      function renderList(items) {
        listEl.innerHTML = "";
        items.forEach((d) => {
          const div = document.createElement("div");
          div.className = "item";
          div.innerHTML = `
            <div><strong>${d.filename}</strong></div>
            <div class="muted">${d.rel_path}</div>
            <div class="muted">${d.created_at} · <span class="badge">${d.chunk_count} chunks</span></div>
          `;
          div.onclick = () => loadDetail(d.id);
          listEl.appendChild(div);
        });
      }

      async function loadList() {
        const res = await fetch("/documents");
        const data = await res.json();
        docs = data.documents || [];
        renderList(docs);
      }

      async function loadDetail(id) {
        const res = await fetch(`/documents/${id}`);
        const data = await res.json();
        const doc = data.document;
        const chunks = data.chunks || [];
        detailEl.innerHTML = `
          <div><strong>${doc.filename}</strong></div>
          <div class="muted">${doc.rel_path} · ${doc.created_at}</div>
          <h3 style="margin-top:16px;">Markdown (원본)</h3>
          <pre>${doc.markdown_text || ""}</pre>
          <h3>Semantic Markdown</h3>
          <pre>${doc.semantic_markdown || ""}</pre>
          <h3>Summary Markdown</h3>
          <pre>${doc.summary_markdown || ""}</pre>
          <h3>Compliance Markdown</h3>
          <pre>${(data.compliance && data.compliance[0] && data.compliance[0].compliance_markdown) || ""}</pre>
          <h3>Chunks (${chunks.length})</h3>
          <div class="chunks">
            ${chunks.map(c => `<pre>[p${c.page} #${c.chunk_index}] ${c.text}</pre>`).join("")}
          </div>
        `;
      }

      searchEl.addEventListener("input", (e) => {
        const q = e.target.value.toLowerCase();
        const filtered = docs.filter(d => d.filename.toLowerCase().includes(q));
        renderList(filtered);
      });

      loadList();
    </script>
  </body>
</html>
"""
    return HTMLResponse(content=html)
