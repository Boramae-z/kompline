# Kompline Implementation Plan (Revised)

## Overview
- **Product**: Kompline (K-compliance + Pipeline)
- **Purpose**: Multi-agent continuous compliance system for Korean financial regulations
- **Target**: Algorithm fairness verification for deposit platforms (별지5 자가평가서)
- **Model**: (ComplianceItem, Artifact) relation 기반 감사
- **Status**: 🔧 In progress (compliance_item 기반 설계로 업데이트)

## Core Concept: Audit Relation (ComplianceItem 단위)

```
Audit Relation = (ComplianceItem, Artifact)

예시:
- (PIPA-001 최소수집, user-service repo) → Inspection Agent #1
- (PIPA-002 보유기간, user-service repo) → Inspection Agent #2
- (BYEOLJI5-ALG-003 무작위화 공개, ranking repo) → Inspection Agent #3
```

하나의 Compliance는 여러 ComplianceItem으로 분해되며,
각 ComplianceItem은 독립적으로 감사를 수행하고 결과를 병합해 보고서를 작성.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Audit Orchestrator (총괄)                         │
│  1. Build relations per ComplianceItem × Artifact                    │
│  2. Spawn Inspection Agents (parallel)                               │
│  3. Aggregate item-level findings into compliance report             │
└─────────────────────────────────────────────────────────────────────┘
                              │ spawn per item
        ┌─────────────────────┼─────────────────────────────┐
        ▼                     ▼                             ▼
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│ Inspection Agent  │  │ Inspection Agent  │  │ Inspection Agent  │
│ (Item₁, A₁)       │  │ (Item₂, A₁)       │  │ (Item₃, A₂)       │
├───────────────────┤  ├───────────────────┤  ├───────────────────┤
│ 1. Code search    │  │ 1. Code search    │  │ 1. Code search    │
│ 2. Collect evidence via Readers                           │
│ 3. Evaluate single item (LLM/Heuristic)                   │
└────────┬──────────┘  └────────┬──────────┘  └────────┬──────────┘
         │ call search/reader agents                      │
    ┌────┴────┐            ┌────┴────┐            ┌────┴────┐
    ▼         ▼            ▼         ▼            ▼         ▼
CodeSearch  CodeReader   CodeSearch  PDFReader  CodeSearch  ConfigReader
```

## Core Abstractions (Proposed)

### 1. Compliance (규정) - `kompline/models/compliance.py`

```python
@dataclass
class Compliance:
    id: str                      # "pipa-kr-2024", "byeolji5-fairness"
    name: str                    # "개인정보보호법", "별지5 알고리즘공정성"
    version: str                 # "2024.01"
    jurisdiction: str            # "KR", "global"
    scope: list[str]             # ["algorithm", "data_handling"]
    items: list[ComplianceItem]  # 규정 내 세부 항목들
    evidence_requirements: list[EvidenceRequirement]
    report_template: str         # 보고서 템플릿 ID
    description: str             # 규정 설명
```

### 2. ComplianceItem (규정 항목) - `kompline/models/compliance_item.py`

```python
@dataclass
class ComplianceItem:
    id: str                      # "PIPA-001"
    compliance_id: str           # 상위 규정 ID
    title: str                   # "최소 수집 원칙"
    description: str
    category: str
    severity: str
    evidence_requirements: list[EvidenceRequirement]
    check_points: list[str]
```

### 3. Artifact (감사 대상) - `kompline/models/artifact.py`

```python
@dataclass
class Artifact:
    id: str                      # "user-service-repo"
    name: str                    # 표시 이름
    type: ArtifactType           # CODE, PDF, LOG, CONFIG
    locator: str                 # "github://org/repo" or file path
    access_method: AccessMethod  # FILE_READ, GIT_CLONE, API
    provenance: Provenance       # 출처 및 버전 정보
    tags: list[str]              # 분류 태그
