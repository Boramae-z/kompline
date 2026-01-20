import sqlite3

from fastapi.testclient import TestClient

import app as appmod


def _make_pdf_bytes(text: str) -> bytes:
    def obj(n: int, body: bytes) -> bytes:
        return f"{n} 0 obj\n".encode("ascii") + body + b"\nendobj\n"

    stream = f"BT /F1 24 Tf 72 100 Td ({text}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    header = b"%PDF-1.4\n"
    body = b""
    offsets = [0]
    for i, content in enumerate(objects, start=1):
        offsets.append(len(header) + len(body))
        body += obj(i, content)

    xref_start = len(header) + len(body)
    xref = b"xref\n0 6\n0000000000 65535 f \n"
    for off in offsets[1:]:
        xref += f"{off:010d} 00000 n \n".encode("ascii")
    trailer = (
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n"
        + str(xref_start).encode("ascii")
        + b"\n%%EOF\n"
    )
    return header + body + xref + trailer


def test_upload_ingest_query(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    appmod.OPENAI_API_KEY = "test-key"
    appmod.BASE_DIR = tmp_path
    appmod.PDF_ROOT = tmp_path
    appmod.UPLOAD_DIR = tmp_path / "uploads"
    appmod.INDEX_PATH = tmp_path / "index.faiss"
    appmod.DB_PATH = tmp_path / "rag.sqlite"

    def fake_post(url, headers=None, json=None, timeout=60):
        inputs = json.get("input", [])
        data = [
            {"index": i, "embedding": [float(i + 1), 0.0, 0.0]}
            for i in range(len(inputs))
        ]

        class Resp:
            status_code = 200
            text = "ok"

            def json(self):
                return {"data": data}

        return Resp()

    monkeypatch.setattr(appmod.requests, "post", fake_post)

    client = TestClient(appmod.app)
    pdf_bytes = _make_pdf_bytes("Hello PDF")
    response = client.post(
        "/upload",
        files=[("files", ("test.pdf", pdf_bytes, "application/pdf"))],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["chunk_count"] >= 1

    response = client.post("/query", params={"q": "Hello", "top_k": 3})
    assert response.status_code == 200
    data = response.json()
    assert data["results"]
    assert "Hello" in data["results"][0]["text"]

    conn = sqlite3.connect(appmod.DB_PATH)
    row = conn.execute("SELECT filename, markdown_text FROM documents").fetchone()
    conn.close()
    assert row[0] == "test.pdf"
    assert "Page 1" in row[1]
