# Kompline Implementation Plan (Revised)

## Overview
- **Product**: Kompline (K-compliance + Pipeline)
- **Purpose**: Multi-agent continuous compliance system for Korean financial regulations
- **Target**: Algorithm fairness verification for deposit platforms (별지5 자가평가서)
- **Model**: (Compliance, Artifact) relation 기반 감사

## Core Concept: Audit Relation

```
Audit Relation = (Compliance, Artifact)

예시:
- (개인정보보호법, user-service repo) → Audit Agent #1
- (별지5 알고리즘공정성, user-service repo) → Audit Agent #2
- (SOC2, infrastructure repo) → Audit Agent #3
```

하나의 Artifact에 여러 Compliance를 적용하거나, 하나의 Compliance를 여러 Artifact에 적용 가능.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Audit Orchestrator (총괄)                         │
│  1. Build audit relations from user request                         │
│  2. Spawn Audit Agents per relation (parallel)                      │
│  3. Aggregate findings into unified report                          │
└─────────────────────────────────────────────────────────────────────┘
                              │ spawn per relation
        ┌─────────────────────┼─────────────────────────────┐
        ▼                     ▼                             ▼
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│    Audit Agent    │  │    Audit Agent    │  │    Audit Agent    │
│ (C₁, A₁)          │  │ (C₁, A₂)          │  │ (C₂, A₁)          │
├───────────────────┤  ├───────────────────┤  ├───────────────────┤
│ 1. Plan evidence  │  │ 1. Plan evidence  │  │ 1. Plan evidence  │
│ 2. Call Readers   │  │ 2. Call Readers   │  │ 2. Call Readers   │
│ 3. Evaluate rules │  │ 3. Evaluate rules │  │ 3. Evaluate rules │
│ 4. Emit findings  │  │ 4. Emit findings  │  │ 4. Emit findings  │
└────────┬──────────┘  └────────┬──────────┘  └────────┬──────────┘
         │ handoff to readers   │                      │
    ┌────┴────┐            ┌────┴────┐            ┌────┴────┐
    ▼         ▼            ▼         ▼            ▼         ▼
┌────────┐ ┌────────┐  ┌────────┐ ┌────────┐  ┌────────┐ ┌────────┐
│ Code   │ │  PDF   │  │ Code   │ │ Log/DB │  │  PDF   │ │ Config │
│ Reader │ │ Reader │  │ Reader │ │ Reader │  │ Reader │ │ Reader │
└────────┘ └────────┘  └────────┘ └────────┘  └────────┘ └────────┘
```

## Core Abstractions

### 1. Compliance (규정)
규제/사내규정/보안정책 등 규칙 집합

```python
@dataclass
class Compliance:
    id: str                      # "pipa-kr-2024", "byeolji5-fairness"
    name: str                    # "개인정보보호법", "별지5 알고리즘공정성"
    version: str                 # "2024.01"
    jurisdiction: str            # "KR", "global"
    scope: list[str]             # ["algorithm", "data_handling"]
    rules: list[Rule]            # 평가 규칙들
    evidence_requirements: list[EvidenceRequirement]
    report_template: str         # 보고서 템플릿 ID
```

### 2. Artifact (감사 대상)
감사 대상물 - 코드, 문서, DB, 로그 등

```python
@dataclass
class Artifact:
    id: str                      # "user-service-repo"
    type: ArtifactType           # CODE, PDF, LOG, DATABASE, CONFIG
    locator: str                 # "github://org/repo" or file path
    access_method: str           # "git_clone", "api", "file_read"
    extraction_schema: dict      # 추출할 데이터 스키마
    provenance: Provenance       # 출처 및 버전 정보
```

### 3. AuditRelation (감사 관계)
(Compliance, Artifact) 조합의 감사 단위

```python
@dataclass
class AuditRelation:
    id: str                      # "rel-001"
    compliance_id: str
    artifact_id: str
    status: AuditStatus          # PENDING, RUNNING, COMPLETED, FAILED
    evidence_collected: list[Evidence]
    findings: list[Finding]
    run_config: RunConfig        # 실행 설정
```

### 4. Evidence (증거)
Reader가 수집한 증거 자료

```python
@dataclass
class Evidence:
    id: str
    relation_id: str
    source: str                  # 증거 출처 (파일 경로, URL 등)
    type: EvidenceType           # CODE_SNIPPET, DOCUMENT_EXCERPT, LOG_ENTRY
    content: str                 # 실제 내용
    metadata: dict               # line_number, page, timestamp 등
    provenance: Provenance       # 출처 추적
    collected_at: datetime
    collected_by: str            # Reader Agent ID