```

### 4. AuditRelation (감사 관계) - `kompline/models/audit_relation.py`

```python
@dataclass
class AuditRelation:
    id: str                      # "rel-001"
    compliance_item_id: str
    artifact_id: str
    status: AuditStatus          # PENDING, RUNNING, COMPLETED, FAILED
    evidence_collected: EvidenceCollection
    findings: list[Finding]
    run_config: RunConfig        # 실행 설정 (use_llm, etc.)
    error_message: str | None    # 실패 시 오류 메시지
```

### 5. Evidence (증거) - `kompline/models/evidence.py`

```python
@dataclass
class Evidence:
    id: str
    relation_id: str
    source: str                  # 증거 출처 (파일 경로, URL 등)
    type: EvidenceType           # CODE_SNIPPET, DOCUMENT_EXCERPT, CONFIG_VALUE
    content: str                 # 실제 내용
    metadata: dict               # line_number, page, timestamp 등
    provenance: Provenance       # 출처 추적
    collected_at: datetime
```

### 6. Finding (발견사항) - `kompline/models/finding.py`

```python
@dataclass
class Finding:
    id: str
    relation_id: str
    rule_id: str
    status: FindingStatus        # PASS, FAIL, REVIEW, NOT_APPLICABLE
    confidence: float            # 0.0 ~ 1.0
    evidence_refs: list[str]     # 관련 Evidence IDs
    reasoning: str               # 판단 근거
    recommendation: str | None   # FAIL인 경우 개선 권고
    citations: list[Citation]    # RAG 출처 인용
    requires_human_review: bool
    review_status: ReviewStatus  # PENDING, APPROVED, REJECTED, MODIFIED
```

### 7. Citation (출처 인용) - `kompline/models/finding.py`

```python
@dataclass
class Citation:
    source: str                  # "별지5 제3조 제2항"
    text: str                    # 관련 규정 텍스트
    relevance: float             # 0.0 ~ 1.0
    page: int | None             # 페이지 번호
    section: str | None          # 섹션/조항 참조
```

## Agent Definitions (Proposed)

### 1. Audit Orchestrator - `kompline/agents/audit_orchestrator.py`
- **역할**: ComplianceItem 단위 관계 생성 + 병렬 실행 + 결과 병합

### 2. Inspection Agent - `kompline/agents/inspection_agent.py`
- **역할**: 단일 ComplianceItem × Artifact 검수
- **특징**:
  - CodeSearch Agent 호출로 관련 코드 범위 탐색
  - Reader Agents로 증거 수집
  - LLM/Heuristic로 단일 항목 판정

### 3. Code Search Agent - `kompline/agents/code_search_agent.py`
- **역할**: 컴플라이언스 항목의 키워드/패턴으로 코드 범위 탐색
- **출력**: 파일 경로 + 라인 범위 + 이유

### 4. Reader Agents - `kompline/agents/readers/`

| Reader | 파일 | 기능 |
|--------|------|------|
| **BaseReader** | `base_reader.py` | 추상 베이스 클래스 |
| **CodeReader** | `code_reader.py` | AST 파싱, 패턴 감지, 데이터 흐름 |
| **PDFReader** | `pdf_reader.py` | 텍스트/테이블 추출 |
| **ConfigReader** | `config_reader.py` | YAML/JSON 파싱 |

### 4. Rule Evaluator - `kompline/agents/rule_evaluator.py`
- 카테고리별 평가 로직 (Algorithm Fairness, Transparency, Disclosure)
- RAG 기반 규칙 조회
- Citation 연결

### 5. Report Generator - `kompline/agents/report_generator.py`
- 별지5 포맷 리포트
- Markdown/JSON 내보내기
- Citation 표시

## Key Features (Planned / Partial)

| Feature | 구현 상태 | 파일 |
|---------|----------|------|
| **Retry + Backoff** | ✅ | `audit_orchestrator.py` |
| **Fallback Strategies** | ✅ | `audit_orchestrator.py` |
| **LLM + Heuristic** | ✅ | `audit_agent.py` |
| **RAG Citations** | ✅ | `finding.py`, `rag_query.py` |
| **Evidence Validation** | ✅ | `guardrails/evidence_validator.py` |
| **Finding Validation** | ✅ | `guardrails/finding_validator.py` |
| **HITL Triggers** | ✅ | `hitl/triggers.py` |
| **Tracing** | ✅ | `tracing/logger.py` |
| **Supabase Integration** | ✅ | `providers/supabase_provider.py` |

## Supabase Integration (New)

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Supabase DB                                  │
│   ┌─────────────┐    ┌──────────────────┐                       │
│   │  documents  │───→│ compliance_items │                       │
│   └─────────────┘    └──────────────────┘                       │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SupabaseProvider                               │
│   • fetch_items_by_document(document_id)                         │
│   • fetch_items_by_type(item_type)                               │
│   • fetch_all_items(language)                                    │
│   • map_row_to_rule() → Rule 객체 변환                            │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│              ComplianceRegistry.load_from_supabase()             │
│   • 규정 로드 → Compliance 객체 생성 → Registry 등록              │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Audit Workflow                                │
│   Compliance → AuditOrchestrator → Inspection Agents → Report   │
└─────────────────────────────────────────────────────────────────┘
```

