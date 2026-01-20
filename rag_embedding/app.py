import os
import sqlite3
from pathlib import Path
from typing import List, Dict, Any

import faiss
import numpy as np
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from pypdf import PdfReader

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
PDF_ROOT = BASE_DIR
UPLOAD_DIR = BASE_DIR / "uploads"
INDEX_PATH = BASE_DIR / "index.faiss"
DB_PATH = BASE_DIR / "rag.sqlite"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
EMBEDDING_BATCH = int(os.getenv("EMBEDDING_BATCH", "64"))

app = FastAPI(title="RAG Embedding API")


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


def find_pdfs(root: Path) -> List[Path]:
    return sorted([p for p in root.rglob("*.pdf") if p.is_file()])


def extract_pages(pdf_path: Path) -> List[str]:
    reader = PdfReader(str(pdf_path))
    pages: List[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    return pages


def pages_to_markdown(pages: List[str]) -> str:
    md_parts = []
    for idx, text in enumerate(pages, start=1):
        cleaned = " ".join((text or "").split())
        md_parts.append(f"## Page {idx}\n\n{cleaned}")
    return "\n\n".join(md_parts).strip()


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
        pages = extract_pages(pdf_path)
        markdown_text = pages_to_markdown(pages)
        pdf_bytes = pdf_path.read_bytes()

        cur = conn.execute(
            """
            INSERT INTO documents (filename, rel_path, pdf_blob, markdown_text)
            VALUES (?, ?, ?, ?)
            """,
            (
                pdf_path.name,
                str(pdf_path.relative_to(PDF_ROOT)),
                sqlite3.Binary(pdf_bytes),
                markdown_text,
            ),
        )
        document_id = cur.lastrowid

        for page_idx, page_text in enumerate(pages, start=1):
            for chunk_idx, chunk in enumerate(
                chunk_text(page_text, CHUNK_SIZE, CHUNK_OVERLAP), start=1
            ):
                cur = conn.execute(
                    """
                    INSERT INTO chunks (document_id, page, chunk_index, text)
                    VALUES (?, ?, ?, ?)
                    """,
                    (document_id, page_idx, chunk_idx, chunk),
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
        "FAISS 인덱스를 구축합니다. 원본 PDF, 마크다운 추출 결과, 청크 메타데이터는 "
        "SQLite에 저장됩니다."
    ),
)
def ingest() -> Dict[str, Any]:
    return ingest_all()


@app.post(
    "/upload",
    summary="PDF 업로드 및 즉시 인덱싱",
    description=(
        "PDF 파일을 업로드하면 즉시 인덱싱을 수행합니다. 원본 PDF, 마크다운 추출 결과, "
        "청크 메타데이터를 SQLite에 저장하고 FAISS 인덱스를 생성합니다."
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
            SELECT c.text, c.page, d.rel_path
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
                }
            )
    conn.close()

    return {"query": q, "results": results}
