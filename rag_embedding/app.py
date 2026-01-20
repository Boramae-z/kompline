import base64
import json
import os
import sqlite3
from pathlib import Path
from typing import List, Dict, Any

import faiss
import numpy as np
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, Response

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PDF_ROOT = BASE_DIR
UPLOAD_DIR = BASE_DIR / "uploads"
INDEX_PATH = BASE_DIR / "index.faiss"
DB_PATH = BASE_DIR / "rag.sqlite"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
GPT_MODEL = os.getenv("GPT_MODEL", "gpt-4o")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
EMBEDDING_BATCH = int(os.getenv("EMBEDDING_BATCH", "64"))

app = FastAPI(title="RAG Embedding API")


def _require_openai_key() -> None:
    """Raise HTTPException if OpenAI API key is not configured."""
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set")


def embed_texts(texts: List[str]) -> np.ndarray:
    _require_openai_key()
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
    _require_openai_key()
    if not pdf_bytes:
        return ""

    file_b64 = base64.b64encode(pdf_bytes).decode("ascii")
    response = requests.post(
        f"{OPENAI_BASE_URL}/responses",
        headers={
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": GPT_MODEL,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "Convert the PDF to clean, structured markdown. "
                                "Preserve headings, lists, and tables when possible. "
                                "If page boundaries are clear, add headings like '## Page N'. "
                                "Return markdown only."
                            ),
                        },
                        {
                            "type": "input_file",
                            "filename": filename,
                            "file_data": file_b64,
                        },
                    ],
                }
            ],
        },
        timeout=120,
    )
    if response.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI responses error: {response.status_code} {response.text}",
        )
    return _extract_response_text(response.json())


def generate_semantic_markdown(markdown_text: str) -> Dict[str, str]:
    _require_openai_key()
    if not markdown_text.strip():
        return {"semantic_markdown": "", "summary_markdown": ""}

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
    _require_openai_key()
    if not markdown_text.strip():
        return ""

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


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                rel_path TEXT NOT NULL,
                pdf_blob BLOB NOT NULL,
                markdown_text TEXT NOT NULL,
                semantic_markdown TEXT NOT NULL DEFAULT '',
                summary_markdown TEXT NOT NULL DEFAULT '',
                compliance_markdown TEXT NOT NULL DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                page INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                text TEXT NOT NULL,
                FOREIGN KEY(document_id) REFERENCES documents(id)
            );
            CREATE TABLE IF NOT EXISTS vector_map (
                position INTEGER PRIMARY KEY,
                chunk_id INTEGER NOT NULL,
                FOREIGN KEY(chunk_id) REFERENCES chunks(id)
            );
            """
        )
        conn.commit()
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(documents)").fetchall()
        }
        if "semantic_markdown" not in columns:
            conn.execute(
                "ALTER TABLE documents ADD COLUMN semantic_markdown TEXT NOT NULL DEFAULT ''"
            )
        if "summary_markdown" not in columns:
            conn.execute(
                "ALTER TABLE documents ADD COLUMN summary_markdown TEXT NOT NULL DEFAULT ''"
            )
        if "compliance_markdown" not in columns:
            conn.execute(
                "ALTER TABLE documents ADD COLUMN compliance_markdown TEXT NOT NULL DEFAULT ''"
            )
        conn.commit()
    finally:
        conn.close()


def reset_db() -> None:
    conn = get_conn()
    try:
        conn.executescript(
            """
            DELETE FROM vector_map;
            DELETE FROM chunks;
            DELETE FROM documents;
            """
        )
        conn.commit()
    finally:
        conn.close()


def get_document_list() -> List[Dict[str, Any]]:
    init_db()
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT d.id, d.filename, d.rel_path, d.created_at,
               COUNT(c.id) AS chunk_count
        FROM documents d
        LEFT JOIN chunks c ON c.document_id = d.id
        GROUP BY d.id
        ORDER BY d.id DESC
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_document_detail(doc_id: int) -> Dict[str, Any]:
    init_db()
    conn = get_conn()
    doc = conn.execute(
        """
        SELECT id, filename, rel_path, markdown_text, semantic_markdown,
               summary_markdown, compliance_markdown, created_at
        FROM documents
        WHERE id = ?
        """,
        (doc_id,),
    ).fetchone()
    if not doc:
        conn.close()
        raise HTTPException(status_code=404, detail="Document not found")

    chunks = conn.execute(
        """
        SELECT id, page, chunk_index, text
        FROM chunks
        WHERE document_id = ?
        ORDER BY page, chunk_index
        """,
        (doc_id,),
    ).fetchall()
    conn.close()
    return {
        "document": dict(doc),
        "chunks": [dict(row) for row in chunks],
    }


def ingest_all() -> Dict[str, Any]:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    init_db()
    pdfs = find_pdfs(PDF_ROOT)
    if not pdfs:
        raise HTTPException(status_code=404, detail="No PDF files found under rag_embedding")

    texts: List[str] = []
    chunk_ids: List[int] = []

    reset_db()
    conn = get_conn()
    for pdf_path in pdfs:
        pdf_bytes = pdf_path.read_bytes()
        markdown_text = pdf_to_markdown_gpt(pdf_bytes, pdf_path.name)
        semantic = generate_semantic_markdown(markdown_text)
        compliance_markdown = generate_compliance_markdown(markdown_text)

        cur = conn.execute(
            """
            INSERT INTO documents (
                filename, rel_path, pdf_blob, markdown_text, semantic_markdown,
                summary_markdown, compliance_markdown
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pdf_path.name,
                str(pdf_path.relative_to(PDF_ROOT)),
                sqlite3.Binary(pdf_bytes),
                markdown_text,
                semantic["semantic_markdown"],
                semantic["summary_markdown"],
                compliance_markdown,
            ),
        )
        document_id = cur.lastrowid

        for chunk_idx, chunk in enumerate(
            chunk_text(markdown_text, CHUNK_SIZE, CHUNK_OVERLAP), start=1
        ):
            cur = conn.execute(
                """
                INSERT INTO chunks (document_id, page, chunk_index, text)
                VALUES (?, ?, ?, ?)
                """,
                (document_id, 0, chunk_idx, chunk),
            )
            chunk_ids.append(cur.lastrowid)
            texts.append(chunk)

    if not texts:
        conn.close()
        raise HTTPException(status_code=400, detail="PDFs found but no extractable text")

    index = build_index(texts)
    save_index(index)

    for pos, chunk_id in enumerate(chunk_ids):
        conn.execute(
            "INSERT INTO vector_map (position, chunk_id) VALUES (?, ?)",
            (pos, chunk_id),
        )
    conn.commit()
    conn.close()

    return {
        "pdf_count": len(pdfs),
        "chunk_count": len(texts),
        "index_path": str(INDEX_PATH),
        "db_path": str(DB_PATH),
    }