```

### 5. Finding (발견사항)
Audit Agent의 평가 결과

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
    requires_human_review: bool
```

## Agent Definitions

### 1. Audit Orchestrator
- **역할**: 전체 감사 워크플로우 조율
- **입력**: 사용자 요청 (Compliance IDs + Artifact IDs)
- **책임**:
  1. AuditRelation 생성 (Cartesian product)
  2. Audit Agent 병렬 스폰
  3. Finding 집계
  4. 최종 리포트 생성 트리거

### 2. Audit Agent (per relation)
- **역할**: 단일 (Compliance, Artifact) 관계 감사
- **입력**: AuditRelation
- **책임**:
  1. Compliance의 evidence_requirements 분석
  2. 필요한 Reader Agent 결정 및 호출
  3. 수집된 Evidence로 규칙 평가
  4. Finding 생성

### 3. Reader Agents (artifact type별)

| Reader | Artifact Type | 추출 내용 |
|--------|---------------|-----------|
| **CodeReader** | CODE | AST, 함수 정의, 데이터 흐름, 패턴 |
| **PDFReader** | PDF | 텍스트, 테이블, 이미지 OCR |
| **LogDBReader** | LOG, DATABASE | 쿼리 결과, 로그 엔트리 |
| **ConfigReader** | CONFIG | YAML/JSON 설정값 |

### 4. Report Generator
- **역할**: 규정별 리포트 포맷 생성
- **입력**: 집계된 Findings + 템플릿 ID
- **출력**: 별지5, SOC2, 사내 포맷 등

## Key Features (OpenAI Agents SDK)

| Feature | Usage |
|---------|-------|
| **Agent** | Orchestrator + Audit Agents (동적) + Reader Agents |
| **handoff()** | Orchestrator → Audit → Reader chain |
| **@function_tool** | Evidence collection, rule evaluation, report export |
| **Guardrails** | Evidence validity + finding consistency |
| **Tracing** | Per-relation traces + global audit log |

## Human-in-the-Loop

### Trigger Conditions
1. **Confidence < 70%**: 불확실한 판단
2. **New Pattern**: 규칙에 없는 새로운 패턴
3. **FAIL Judgment**: 위반 사항은 반드시 확인
4. **Conflicting Evidence**: 상충되는 증거 발견

### Review Flow
```
Finding (REVIEW) → ReviewRequest 생성 → Queue에 추가
                                              ↓
피감사자 (Developer)  ←──── 컨텍스트 추가 요청
감사자 (Auditor)      ←──── 최종 승인/거부
                                              ↓
                           ReviewResponse → Finding 업데이트
```

## Implementation Phases

### Phase 1: Core Models & Registry
- [ ] Compliance, Artifact, AuditRelation 모델 정의
- [ ] Evidence, Finding 모델 정의
- [ ] ComplianceRegistry: 규정 등록/조회
- [ ] ArtifactRegistry: 대상물 등록/조회
- [ ] Provenance 추적 모델

### Phase 2: Reader Agents
- [ ] BaseReader 추상 클래스
- [ ] CodeReader (AST parsing, pattern detection)
- [ ] PDFReader (text extraction, 기존 RAG 활용)
- [ ] LogDBReader (query execution, log parsing)
- [ ] ConfigReader (YAML/JSON parsing)

### Phase 3: Audit Agent & Orchestrator
- [ ] AuditAgent (per-relation evaluation)
- [ ] RuleEvaluator (RAG + builtin rules)
- [ ] AuditOrchestrator (relation building, parallel spawn)
- [ ] Finding aggregation logic

### Phase 4: Report Generator
- [ ] ReportTemplate 모델
- [ ] 별지5 템플릿 구현
- [ ] Markdown/PDF 내보내기
- [ ] Evidence 참조 링킹

### Phase 5: Human-in-the-Loop
- [ ] ReviewTrigger 조건 구현
- [ ] ReviewQueue 관리
- [ ] Streamlit UI for review

### Phase 6: Guardrails & Tracing
- [ ] Evidence validity guardrail
- [ ] Finding consistency guardrail
- [ ] Per-relation tracing
- [ ] Global audit log

### Phase 7: Demo & Integration
- [ ] Multi-compliance demo scenario
- [ ] FastAPI endpoints
- [ ] Streamlit demo UI
- [ ] README 업데이트

## File Structure

