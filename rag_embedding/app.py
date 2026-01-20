import json
import os
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
META_PATH = BASE_DIR / "index.json"

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


def save_metadata(metadata: List[Dict[str, Any]]) -> None:
    with META_PATH.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def load_metadata() -> List[Dict[str, Any]]:
    if not META_PATH.exists():
        raise FileNotFoundError("metadata not found")
    with META_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_index(index: faiss.IndexFlatIP) -> None:
    faiss.write_index(index, str(INDEX_PATH))


def load_index() -> faiss.IndexFlatIP:
    if not INDEX_PATH.exists():
        raise FileNotFoundError("index not found")
    return faiss.read_index(str(INDEX_PATH))


@app.post("/ingest")
def ingest() -> Dict[str, Any]:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    pdfs = find_pdfs(PDF_ROOT)
    if not pdfs:
        raise HTTPException(status_code=404, detail="No PDF files found under rag_embedding")

    documents: List[Dict[str, Any]] = []
    texts: List[str] = []

    for pdf_path in pdfs:
        pages = extract_pages(pdf_path)
        for page_idx, page_text in enumerate(pages, start=1):
            for chunk in chunk_text(page_text, CHUNK_SIZE, CHUNK_OVERLAP):
                documents.append(
                    {
                        "text": chunk,
                        "source": str(pdf_path.relative_to(PDF_ROOT)),
                        "page": page_idx,
                    }
                )
                texts.append(chunk)

    if not texts:
        raise HTTPException(status_code=400, detail="PDFs found but no extractable text")

    index = build_index(texts)
    save_index(index)
    save_metadata(documents)

    return {
        "pdf_count": len(pdfs),
        "chunk_count": len(texts),
        "index_path": str(INDEX_PATH),
        "metadata_path": str(META_PATH),
    }


@app.post("/upload")
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

    return {"saved": saved, "count": len(saved)}


@app.post("/query")
def query(q: str, top_k: int = 5) -> Dict[str, Any]:
    try:
        index = load_index()
        metadata = load_metadata()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Index not found. Run /ingest first.")

    q_emb = embed_texts([q])

    top_k = max(1, min(top_k, 20))
    scores, indices = index.search(q_emb, top_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        item = metadata[idx]
        results.append(
            {
                "score": float(score),
                "text": item["text"],
                "source": item["source"],
                "page": item["page"],
            }
        )

    return {"query": q, "results": results}