@app.post(
    "/ingest",
    summary="PDF 임베딩 인덱싱",
    description=(
        "업로드/폴더 내 PDF를 읽어 텍스트 청크를 만들고 임베딩 생성 후 "
        "FAISS 인덱스를 구축합니다. 원본 PDF, 마크다운 추출 결과, "
        "시맨틱/요약 마크다운, 청크 메타데이터는 SQLite에 저장됩니다."
    ),
)
def ingest() -> Dict[str, Any]:
    return ingest_all()


@app.post(
    "/upload",
    summary="PDF 업로드 및 즉시 인덱싱",
    description=(
        "PDF 파일을 업로드하면 즉시 인덱싱을 수행합니다. 원본 PDF, 마크다운 추출 결과, "
        "시맨틱/요약 마크다운, 청크 메타데이터를 SQLite에 저장하고 FAISS 인덱스를 생성합니다."
    ),
)
def upload(files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    saved = []
    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            continue
        target = UPLOAD_DIR / Path(file.filename).name
        content = file.file.read()
        target.write_bytes(content)
        saved.append(str(target.relative_to(PDF_ROOT)))

    if not saved:
        raise HTTPException(status_code=400, detail="No PDF files uploaded")

    result = ingest_all()
    result["uploaded"] = saved
    result["uploaded_count"] = len(saved)
    return result


@app.post(
    "/query",
    summary="유사 청크 검색",
    description=(
        "질의 문장을 임베딩하여 FAISS에서 유사한 청크를 검색하고 "
        "SQLite에 저장된 청크/문서 정보를 함께 반환합니다."
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

    init_db()
    conn = get_conn()
    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        row = conn.execute(
            """
            SELECT c.text, c.page, d.rel_path, d.id AS document_id,
                   d.filename, d.markdown_text, d.compliance_markdown
            FROM vector_map vm
            JOIN chunks c ON c.id = vm.chunk_id
            JOIN documents d ON d.id = c.document_id
            WHERE vm.position = ?
            """,
            (int(idx),),
        ).fetchone()
        if row:
            results.append(
                {
                    "score": float(score),
                    "text": row["text"],
                    "source": row["rel_path"],
                    "page": row["page"],
                    "document_id": row["document_id"],
                    "document_filename": row["filename"],
                    "document_markdown": row["markdown_text"],
                    "compliance_markdown": row["compliance_markdown"],
                    "document_pdf_url": f"/documents/{row['document_id']}/pdf",
                }
            )
    conn.close()

    return {"query": q, "results": results}


@app.get(
    "/documents",
    summary="문서 목록 조회",
    description="SQLite에 저장된 문서 목록과 청크 개수를 반환합니다.",
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
    description="SQLite에 저장된 원본 PDF 파일을 반환합니다.",
)
def document_pdf(doc_id: int) -> Response:
    init_db()
    conn = get_conn()
    row = conn.execute(
        "SELECT filename, pdf_blob FROM documents WHERE id = ?",
        (doc_id,),
    ).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    return Response(
        content=row["pdf_blob"],
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{row["filename"]}"'},
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
          <pre>${doc.compliance_markdown || ""}</pre>
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