```
kompline/
├── kompline/
│   ├── __init__.py
│   ├── models/                    # Core domain models
│   │   ├── __init__.py
│   │   ├── compliance.py          # Compliance, Rule
│   │   ├── artifact.py            # Artifact, ArtifactType
│   │   ├── audit_relation.py      # AuditRelation, RunConfig
│   │   ├── evidence.py            # Evidence, Provenance
│   │   └── finding.py             # Finding, FindingStatus
│   ├── registry/                  # Registries
│   │   ├── __init__.py
│   │   ├── compliance_registry.py
│   │   └── artifact_registry.py
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py        # Audit Orchestrator
│   │   ├── audit_agent.py         # Per-relation Audit Agent
│   │   ├── rule_evaluator.py      # Rule evaluation logic
│   │   ├── report_generator.py    # Report generation
│   │   └── readers/               # Reader Agents
│   │       ├── __init__.py
│   │       ├── base_reader.py     # Abstract base
│   │       ├── code_reader.py     # Python/JS code
│   │       ├── pdf_reader.py      # PDF documents
│   │       ├── log_db_reader.py   # Logs & databases
│   │       └── config_reader.py   # Config files
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── code_parser.py         # AST utilities
│   │   ├── rag_query.py           # RAG integration
│   │   └── report_export.py       # Export utilities
│   ├── guardrails/
│   │   ├── __init__.py
│   │   ├── evidence_validator.py
│   │   └── finding_validator.py
│   ├── hitl/
│   │   ├── __init__.py
│   │   ├── triggers.py
│   │   └── review_handler.py
│   ├── tracing/
│   │   ├── __init__.py
│   │   └── logger.py
│   └── runner.py
├── api/
│   └── main.py
├── ui/
│   └── app.py
├── config/
│   └── settings.py
├── samples/
│   ├── compliances/               # Sample compliance definitions
│   │   ├── byeolji5_fairness.yaml
│   │   └── pipa_kr.yaml
│   ├── artifacts/                 # Sample artifacts
│   │   └── deposit_ranking.py
│   └── demo_scenario.py
├── tests/
├── docs/
│   └── IMPLEMENTATION_PLAN.md
├── pyproject.toml
└── README.md
```

## Tech Stack
- Python 3.11+
- OpenAI Agents SDK (`openai-agents`)
- GPT-4o
- Streamlit (demo UI)
- FastAPI (API server)
- Existing RAG backend (rag_embedding/)

## Demo Scenario (3 min)

### 시나리오: 예금 추천 알고리즘 다중 규정 감사

1. **Setup** (30s)
   - Artifact: `samples/artifacts/deposit_ranking.py`
   - Compliance 1: 별지5 알고리즘공정성
   - Compliance 2: 개인정보보호법 (샘플)

2. **Demo** (90s)
   ```
   User: "deposit_ranking.py를 별지5와 개인정보보호법으로 감사해줘"

   Orchestrator: 2개의 AuditRelation 생성
   → AuditAgent(별지5, code) spawned
   → AuditAgent(개인정보보호법, code) spawned

   [병렬 실행]

   AuditAgent#1: CodeReader 호출 → Evidence 수집 → 규칙 평가
   AuditAgent#2: CodeReader 호출 → Evidence 수집 → 규칙 평가

   Findings 집계:
   - 별지5: 2 PASS, 1 FAIL (affiliate boost 발견)
   - 개인정보보호법: 3 PASS

   [FAIL → HITL trigger]

   ReportGenerator: 별지5 포맷으로 통합 리포트 생성
   ```

3. **Value** (30s)
   - 수동 2주 → 자동 2분
   - 다중 규정 동시 검증
   - 증거 기반 감사 추적

4. **Extensibility** (30s)
   - 새 규정: YAML로 Compliance 정의 추가
   - 새 Artifact 타입: Reader Agent 추가

## Verification Checklist

- [ ] Core 모델들 (Compliance, Artifact, Evidence, Finding) 정상 동작
- [ ] Registry에서 규정/아티팩트 조회
- [ ] Orchestrator가 AuditRelation 생성
- [ ] Audit Agent가 Reader 호출 후 Finding 생성
- [ ] 병렬 Audit Agent 실행
- [ ] HITL trigger 조건 동작
- [ ] 별지5 포맷 리포트 생성
- [ ] 다중 규정 시나리오 통과

## Migration from Current Implementation

현재 구현된 코드를 새 아키텍처로 전환:

| 기존 | 신규 | 마이그레이션 |
|------|------|-------------|
| `code_analyzer.py` | `readers/code_reader.py` | 리팩토링 |
| `rule_matcher.py` | `audit_agent.py` + `rule_evaluator.py` | 분리 |
| `report_generator.py` | 유지 | 템플릿 시스템 추가 |
| `guardrails/` | 유지 | Evidence/Finding 검증 추가 |
| `hitl/` | 유지 | Finding 기반으로 수정 |
| N/A | `models/` | 신규 생성 |
| N/A | `registry/` | 신규 생성 |