### DB Schema

```sql
-- documents
- id (bigserial, PK)
- filename, markdown_text, pdf_blob, page_count, language, created_at

-- compliance_items
- id (bigserial, PK)
- document_id (FK → documents.id)
- document_title, item_index, item_type, item_text
- page, section, item_json (jsonb), language, created_at
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| **SupabaseProvider** | `kompline/providers/supabase_provider.py` | REST API로 DB 조회, Rule 변환 |
| **ComplianceItemRow** | `kompline/providers/supabase_provider.py` | DB 행 데이터클래스 |
| **load_from_supabase()** | `kompline/registry/compliance_registry.py` | DB에서 Compliance 로드 |

### Usage

```python
from kompline.registry import get_compliance_registry
import asyncio

async def main():
    registry = get_compliance_registry()

    # 방법 1: 특정 문서의 규정 로드
    compliance = await registry.load_from_supabase(
        document_id=1,
        language="ko",
        compliance_id="byeolji5-db",
    )

    # 방법 2: 특정 타입의 규정 로드
    compliance = await registry.load_from_supabase(
        item_type="algorithm_fairness",
    )

    # 방법 3: 전체 규정 로드
    compliance = await registry.load_from_supabase(language="ko")

    print(f"Loaded {len(compliance.rules)} rules")

asyncio.run(main())
```

### Environment Variables

```bash
# .env
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=sb_secret_xxx
```

### item_type → RuleCategory Mapping

| DB item_type | RuleCategory |
|--------------|--------------|
| `algorithm_fairness`, `fairness` | ALGORITHM_FAIRNESS |
| `data_handling` | DATA_HANDLING |
| `transparency` | TRANSPARENCY |
| `disclosure` | DISCLOSURE |
| `privacy` | PRIVACY |
| `security` | SECURITY |

## Human-in-the-Loop (Implemented)

### Trigger Conditions - `kompline/hitl/triggers.py`
1. **Confidence < 70%**: 불확실한 판단
2. **New Pattern**: 규칙에 없는 새로운 패턴
3. **FAIL Judgment**: 위반 사항은 반드시 확인
4. **Conflicting Evidence**: 상충되는 증거 발견

### Review Flow - `kompline/hitl/review_handler.py`
```
Finding (FAIL/REVIEW) → ReviewRequest 생성 → Queue에 추가
                                              ↓
피감사자 (Developer)  ←──── 컨텍스트 추가 요청
감사자 (Auditor)      ←──── 최종 승인/거부
                                              ↓
                           ReviewResponse → Finding 업데이트
