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
    appmod.SUPABASE_URL = "https://example.supabase.co"
    appmod.SUPABASE_SERVICE_ROLE_KEY = "test-key"
    appmod.SUPABASE_KEY = "test-key"

    class Result:
        def __init__(self, data):
            self.data = data

    class FakeTable:
        def __init__(self, store, name, ids):
            self.store = store
            self.name = name
            self.ids = ids
            self._action = "select"
            self._payload = None
            self._filters = []
            self._order = None

        def select(self, _fields="*"):
            self._action = "select"
            return self

        def insert(self, payload):
            self._action = "insert"
            self._payload = payload
            return self

        def delete(self):
            self._action = "delete"
            return self

        def eq(self, key, value):
            self._filters.append(("eq", key, value))
            return self

        def in_(self, key, values):
            self._filters.append(("in", key, set(values)))
            return self

        def order(self, key, desc=False):
            self._order = (key, desc)
            return self

        def _apply_filters(self, rows):
            for ftype, key, val in self._filters:
                if ftype == "eq":
                    rows = [r for r in rows if r.get(key) == val]
                elif ftype == "in":
                    rows = [r for r in rows if r.get(key) in val]
            return rows

        def execute(self):
            rows = self.store.setdefault(self.name, [])
            if self._action == "insert":
                payloads = self._payload if isinstance(self._payload, list) else [self._payload]
                inserted = []
                for item in payloads:
                    row = dict(item)
                    if "id" not in row:
                        self.ids[self.name] = self.ids.get(self.name, 0) + 1
                        row["id"] = self.ids[self.name]
                    rows.append(row)
                    inserted.append(row)
                return Result(inserted)
            if self._action == "delete":
                kept = self._apply_filters(rows)
                removed = [r for r in rows if r not in kept]
                if self._filters:
                    self.store[self.name] = kept
                else:
                    self.store[self.name] = []
                return Result(removed)
            # select
            result = self._apply_filters(rows)
            if self._order:
                key, desc = self._order
                result = sorted(result, key=lambda r: r.get(key), reverse=desc)
            return Result(result)

    class FakeSupabase:
        def __init__(self):
            self.store = {}
            self.ids = {}

        def table(self, name):
            return FakeTable(self.store, name, self.ids)

    fake_supabase = FakeSupabase()
    monkeypatch.setattr(appmod, "get_supabase", lambda: fake_supabase)

    def fake_post(url, headers=None, json=None, timeout=60):
        if url.endswith("/embeddings"):
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

        if url.endswith("/responses"):
            is_json_schema = bool(json.get("text", {}).get("format", {}).get("type") == "json_schema")
            schema_name = json.get("text", {}).get("format", {}).get("name")

            class Resp:
                status_code = 200
                text = "ok"

                def json(self):
                    if is_json_schema and schema_name == "semantic_extract":
                        return {
                            "output_text": (
                                "{\"semantic_markdown\":\"# Semantic\\n- Entity: Test\","
                                "\"summary_markdown\":\"# Summary\\nTest\"}"
                            )
                        }
                    if is_json_schema and schema_name == "compliance_extract":
                        return {
                            "output_text": "{\"compliance_markdown\":\"# Compliance\\n- Control: X\"}"
                        }
                    return {"output_text": "# Title\n\nHello PDF"}

            return Resp()

        raise AssertionError(f"Unexpected URL: {url}")

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

    docs = fake_supabase.store.get("documents", [])
    compliance = fake_supabase.store.get("compliance_items", [])
    assert docs and compliance
    assert docs[0]["filename"] == "test.pdf"
    assert "Hello PDF" in docs[0]["markdown_text"]
    assert "Semantic" in docs[0]["semantic_markdown"]
    assert "Summary" in docs[0]["summary_markdown"]
    assert "Compliance" in compliance[0]["compliance_markdown"]
