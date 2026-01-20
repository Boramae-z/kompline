# RAG Embedding API

PDF 업로드 → GPT 기반 마크다운 변환 → 청크 분할 → OpenAI 임베딩 → FAISS 인덱싱 → SQLite 저장까지 수행하는 간단한 RAG 백엔드입니다.

## 환경 설정

### 1) 의존성 설치
```powershell
pip install -r requirements.txt
```

### 2) .env 설정
`rag_embedding/.env` 파일을 만들고 아래 값을 설정하세요.
```env
OPENAI_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_BASE_URL=https://api.openai.com/v1
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
EMBEDDING_BATCH=64
GPT_MODEL=gpt-4o-mini
```

필수: `OPENAI_API_KEY`

## 서버 실행

```powershell
python -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Swagger 문서:
- http://127.0.0.1:8000/docs

UI:
- http://127.0.0.1:8000/ui

## API 목록

### POST /upload
PDF 업로드와 동시에 인덱싱을 수행합니다.

- 입력: multipart form (`files`)
- 출력: 업로드된 파일 목록, 인덱싱 결과(청크 수 등)

예시:
```powershell
curl -X POST "http://127.0.0.1:8000/upload" `
  -F "files=@C:\path\to\file.pdf"
```

### POST /ingest
폴더 내 모든 PDF를 읽어 전체 재인덱싱합니다.

- 사용 시점: 업로드 외부로 PDF를 넣었거나, 전체 재빌드 필요할 때

예시:
```powershell
curl -X POST "http://127.0.0.1:8000/ingest"
```

### POST /query
질의 문장을 임베딩하여 유사 청크를 검색합니다.

- 입력: `q`(질의문), `top_k`(최대 20)
- 출력: 유사 청크 목록(점수, 텍스트, 소스 파일, 페이지, 문서 마크다운, 컴플라이언스 마크다운, 원본 PDF URL)

예시:
```powershell
curl -X POST "http://127.0.0.1:8000/query?q=hello&top_k=5"
```

### GET /documents
SQLite에 저장된 문서 목록과 청크 개수를 조회합니다.

### GET /documents/{doc_id}
문서 메타데이터, 마크다운 추출 텍스트, 시맨틱/요약/컴플라이언스 마크다운, 청크 목록을 반환합니다.

### GET /documents/{doc_id}/pdf
SQLite에 저장된 원본 PDF 파일을 반환합니다.

## 저장 구조

### FAISS 인덱스
- `rag_embedding/index.faiss`

### SQLite DB
- `rag_embedding/rag.sqlite`

#### tables
- `documents`: PDF 원본(blob), 파일명, 경로, 마크다운, 시맨틱/요약/컴플라이언스 마크다운
- `chunks`: 문서별 청크 텍스트, 페이지, 청크 인덱스
- `vector_map`: FAISS 인덱스 위치 → 청크 ID 매핑

## 테스트

```powershell
python -m pytest -q
```