```

## Implementation Phases (All Complete)

### Phase 1: Core Models & Registry ✅
- [x] Compliance, Artifact, AuditRelation 모델 정의
- [x] Evidence, Finding, Citation 모델 정의
- [x] ComplianceRegistry: 규정 등록/조회/YAML 로드
- [x] ArtifactRegistry: 대상물 등록/조회
- [x] Provenance 추적 모델

### Phase 2: Reader Agents ✅
- [x] BaseReader 추상 클래스
- [x] CodeReader (AST parsing, pattern detection)
- [x] PDFReader (text extraction)
- [x] ConfigReader (YAML/JSON parsing)

### Phase 3: Audit Agent & Orchestrator ✅
- [x] AuditAgent (per-relation evaluation, LLM + heuristic)
- [x] RuleEvaluator (RAG + builtin rules)
- [x] AuditOrchestrator (relation building, parallel spawn, retry)
- [x] Finding aggregation logic
- [x] Citation 연결

### Phase 4: Report Generator ✅
- [x] ReportTemplate 모델
- [x] 별지5 템플릿 구현
- [x] Markdown 내보내기
- [x] Evidence/Citation 참조 링킹

### Phase 5: Human-in-the-Loop ✅
- [x] ReviewTrigger 조건 구현
- [x] ReviewQueue 관리
- [x] Streamlit UI for review

### Phase 6: Guardrails & Tracing ✅
- [x] Evidence validity guardrail
- [x] Finding consistency guardrail
- [x] Per-relation tracing
- [x] Global audit log

### Phase 7: Demo & Integration ✅
- [x] Multi-compliance demo scenario (`demo.py`)
- [x] FastAPI endpoints (`api/main.py`)
- [x] Streamlit demo UI (`ui/app.py`)
- [x] CLI runner (`kompline/runner.py`)
- [x] README 업데이트

### Phase 8: Supabase Integration ✅
- [x] SupabaseProvider (REST API 기반 DB 조회)
- [x] ComplianceItemRow 데이터클래스
- [x] ComplianceRegistry.load_from_supabase() 메서드
- [x] item_type → RuleCategory 매핑
- [x] 캐싱 (TTL 기반)
- [x] 단위 테스트 (23개 통과)

## File Structure (Current)

```
kompline/
├── kompline/
│   ├── __init__.py
│   ├── models/                    # Core domain models
│   │   ├── __init__.py            # All model exports
│   │   ├── compliance.py          # Compliance, Rule, RuleCategory
│   │   ├── artifact.py            # Artifact, ArtifactType, Provenance
│   │   ├── audit_relation.py      # AuditRelation, RunConfig
│   │   ├── evidence.py            # Evidence, EvidenceCollection
│   │   └── finding.py             # Finding, Citation, FindingStatus
│   ├── registry/                  # Registries
│   │   ├── __init__.py
│   │   ├── compliance_registry.py # YAML 로드 + Supabase 로드 지원
│   │   └── artifact_registry.py   # 파일/저장소 등록
│   ├── providers/                 # External data providers
│   │   ├── __init__.py
│   │   ├── github_provider.py     # GitHub API
│   │   └── supabase_provider.py   # Supabase REST API
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── audit_orchestrator.py  # RetryConfig, 재분배 전략
│   │   ├── audit_agent.py         # LLM + Heuristic, Citation
│   │   ├── rule_evaluator.py      # 카테고리별 평가
│   │   ├── report_generator.py    # 별지5, Markdown
│   │   ├── orchestrator.py        # Legacy SDK handoff
│   │   ├── code_analyzer.py       # Legacy
│   │   ├── rule_matcher.py        # Legacy
│   │   └── readers/
│   │       ├── __init__.py
│   │       ├── base_reader.py
│   │       ├── code_reader.py     # AST + 패턴 감지
│   │       ├── pdf_reader.py
│   │       └── config_reader.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── code_parser.py         # AST utilities
│   │   ├── rag_query.py           # RAG + Citation
│   │   └── report_export.py       # Export utilities
│   ├── guardrails/
│   │   ├── __init__.py
│   │   ├── input_validator.py     # 소스 코드 검증
│   │   ├── output_validator.py    # 품질 검사
│   │   ├── evidence_validator.py  # Evidence 검증
│   │   └── finding_validator.py   # Finding 일관성
│   ├── hitl/
│   │   ├── __init__.py
│   │   ├── triggers.py            # 리뷰 트리거 조건
│   │   └── review_handler.py      # ReviewQueue
│   ├── tracing/
│   │   ├── __init__.py
│   │   └── logger.py              # 감사 로깅
│   ├── utils/
│   │   ├── __init__.py
│   │   └── json_utils.py          # JSON 추출
│   ├── demo_data.py               # 데모 데이터 헬퍼
│   └── runner.py                  # CLI + KomplineRunner
├── api/
│   ├── __init__.py
│   └── main.py                    # FastAPI 서버
├── ui/
│   └── app.py                     # Streamlit 데모
├── config/
│   ├── __init__.py
│   └── settings.py                # 환경 설정
├── samples/
│   ├── compliances/
│   │   ├── byeolji5_fairness.yaml
│   │   └── pipa_kr.yaml
│   ├── deposit_ranking.py         # 샘플 코드 (위반 포함)
│   └── demo_scenario.py           # 데모 시나리오
├── tests/
│   ├── __init__.py
│   ├── test_supabase_provider.py      # SupabaseProvider 단위 테스트
│   ├── test_compliance_registry_supabase.py  # Registry Supabase 테스트
│   └── test_supabase_integration.py   # 통합 테스트 (DB 필요)
├── docs/
│   ├── IMPLEMENTATION_PLAN.md     # 이 문서
│   └── audits/                    # 규제 양식 PDF
├── demo.py                        # 메인 데모 스크립트
├── pyproject.toml
└── README.md
```

## Running the Demo

### Quick Start

```bash
# 1. Install dependencies
pip install -e .

