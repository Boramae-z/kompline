# Kompline

> 금융권, 레그테크 기업 등 대내외 규정·법령·표준인증 점검 룰을 기반으로 서비스 준수 상태를 지속 증명하는 멀티에이전트 컴플라이언스 시스템

## 개요

Kompline은 금융권, 레그테크 기업 등 대내외 규정·법령·표준 인증 준수 상태를 지속적으로 증명·관리해야 하는 조직을 위한 멀티 에이전트 컴플라이언스 시스템입니다. 코드·로그·데이터 등 기업 산출물을 지속적으로 스캔해 감사자에게는 자동 점검 및 리포팅을, 피감사자에게는 증빙자료 생성을, 실무자에게는 업무 착수 전 규정 적합성 사전 검토를 제공합니다. 이를 통해 감사 비용을 절감하고 리스크를 조기에 대응하는 워크플로우를 구축합니다.

## 핵심 가치

- **Continuous Compliance**: 주기적 감사가 아닌 상시 준수 검증으로 리스크 조기 탐지
- **증빙 자동화**: 결과에 근거한 Evidence 생성 및 추적
- **멀티 에이전트 확장성**: Orchestrator/Validator/Reporter 병렬 실행
- **실무 친화**: 감사자/피감사자/실무자 모두의 업무 부담 감소

## 구성 요소

- **Compliance Extractor** (`compliance_extractor/`): 규정 PDF 업로드 → 규정 항목(compliance_items) 추출 및 Supabase 저장
- **Agents** (`agents/`): Orchestrator/Validator/Reporter가 스캔 파이프라인 수행
- **Frontend** (`frontend/`): 규정/스캔 결과 확인 UI
- **Supabase Schema** (`supabase/schema.sql`, `agents/sql/scan_schema.sql`): 규정/스캔 테이블 정의

## 아키텍처

```
┌──────────────────────────────────────────────────────────────────┐
│                         Kompline Platform                         │
├──────────────────────────────────────────────────────────────────┤
│  Frontend (Next.js) ─────┐                                        │
│                          │   Supabase (Postgres)                   │
│  Compliance Extractor ───┼──▶ documents, compliance_items          │
│  (FastAPI)               │   scans, scan_documents, scan_results   │
│                          │   repositories                          │
│  Agents (Python)   ◀─────┘                                        │
│   - Orchestrator                                                │
│   - Validator                                                   │
│   - Reporter                                                    │
│                                                                  │
│  Git Repos ──────────▶ Validator (clone/search)                  │
│  OpenAI API ◀────────── LLM 판정                                 │
└──────────────────────────────────────────────────────────────────┘
```

## Repository 구조

```
Giopaik/
├── compliance_extractor/       # PDF -> compliance_items 적재 API
├── agents/                     # Orchestrator/Validator/Reporter 워커
├── frontend/                   # Next.js UI
├── supabase/schema.sql         # documents/compliance_items 테이블
└── agents/sql/scan_schema.sql  # scans/scan_results 테이블
```

## 사전 준비

- **Python 3.10+** (compliance_extractor, agents)
- **Node 18+** (frontend)
- **Supabase 프로젝트 및 스키마 적용**
- **OpenAI API 키**

## 빠른 시작

### 1) Python 환경 구성

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r compliance_extractor/requirements.txt
```

### 2) Supabase 스키마 적용

아래 두 파일을 Supabase에 적용합니다.

1) `supabase/schema.sql` (documents + compliance_items)  
2) `agents/sql/scan_schema.sql` (scans + scan_results)

필수 테이블:

- `documents`: `filename`, `markdown_text`, `pdf_blob`, `page_count`, `language`
- `compliance_items`: `document_id`, `document_title`, `item_index`, `item_type`, `item_text`, `page`, `section`, `item_json`, `language`

### 3) 환경 변수 설정

루트 `.env` 또는 각 서비스 디렉터리의 `.env`에 다음을 설정하세요.

```bash
# OpenAI
OPENAI_API_KEY=sk-your-key
OPENAI_BASE_URL=https://api.openai.com/v1
GPT_MODEL=gpt-4o-mini

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=sb_secret_xxx
SUPABASE_ANON_KEY=sb_public_xxx
```

Frontend (`frontend/.env.local`)에는 다음을 설정하세요.

```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sb_public_xxx
```

## 실행 방법

### Compliance Extractor (PDF → DB)

```bash
uvicorn compliance_extractor.app:app --reload --port 8000
```

### Agents (Orchestrator / Validator / Reporter)

```bash
python -m agents.run orchestrator
python -m agents.run validator
python -m agents.run reporter
```

### Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev
```

## Compliance Extractor API

- `GET /health`: 헬스 체크
- `POST /upload`: PDF 업로드 → 규정 항목 추출 → Supabase 저장

```bash
curl -X POST \
  -F "files=@/path/to/regulation.pdf" \
  http://localhost:8000/upload
```

## 동작 흐름 (데모 시나리오)

1. 관리자 페이지에서 규정 PDF 업로드
2. Compliance Extractor가 `documents` / `compliance_items` 저장
3. 사용자가 레포지토리 URL과 규정 문서를 선택해 스캔 요청 생성
4. Orchestrator가 `scan_results` 작업 생성
5. Validator가 규정 항목별 검수 수행
6. Reporter가 결과 집계 및 리포트 생성

## Notes

- compliance_extractor는 OpenAI를 사용해 PDF 내용을 규정 항목 단위로 정규화/분할합니다.
- agents 파이프라인은 Supabase를 상태 저장소로 사용합니다.
- validator는 병렬 실행으로 스케일링 가능합니다.

## 문서

- `docs/IMPLEMENTATION_PLAN.md`: 아키텍처 및 구현 계획
- `agents/PLAN.md`: 에이전트 동작 설계

## License

MIT