# 2. Set environment variables
export OPENAI_API_KEY=sk-your-key
export SUPABASE_URL=https://xxx.supabase.co
export SUPABASE_SERVICE_ROLE_KEY=sb_secret_xxx

# 3. Run demo
python demo.py
```

### Expected Output

```
============================================================
  Kompline - 금융규제 준수 자동 감사 시스템
============================================================

🚀 Multi-Agent Compliance Audit Demo
   별지5 알고리즘 공정성 자가평가

📜 Loaded: 별지5 알고리즘공정성 (3 rules)
📁 Registered: 예금상품 추천 알고리즘

🔍 Running audit...
   ❌ ALG-001: FAIL (85%) - shuffle() 감지
   ❌ ALG-002: FAIL (85%) - affiliate bias 감지
   ❌ ALG-003: FAIL (85%) - preferred keyword 감지

🧑‍⚖️ Human Review Queue: 3 items
```

### Alternative Interfaces

```bash
# CLI
python -m kompline.runner samples/deposit_ranking.py --compliance byeolji5-fairness

# API Server
uvicorn api.main:app --port 8080

# Streamlit UI
streamlit run ui/app.py
```

## Verification Checklist (All Passed)

- [x] Core 모델들 (Compliance, Artifact, Evidence, Finding) 정상 동작
- [x] Registry에서 규정/아티팩트 조회
- [x] Orchestrator가 AuditRelation 생성
- [x] Audit Agent가 Reader 호출 후 Finding 생성
- [x] 병렬 Audit Agent 실행
- [x] HITL trigger 조건 동작
- [x] 별지5 포맷 리포트 생성
- [x] 다중 규정 시나리오 통과
- [x] Retry + 재분배 로직 동작
- [x] RAG Citation 출력
- [x] Supabase에서 규정 로드 (17개 항목 확인)
- [x] SupabaseProvider 단위 테스트 (15개 통과)
- [x] ComplianceRegistry Supabase 테스트 (8개 통과)

## Tech Stack

- Python 3.11+
- OpenAI Agents SDK (`openai-agents`) - optional, heuristic fallback available
- GPT-4o (when LLM enabled)
- Streamlit (demo UI)
- FastAPI (API server)
- Existing RAG backend (`rag_embedding/`)

## B2B Value Proposition

| Before (Manual) | After (Kompline) |
|-----------------|------------------|
| 2-3 weeks per audit | **2-3 minutes** automated |
| Single compliance | **Multi-compliance parallel** |
| Inconsistent evidence | **Structured with provenance** |
| Paper-based reports | **Digital 별지5** with citations |

**ROI**:
- 80% reduction in audit time
- Consistent rule application
- Full audit trail for regulators
- Scalable to multiple repos/products
