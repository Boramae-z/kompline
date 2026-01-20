# Kompline PRD (Product Requirements Document)

> **Kompline** = K-Compliance + Pipeline
> 금융권, 레그테크 기업을 위한 멀티에이전트 지속 준수 시스템 (Continuous Compliance System)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Target Market & Customer Segments](#2-target-market--customer-segments)
3. [User Personas & Use Cases](#3-user-personas--use-cases)
4. [System Architecture](#4-system-architecture)
5. [Core Features & Functional Requirements](#5-core-features--functional-requirements)
6. [Roadmap & Future Vision](#6-roadmap--future-vision)
7. [Non-Functional Requirements](#7-non-functional-requirements)
8. [Success Metrics & KPIs](#8-success-metrics--kpis)
9. [Competitive Analysis & Differentiation](#9-competitive-analysis--differentiation)
10. [Risks & Mitigations](#10-risks--mitigations)
11. [Glossary & Appendix](#11-glossary--appendix)

---

## 1. Executive Summary

### Product Overview

**Kompline (K-Compliance + Pipeline)**

금융권, 레그테크 기업 등 높은 수준의 컴플라이언스 관리가 요구되는 조직을 위한 **멀티에이전트 지속 준수 시스템(Continuous Compliance System)**.

### Problem

규제 산업의 실무자들은 국내외 법률, 산업 표준, 사내 규정 등 복잡한 규정 체계를 준수해야 하며, 이는 주기적 감사를 통해 관리된다. 그러나 현행 감사 방식은:

- **감사자**: 수작업 점검으로 2-3주 소요, 인적 오류 발생
- **피감사자**: 증빙자료 수집에 막대한 업무 부하
- **실무자**: 감사 기간 사이 규정 위반 리스크 상존

### Solution

Kompline은 코드, 로그, 데이터 등 기업 산출물을 **수시로 자동 분석**하여:

| 사용자 | 제공 가치 |
|--------|-----------|
| 감사자 | 자동 점검 및 규정 준수 리포팅 |
| 피감사자 | 증빙자료 자동 생성 (Provenance 추적) |
| 실무자 | 업무 착수 전 규정 적합성 사전 검토 |

### Core Value Proposition

> **"주기적 감사에서 Continuous Compliance로"**

- 감사 소요 시간: 2-3주 → **2-3분**
- 다중 규정 병렬 검사
- 규제당국 제출 가능한 감사 증적 (Citation 기반)

---

## 2. Target Market & Customer Segments

### 시장 개요

**TAM (Total Addressable Market)**
- 글로벌 RegTech 시장: $12.8B (2024) → $30.4B (2028), CAGR 18.4%
- 국내 금융 컴플라이언스 시장: 약 1.2조원 (금융사 내부통제 비용 기준)

**SAM (Serviceable Addressable Market)**
- 국내 금융사 및 핀테크 기업의 알고리즘/AI 규제 대응 수요
- 금융위 "금융분야 AI 가이드라인" 시행으로 시장 확대 예상

### 타겟 고객 (우선순위순)

#### 1. 금융사 (은행, 증권, 보험)
- **Pain Point**: 내부 컴플라이언스팀의 반복적 수작업, 규제 변경 대응 지연
- **Use Case**: 알고리즘 공정성 자가평가, 개인정보보호법 준수 점검
- **Decision Maker**: 준법감시인(CCO), IT 부서장

#### 2. 핀테크/플랫폼 기업
- **Pain Point**: 빠른 개발 주기 vs 규제 준수 검증 병목
- **Use Case**: 예금/대출 비교 서비스의 추천 알고리즘 공정성 검증
- **Decision Maker**: CTO, CPO

#### 3. 감사법인/컨설팅
- **Pain Point**: 다수 클라이언트 감사 시 일관성 확보 어려움
- **Use Case**: 외부 감사 업무 효율화, 표준화된 감사 리포트 생성
- **Decision Maker**: 파트너, 감사팀 리더

### 고객별 기대 ROI

| 고객 유형 | Before | After | 절감 효과 |
|-----------|--------|-------|-----------|
| 금융사 | 감사당 2-3주 | 2-3분 | 인력 비용 80% 절감 |
| 핀테크 | 출시 지연 2주 | 실시간 검증 | Time-to-Market 단축 |
| 감사법인 | 클라이언트당 40시간 | 4시간 | 처리량 10배 증가 |

---

## 3. User Personas & Use Cases

### Persona 1: 감사자 (Auditor)

**프로필**
- 역할: 금융사 준법감시팀, 외부 감사법인 담당자
- 목표: 규정 준수 여부를 객관적으로 검증하고 보고서 작성
- 불만: 수작업 점검의 비효율, 증거 수집의 일관성 부족

**User Story**
> "감사 대상 시스템의 코드와 설정을 자동으로 분석하여 규정 위반 여부를 판정하고, 근거가 명시된 감사 보고서를 생성하고 싶다."

**주요 기능**
- 자동 규정 점검 실행 (다중 규정 병렬)
- Citation 기반 위반 근거 제시
- 규제당국 제출용 리포트 생성 (자가평가서 양식)

---

### Persona 2: 피감사자 (Auditee)

**프로필**
- 역할: 서비스 개발팀 리더, DevOps 엔지니어
- 목표: 감사 요청에 신속히 대응, 증빙자료 준비 부담 최소화
- 불만: 감사 때마다 동일한 자료를 반복 수집, 어떤 증거가 필요한지 불명확

**User Story**
> "감사에 필요한 증빙자료가 자동으로 수집되고, 어떤 부분이 규정을 충족하는지 미리 확인하고 싶다."

**주요 기능**
- 코드/로그/설정에서 Evidence 자동 추출
- Provenance 추적 (출처, 버전, 수집 시점)
- 감사 전 Self-check 리포트

---

### Persona 3: 실무자 (Practitioner)

**프로필**
- 역할: 백엔드 개발자, 데이터 사이언티스트
- 목표: 개발 중인 코드가 규정에 위배되는지 사전 확인
- 불만: 규정 문서가 방대하고 해석이 어려움, 감사 후에야 문제 발견

**User Story**
> "커밋하기 전에 내 코드가 알고리즘 공정성 규정을 위반하는지 바로 확인하고 싶다."

**주요 기능**
- Pre-commit / PR 단계 규정 적합성 검사
- 위반 시 구체적 개선 권고 (Recommendation)
- IDE/CI 통합으로 개발 워크플로우에 자연스럽게 연결

---

### Use Case Matrix

| Use Case | 감사자 | 피감사자 | 실무자 |
|----------|:------:|:--------:|:------:|
| 정기 감사 실행 | ● | ○ | |
| 증빙자료 자동 생성 | ○ | ● | |
| 사전 규정 검토 | | ○ | ● |
| 감사 리포트 생성 | ● | ○ | |
| CI/CD 통합 검사 | | ○ | ● |
| HITL 리뷰 승인 | ● | ● | |

*(●: Primary, ○: Secondary)*

---

## 4. System Architecture

### 아키텍처 개요

Kompline은 **멀티에이전트 협업 구조**를 기반으로 복잡한 컴플라이언스 검사를 병렬 처리한다.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Kompline Platform                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐  │
│  │ Supabase DB │    │   GitHub    │    │      OpenAI API         │  │
│  │ (Rules)     │    │ (Artifacts) │    │  ┌─────────────────────┐│  │
│  └──────┬──────┘    └──────┬──────┘    │  │ gpt-4o: 규정 판정   ││  │
│         │                  │           │  │ gpt-4o-mini: RAG    ││  │
│         │                  │           │  └─────────────────────┘│  │
│         ▼                  ▼           └────────────┬────────────┘  │
│  ┌──────────────────────────────────┐               │               │
│  │      Registry Layer              │               │               │
│  │  ComplianceRegistry │ ArtifactRegistry          │               │
│  └──────────────┬───────────────────┘               │               │
│                 │                                   │               │
│                 ▼                                   │               │
│  ┌──────────────────────────────────────────────────┼──────────────┐│
│  │              Audit Orchestrator                  │              ││
│  │  • (Rule, Artifact) 관계 생성                    │              ││
│  │  • Inspection Agent 병렬 스폰                    │              ││
│  │  • 에러 재시도 및 작업 재분배                    │              ││
│  └──────────────────────┬───────────────────────────┼──────────────┘│
│                         │                           │               │
│         ┌───────────────┼───────────────┐           │               │
│         ▼               ▼               ▼           │               │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │               │
│  │ Inspection  │ │ Inspection  │ │ Inspection  │◄──┘ (gpt-4o)     │
│  │ Agent #1    │ │ Agent #2    │ │ Agent #N    │    LLM 판정      │
│  │ ┌─────────┐ │ │             │ │             │    or Heuristic  │
│  │ │Heuristic│ │ │             │ │             │    Fallback      │
│  │ │Fallback │ │ │             │ │             │                  │
│  │ └─────────┘ │ │             │ │             │                  │
│  └──────┬──────┘ └─────────────┘ └─────────────┘                  │
│         │                                                          │
│         ▼                                                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     Reader Agents                            │   │
│  │   CodeReader │ PDFReader │ ConfigReader │ LogReader          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                             │                                       │
│                             ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  RAG Engine ◄───────────────────────────────── (gpt-4o-mini)│   │
│  │  • 규정 텍스트 임베딩 검색                                    │   │
│  │  • Citation 생성 (출처 명시)                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │
│  │  Guardrails  │  │     HITL     │  │   Tracing    │              │
│  │  (Validator) │  │   (Review)   │  │   (Logger)   │              │
│  └──────────────┘  └──────────────┘  └──────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
```

### 핵심 컴포넌트

| 컴포넌트 | 역할 | 특징 |
|----------|------|------|
| **Audit Orchestrator** | 전체 감사 워크플로우 조율 | 병렬 실행, 에러 재시도/재분배 |
| **Inspection Agent** | 개별 (규정, 산출물) 쌍 검사 | LLM + Heuristic 하이브리드 판정 |
| **Reader Agents** | 산출물 유형별 증거 추출 | Code/PDF/Config/Log 파서 |
| **RAG Engine** | 규정 조회 및 Citation 생성 | 출처 명시로 할루시네이션 방지 |
| **Guardrails** | 입출력 검증 | Evidence/Finding 일관성 보장 |
| **HITL Module** | 사람 검토 트리거 | 저신뢰도, FAIL 판정 시 활성화 |

### 데이터 흐름

| 데이터 | 소스 | 처리 |
|--------|------|------|
| **규정 (Rules)** | Supabase DB (compliance_items 테이블) | SupabaseProvider → ComplianceRegistry |
| **산출물 (Artifacts)** | GitHub, 로컬 파일 | ArtifactRegistry |
| **증거 (Evidence)** | Reader Agents | Inspection Agent가 수집 |
| **판정 (Finding)** | LLM + Heuristic | RAG Citation 첨부 |

### OpenAI API 호출 지점

| 컴포넌트 | 용도 | 모델 | Fallback |
|----------|------|------|----------|
| **Inspection Agent** | 규정 위반 판정 (PASS/FAIL) | gpt-4o | Heuristic (룰 기반) |
| **RAG Engine** | 임베딩 + Citation 생성 | gpt-4o-mini | - |

### LLM + Heuristic 하이브리드 전략

```
사용자 요청
    │
    ▼
┌─────────────┐
│ use_llm=true│───Yes──▶ OpenAI API 호출 (gpt-4o)
└─────────────┘                    │
    │ No                           ▼
    │                    ┌─────────────────┐
    ▼                    │ API 성공?       │
┌─────────────┐          └────────┬────────┘
│ Heuristic   │◀────No────────────┘
│ (룰 기반)   │                    │ Yes
└─────────────┘                    ▼
                         ┌─────────────────┐
                         │ LLM Finding     │
                         └─────────────────┘
```

**왜 하이브리드인가?**
- LLM: 복잡한 맥락 이해, 자연어 규정 해석
- Heuristic: 비용 절감, 빠른 응답, API 장애 대응

### 에이전트 협업 흐름

```
1. Orchestrator가 (Compliance, Artifact) 관계 매트릭스 생성
       ↓
2. 각 관계에 대해 Inspection Agent 병렬 스폰
       ↓
3. Inspection Agent가 Reader 호출하여 Evidence 수집
       ↓
4. RAG로 관련 규정 조회 → LLM/Heuristic으로 판정
       ↓
5. Finding 생성 (PASS/FAIL/REVIEW) + Citation 첨부
       ↓
6. 실패 시 재시도 또는 다른 Agent에 재분배
       ↓
7. 결과 집계 → Report 생성 → HITL 큐 등록
```

---

## 5. Core Features & Functional Requirements

### Feature 1: 자동 컴플라이언스 검사

**설명**
규정(Rule)과 산출물(Artifact)의 모든 조합에 대해 자동으로 준수 여부를 검사한다.

| 항목 | 상세 |
|------|------|
| **입력** | Compliance (from Supabase), Artifact (Code/Config/Log) |
| **처리** | 병렬 Inspection Agent 실행, LLM/Heuristic 판정 |
| **출력** | Finding (PASS/FAIL/REVIEW) + Evidence + Citation |

**기능 요구사항**
- FR-1.1: 다중 규정을 동시에 병렬 검사할 수 있어야 한다
- FR-1.2: 검사 실패 시 자동 재시도 (최대 3회, exponential backoff)
- FR-1.3: 재시도 실패 시 다른 Agent에 작업 재분배
- FR-1.4: LLM 장애 시 Heuristic으로 자동 Fallback

---

### Feature 2: 증거 자동 수집 (Evidence Collection)

**설명**
다양한 형태의 산출물에서 규정 준수 증거를 자동 추출한다.

| Reader | 대상 | 추출 내용 |
|--------|------|-----------|
| **CodeReader** | .py, .js, .java 등 | AST 패턴, 함수 호출, 데이터 흐름 |
| **ConfigReader** | .yaml, .json | 설정값, 환경변수 |
| **PDFReader** | .pdf | 텍스트, 테이블 |
| **LogReader** | .log | 이벤트, 타임스탬프 |

**기능 요구사항**
- FR-2.1: 각 Evidence에 Provenance(출처, 버전, 수집시점) 기록
- FR-2.2: 코드의 경우 파일 경로 + 라인 번호 명시
- FR-2.3: 민감정보(API Key 등) 자동 마스킹

---

### Feature 3: Citation 기반 판정 근거

**설명**
모든 판정(Finding)에 규정 원문 출처를 명시하여 할루시네이션을 방지한다.

```
Finding: FAIL (confidence: 85%)
Reasoning: 추천 알고리즘에서 제휴사 우대 로직 감지
Citation:
  - source: "알고리즘 공정성 자가평가 제3조 제2항"
    text: "금융상품의 추천·비교 시 특정 상품을 부당하게 우대하거나
           차별하여서는 아니 된다"
    relevance: 0.92
```

**기능 요구사항**
- FR-3.1: RAG로 관련 규정 검색 후 Citation 자동 첨부
- FR-3.2: Citation에 relevance score 포함
- FR-3.3: 다중 Citation 지원 (복합 위반 시)

---

### Feature 4: Human-in-the-Loop (HITL)

**설명**
자동 판정이 불확실하거나 위반 사항 발견 시 사람 검토를 요청한다.

| 트리거 조건 | 설명 |
|-------------|------|
| Confidence < 70% | LLM 판정 신뢰도 낮음 |
| FAIL 판정 | 모든 위반 사항은 사람 확인 필수 |
| New Pattern | 기존 규칙에 없는 새로운 패턴 |
| Conflicting Evidence | 상충되는 증거 발견 |

**기능 요구사항**
- FR-4.1: Review Queue에 검토 요청 자동 등록
- FR-4.2: 감사자가 APPROVE/REJECT/MODIFY 가능
- FR-4.3: 피감사자에게 추가 컨텍스트 요청 가능
- FR-4.4: 검토 결과가 Finding에 반영

---

### Feature 5: 감사 리포트 생성

**설명**
규제당국 제출용 자가평가서 양식의 리포트를 자동 생성한다.

| 포맷 | 용도 |
|------|------|
| **자가평가서 (별지5 양식)** | 금융당국 제출용 |
| **Markdown** | 내부 공유, GitHub PR 코멘트 |
| **JSON** | 시스템 연동, API 응답 |

**기능 요구사항**
- FR-5.1: 자가평가서 양식 준수 (항목별 준수/미준수/해당없음)
- FR-5.2: Evidence 참조 링크 포함
- FR-5.3: Citation 기반 판정 근거 명시
- FR-5.4: 개선 권고사항 (Recommendation) 포함

---

### Feature 6: Guardrails & Validation

**설명**
입출력 검증으로 시스템 안정성과 결과 일관성을 보장한다.

| Guardrail | 검증 내용 |
|-----------|-----------|
| **Evidence Validator** | 출처 유효성, 내용 무결성 |
| **Finding Validator** | 판정-증거 일관성, 필수 필드 |
| **Input Validator** | 악성 코드/인젝션 방지 |

**기능 요구사항**
- FR-6.1: 모든 Evidence에 유효한 Provenance 필수
- FR-6.2: FAIL 판정 시 최소 1개 Evidence 필수
- FR-6.3: 민감 정보 입력 차단

---

## 6. Roadmap & Future Vision

### 현재 상태 (v0.1 - MVP)

| 영역 | 구현 완료 |
|------|-----------|
| **Core Engine** | Multi-agent Orchestrator, Inspection Agent, Reader Agents |
| **Data Layer** | Supabase 연동, ComplianceRegistry, ArtifactRegistry |
| **AI/ML** | LLM 판정 (gpt-4o), RAG Citation (gpt-4o-mini), Heuristic Fallback |
| **Quality** | Guardrails, Evidence/Finding Validator, Tracing |
| **UX** | HITL Review, Streamlit UI, FastAPI, CLI |
| **규정** | 알고리즘 공정성 자가평가 |

---

### Phase 1: 규정 커버리지 확장 (v0.2)

**목표**: 알고리즘 공정성 외 다양한 규정 지원

| 규정 | 대상 | 우선순위 |
|------|------|:--------:|
| **개인정보보호법 (PIPA)** | 개인정보 수집/처리/보관 | P0 |
| **전자금융거래법** | 금융 시스템 보안 | P1 |
| **신용정보법** | 신용정보 활용 | P1 |
| **ISO 27001** | 정보보안 관리체계 | P2 |
| **SOC 2 Type II** | 서비스 조직 통제 | P2 |

**주요 작업**
- 규정별 Rule 템플릿 설계
- Supabase에 규정 데이터 적재
- Reader 확장 (DB 스키마, 네트워크 로그 등)
- 규정 간 Cross-reference 지원

---

### Phase 2: CI/CD 통합 (v0.3)

**목표**: 개발 워크플로우에 Continuous Compliance 내재화

```
Developer Workflow with Kompline
─────────────────────────────────────────────────────────────

  Code Push          PR Created           Merge to Main
      │                   │                     │
      ▼                   ▼                     ▼
┌───────────┐      ┌───────────────┐      ┌──────────────┐
│ Pre-commit│      │ GitHub Action │      │ Scheduled    │
│ Hook      │      │ PR Check      │      │ Full Audit   │
│           │      │               │      │              │
│ Quick     │      │ Changed Files │      │ All Artifacts│
│ Scan      │      │ Only          │      │ All Rules    │
└─────┬─────┘      └───────┬───────┘      └──────┬───────┘
      │                    │                     │
      ▼                    ▼                     ▼
 ⚡ 10초 이내         📋 PR Comment         📊 Dashboard
 Pass/Fail            위반 사항 리포트       전체 현황
```

**지원 플랫폼**
| 플랫폼 | 통합 방식 |
|--------|-----------|
| **GitHub Actions** | Official Action (`kompline/action`) |
| **GitLab CI** | Docker Image + `.gitlab-ci.yml` 템플릿 |
| **Jenkins** | Plugin 또는 CLI 호출 |
| **Pre-commit** | Hook 스크립트 제공 |

**주요 작업**
- GitHub Action 개발 및 Marketplace 등록
- Incremental Scan (변경 파일만 검사)
- PR Comment 자동 생성
- Status Check 연동 (Block merge if FAIL)

---

### Phase 3: 대시보드 & 리포팅 고도화 (v0.4)

**목표**: 경영진/감사팀을 위한 컴플라이언스 현황 시각화

```
┌─────────────────────────────────────────────────────────────────┐
│                 Kompline Dashboard                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Compliance   │  │ Risk Score   │  │ Open Issues  │          │
│  │ Rate         │  │              │  │              │          │
│  │    94.2%     │  │    LOW       │  │     7        │          │
│  │   ▲ +2.1%    │  │   (23/100)   │  │   ▼ -3       │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Compliance Trend (Last 30 Days)                            │ │
│  │  100%┤                                          ●──●       │ │
│  │   95%┤              ●──●──●──●──●──●──●──●──●──●           │ │
│  │   90%┤    ●──●──●──●                                       │ │
│  │   85%┤●──●                                                 │ │
│  │      └─────────────────────────────────────────────────    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────┐  ┌─────────────────────────────┐  │
│  │ By Regulation           │  │ Recent Findings             │  │
│  │                         │  │                             │  │
│  │ 알고리즘 공정성 ██████ 96%│  │ ❌ affiliate_bias (PR #142)│  │
│  │ 개인정보보호   █████░ 91%│  │ ❌ missing_disclosure (#138)│  │
│  │ 전자금융거래   ██████ 98%│  │ ⚠️ low_confidence (#136)   │  │
│  └─────────────────────────┘  └─────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**주요 기능**
| 기능 | 설명 |
|------|------|
| **Compliance Score** | 규정별/서비스별 준수율 집계 |
| **Risk Heatmap** | 위험도 기반 우선순위 시각화 |
| **Trend Analysis** | 시계열 준수율 변화 추적 |
| **Alert & Notification** | Slack/Email 알림 연동 |
| **Export** | PDF/Excel 정기 리포트 자동 생성 |
| **Audit Log** | 전체 감사 이력 조회 |

---

### Long-term Vision (v1.0+)

| 방향 | 설명 |
|------|------|
| **규정 변경 자동 반영** | 법령 개정 모니터링 → RAG DB 자동 업데이트 → 재감사 트리거 |
| **Predictive Compliance** | 코드 변경 시 위반 가능성 사전 예측 |
| **Cross-org Benchmarking** | 익명화된 업계 평균 대비 준수율 비교 |
| **Audit-as-a-Service** | 감사법인용 멀티테넌트 SaaS |

---

## 7. Non-Functional Requirements

### 성능 (Performance)

| 지표 | 목표 | 현재 |
|------|------|------|
| **단일 파일 검사** | < 5초 | ~3초 |
| **전체 감사 (10 Rules × 5 Artifacts)** | < 3분 | ~2분 |
| **API 응답 시간 (P95)** | < 10초 | ~8초 |
| **동시 Inspection Agent** | 최대 20개 | 10개 |

**최적화 전략**
- 병렬 Agent 실행 (asyncio)
- Supabase 쿼리 캐싱 (TTL 기반)
- Incremental Scan (변경분만 검사)

---

### 안정성 (Reliability)

| 항목 | 요구사항 |
|------|----------|
| **가용성** | 99.5% uptime (B2B SLA 기준) |
| **에러 복구** | 자동 재시도 3회 + 작업 재분배 |
| **Fallback** | LLM 장애 시 Heuristic 전환 |
| **데이터 무결성** | Evidence/Finding 검증 Guardrail |

**장애 대응 흐름**
```
Agent 실패
    │
    ├─▶ 재시도 (최대 3회, exponential backoff)
    │         │
    │         └─▶ 성공 → 정상 진행
    │
    └─▶ 3회 실패
              │
              ├─▶ 다른 Agent에 재분배
              │
              └─▶ 재분배 실패 → REVIEW 상태로 HITL 큐 등록
```

---

### 보안 (Security)

| 영역 | 요구사항 |
|------|----------|
| **인증** | API Key 기반, OAuth 2.0 (Phase 2) |
| **암호화** | TLS 1.3 (전송), AES-256 (저장) |
| **접근 제어** | Role-based (Admin, Auditor, Developer) |
| **민감정보** | 코드 내 Secret 자동 마스킹 |
| **감사 로그** | 모든 API 호출 및 판정 이력 기록 |

**Guardrails (Safety)**
| Guardrail | 목적 |
|-----------|------|
| Input Validator | 악성 코드/인젝션 차단 |
| Output Validator | 민감정보 노출 방지 |
| Evidence Validator | 출처 위변조 탐지 |
| Finding Validator | 판정 일관성 검증 |

---

### 확장성 (Scalability)

| 시나리오 | 대응 |
|----------|------|
| **규정 증가** | Supabase DB 스키마 확장, 동적 Rule 로딩 |
| **Artifact 증가** | Reader 플러그인 아키텍처 |
| **동시 사용자 증가** | Horizontal scaling (K8s), Queue 기반 작업 분배 |
| **멀티테넌트** | 테넌트별 DB 분리 또는 Row-level Security |

---

### 관측성 (Observability)

| 영역 | 도구/방식 |
|------|-----------|
| **Logging** | 구조화 로그 (JSON), 감사별 trace_id |
| **Tracing** | Per-relation 실행 추적 |
| **Metrics** | 처리량, 지연시간, 에러율 |
| **Alerting** | 임계치 초과 시 Slack/Email 알림 |

**로그 구조 예시**
```json
{
  "timestamp": "2024-01-20T10:30:00Z",
  "trace_id": "audit-20240120-001",
  "level": "INFO",
  "component": "InspectionAgent",
  "event": "finding_created",
  "rule_id": "ALG-001",
  "artifact_id": "deposit-ranking",
  "status": "FAIL",
  "confidence": 0.85,
  "duration_ms": 1230
}
```

---

### 비용 효율성 (Cost Efficiency)

| 항목 | 전략 |
|------|------|
| **LLM 비용** | Heuristic 우선, LLM은 복잡한 케이스만 |
| **캐싱** | 동일 파일 재검사 시 캐시 활용 |
| **Batch 처리** | 유사 검사 요청 묶어서 처리 |

**예상 비용 (월간)**
| 사용량 | OpenAI API | Supabase | 합계 |
|--------|------------|----------|------|
| 소규모 (100회 감사) | ~$10 | Free tier | ~$10 |
| 중규모 (1,000회 감사) | ~$80 | $25 | ~$105 |
| 대규모 (10,000회 감사) | ~$600 | $100 | ~$700 |

---

## 8. Success Metrics & KPIs

### 비즈니스 지표

| 지표 | 정의 | 목표 (6개월) |
|------|------|-------------|
| **감사 시간 절감율** | (기존 소요시간 - Kompline 소요시간) / 기존 소요시간 | ≥ 80% |
| **감사 비용 절감** | 인력 비용 + 외부 감사 비용 감소분 | ≥ 50% |
| **규정 위반 조기 발견율** | 정기 감사 전 발견된 위반 / 전체 위반 | ≥ 70% |
| **Compliance Score 개선** | 도입 전후 평균 준수율 변화 | +10%p |

---

### 제품 지표

| 지표 | 정의 | 목표 |
|------|------|------|
| **자동화율** | 자동 판정 / 전체 판정 (HITL 제외) | ≥ 85% |
| **판정 정확도** | 사람 검토 후 APPROVE / 전체 HITL | ≥ 90% |
| **False Positive율** | 잘못된 FAIL 판정 / 전체 FAIL | ≤ 10% |
| **False Negative율** | 놓친 위반 / 실제 위반 | ≤ 5% |
| **평균 검사 시간** | 1회 전체 감사 소요 시간 | ≤ 3분 |

---

### 기술 지표

| 지표 | 정의 | 목표 |
|------|------|------|
| **시스템 가용성** | Uptime / 전체 시간 | ≥ 99.5% |
| **API 응답 시간 (P95)** | 95번째 백분위 응답 시간 | ≤ 10초 |
| **에러 재시도 성공률** | 재시도 후 성공 / 전체 재시도 | ≥ 80% |
| **LLM Fallback 발생률** | Heuristic 전환 횟수 / 전체 판정 | ≤ 15% |

---

### 사용자 지표

| 지표 | 정의 | 목표 |
|------|------|------|
| **Weekly Active Users** | 주간 활성 사용자 수 | 지속 성장 |
| **감사 실행 빈도** | 조직당 월간 평균 감사 횟수 | ≥ 10회 |
| **HITL 처리 시간** | Review 요청 → 승인까지 평균 시간 | ≤ 24시간 |
| **NPS (순추천지수)** | 추천 의향 점수 | ≥ 40 |

---

### 해커톤 평가 기준 매핑

| 평가 항목 | 배점 | Kompline 대응 | 증빙 |
|-----------|:----:|---------------|------|
| **아이디어 (30%)** | | | |
| └ 시장성 & ROI | 15% | 감사 80% 시간 절감, 실제 금융권 Pain Point | ROI 산출표, 타겟 고객 분석 |
| └ AI 필수성 | 15% | 자연어 규정 해석, 맥락 기반 판정 필요 | LLM vs Heuristic 비교 |
| **기술 구현 (40%)** | | | |
| └ 멀티에이전트 협업 | 15% | Orchestrator → Inspection Agent 병렬 | 아키텍처 다이어그램 |
| └ 에러 처리/재분배 | 10% | 재시도 3회 + Agent 간 작업 재분배 | RetryConfig 코드 |
| └ 도구 사용 (Function Calling) | 10% | Reader Agents, RAG Query | 스키마 검증 로직 |
| └ RAG & Citation | 5% | 출처 명시, 할루시네이션 방지 | Citation 출력 예시 |
| **완성도 (20%)** | | | |
| └ 안정성 | 10% | Guardrails, Fallback, Validation | Edge case 테스트 |
| └ 실용성 (속도/비용) | 10% | 3분 이내 감사, Heuristic 우선 전략 | 벤치마크 결과 |
| **문서화 (10%)** | | | |
| └ README & 아키텍처 | 10% | PRD, 실행 가능한 데모 | 이 문서 |
| **가산점** | | | |
| └ Safety (Guardrails) | +α | Input/Output/Evidence/Finding Validator | 구현 코드 |
| └ Advanced UX (HITL) | +α | Review Queue, Streamlit UI | UI 스크린샷 |
| └ Observability | +α | Structured logging, Tracing | 로그 예시 |

---

### 측정 방법

| 지표 유형 | 데이터 소스 | 수집 주기 |
|-----------|-------------|-----------|
| 비즈니스 | 고객 인터뷰, 도입 전후 비교 | 분기별 |
| 제품 | Audit 결과 DB, HITL 리뷰 로그 | 실시간 |
| 기술 | Application 로그, APM | 실시간 |
| 사용자 | Analytics, 설문조사 | 월간 |

---

## 9. Competitive Analysis & Differentiation

### 경쟁 환경 개요

| 구분 | 플레이어 | 특징 |
|------|----------|------|
| **글로벌 RegTech** | Compliance.ai, Ascent, Kount | 범용 규정, 영미권 중심 |
| **국내 RegTech** | 레그테크코리아, 파운트 | 금융규제 특화, 수작업 컨설팅 병행 |
| **코드 보안 도구** | SonarQube, Snyk, Checkmarx | 보안 취약점 중심, 규정 준수 아님 |
| **AI 코드 분석** | GitHub Copilot, Codex | 코드 생성/리뷰, 컴플라이언스 미지원 |

---

### 경쟁사 비교

| 기능 | Kompline | Compliance.ai | SonarQube | 수작업 감사 |
|------|:--------:|:-------------:|:---------:|:----------:|
| **한국 금융규제 특화** | ● | ○ | ✗ | ● |
| **코드 레벨 검사** | ● | ✗ | ● | △ |
| **멀티에이전트 병렬** | ● | ✗ | ✗ | ✗ |
| **LLM 기반 판정** | ● | ○ | ✗ | ✗ |
| **Citation 출처 명시** | ● | ○ | ✗ | ● |
| **HITL 워크플로우** | ● | ○ | ✗ | ● |
| **CI/CD 통합** | ◐ | ✗ | ● | ✗ |
| **실시간 검사** | ● | ✗ | ● | ✗ |
| **비용** | 低 | 高 | 中 | 高 |

*(●: 완전 지원, ◐: 부분/예정, ○: 제한적, △: 수작업, ✗: 미지원)*

---

### Kompline 차별점

#### 1. 한국 금융규제 네이티브

```
┌─────────────────────────────────────────────────────────────┐
│                    글로벌 RegTech                            │
│                                                              │
│   GDPR, SOX, HIPAA 중심 → 한국 규제 번역/매핑 필요           │
│   영문 기반 → 한국어 규정 해석 한계                           │
└─────────────────────────────────────────────────────────────┘
                           vs
┌─────────────────────────────────────────────────────────────┐
│                      Kompline                                │
│                                                              │
│   알고리즘 공정성 자가평가, 개인정보보호법 등 네이티브 지원    │
│   한국어 규정 원문 기반 RAG → 정확한 Citation                 │
│   금융위/금감원 제출 양식 자동 생성                           │
└─────────────────────────────────────────────────────────────┘
```

#### 2. 코드 ↔ 규정 브릿지

| 기존 도구 | Kompline |
|-----------|----------|
| 코드 분석 OR 규정 관리 (분리) | 코드 분석 AND 규정 판정 (통합) |
| "이 코드에 버그가 있다" | "이 코드가 제3조 제2항을 위반한다" |
| 개발자 → 감사자 수작업 전달 | Evidence 자동 추출 및 링킹 |

#### 3. Continuous Compliance 패러다임

```
기존: 주기적 감사
────────────────────────────────────────────────────
Jan        Apr        Jul        Oct        Jan
 │          │          │          │          │
 ▼          ▼          ▼          ▼          ▼
[감사]     [감사]     [감사]     [감사]     [감사]
 2주        2주        2주        2주        2주

 ↑ 감사 사이 3개월간 위반 리스크 상존


Kompline: Continuous Compliance
────────────────────────────────────────────────────
│●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●●│
 ↑ 매 커밋/PR마다 실시간 검사, 위반 즉시 탐지
```

#### 4. 비용 구조 혁신

| 항목 | 수작업 감사 | Kompline |
|------|------------|----------|
| 감사당 인력 | 2-3명 × 2주 | 자동화 |
| 연간 비용 (분기 감사 기준) | ~1억원 | ~1,000만원 |
| 확장 비용 | 선형 증가 | 거의 고정 |

---

### 포지셔닝 맵

```
                    규정 커버리지
                         ▲
                         │
        Compliance.ai    │
              ●          │
                         │
                         │         Kompline (목표)
                         │              ◐
    ─────────────────────┼─────────────────────────▶ 코드 레벨 분석
        수작업 감사      │              ●
              ●          │          Kompline (현재)
                         │
                         │    SonarQube
                         │        ●
                         │
```

---

### 진입 장벽 (Moat)

| 장벽 | 설명 |
|------|------|
| **규정 데이터** | 한국 금융규제 구조화 데이터 축적 |
| **도메인 지식** | 금융 컴플라이언스 판정 로직 노하우 |
| **고객 피드백 루프** | HITL 데이터로 판정 정확도 지속 개선 |
| **통합 생태계** | CI/CD, 대시보드 등 워크플로우 Lock-in |

---

## 10. Risks & Mitigations

### 기술 리스크

| 리스크 | 영향도 | 발생 가능성 | 완화 전략 |
|--------|:------:|:----------:|-----------|
| **LLM 할루시네이션** | 高 | 中 | RAG Citation 필수화, Confidence 임계치, HITL 검증 |
| **LLM API 장애/지연** | 中 | 中 | Heuristic Fallback, 재시도 로직, 멀티 프로바이더 |
| **대용량 코드 처리 한계** | 中 | 中 | Chunking 전략, Incremental Scan, 캐싱 |
| **규정 해석 모호성** | 高 | 高 | 다중 Citation, Confidence 표시, HITL 필수화 |

---

### 비즈니스 리스크

| 리스크 | 영향도 | 발생 가능성 | 완화 전략 |
|--------|:------:|:----------:|-----------|
| **오판정으로 인한 신뢰 손실** | 高 | 中 | FAIL은 HITL 필수, False Positive 최소화 |
| **규제 변경 대응 지연** | 中 | 高 | 규정 DB 정기 업데이트, 변경 알림 시스템 |
| **경쟁사 진입** | 中 | 高 | 한국 규제 특화, 고객 피드백 루프로 선점 |
| **고객 도입 저항** | 中 | 中 | Pilot 무료 제공, ROI 명확히 증명 |

---

### 법적/규제 리스크

| 리스크 | 영향도 | 발생 가능성 | 완화 전략 |
|--------|:------:|:----------:|-----------|
| **AI 판정 법적 책임** | 高 | 低 | "보조 도구" 명시, 최종 판단은 사람 |
| **고객 코드 데이터 보안** | 高 | 低 | On-premise 옵션, 데이터 미저장 모드 |
| **LLM 학습 데이터 유출** | 中 | 低 | OpenAI API 정책 준수, 민감정보 마스킹 |

---

### 리스크 대응 매트릭스

```
        영향도
          ▲
       高 │  ┌─────────────┐    ┌─────────────┐
          │  │ 오판정 신뢰  │    │ LLM 할루시  │
          │  │ → HITL 필수 │    │ → Citation  │
          │  └─────────────┘    └─────────────┘
          │
       中 │  ┌─────────────┐    ┌─────────────┐
          │  │ 경쟁사 진입  │    │ 규제 변경   │
          │  │ → 선점/특화 │    │ → 자동 반영 │
          │  └─────────────┘    └─────────────┘
          │
       低 │
          │
          └────────────────────────────────────▶
              低            中            高
                      발생 가능성
```

---

### 핵심 완화 장치 (Built-in)

| 장치 | 대응 리스크 | 구현 상태 |
|------|-------------|:---------:|
| **Heuristic Fallback** | LLM 장애 | ✅ |
| **Retry + 재분배** | Agent 실패 | ✅ |
| **RAG Citation** | 할루시네이션 | ✅ |
| **Confidence Score** | 판정 불확실성 | ✅ |
| **HITL Review** | 오판정 | ✅ |
| **Guardrails** | 입출력 오류 | ✅ |
| **Evidence Provenance** | 증거 위변조 | ✅ |
| **Structured Logging** | 디버깅/감사 | ✅ |

---

### Contingency Plan

**시나리오 1: LLM API 전면 장애**
```
1. 자동으로 Heuristic 모드 전환
2. 관리자에게 Slack/Email 알림
3. 복잡한 케이스는 REVIEW 상태로 큐잉
4. API 복구 후 REVIEW 건 재처리
```

**시나리오 2: 심각한 오판정 발견**
```
1. 해당 Rule 즉시 비활성화
2. 영향받은 감사 결과 롤백 표시
3. Root cause 분석 후 Rule 수정
4. 영향받은 고객 개별 통지
```

**시나리오 3: 규정 대폭 개정**
```
1. 규정 변경 감지 (수동 또는 자동)
2. 신규 Rule 버전 생성 (기존 유지)
3. Staging 환경에서 검증
4. 고객별 순차 적용 + 재감사 안내
```

---

## 11. Glossary & Appendix

### 용어 정의

| 용어 | 정의 |
|------|------|
| **Compliance** | 준수해야 할 규정/법령 (예: 알고리즘 공정성 자가평가) |
| **Rule** | Compliance 내 개별 검사 항목 (예: 제3조 제2항) |
| **Artifact** | 검사 대상 산출물 (코드, 설정, 로그, 문서) |
| **Audit Relation** | (Rule, Artifact) 쌍 - 하나의 검사 단위 |
| **Evidence** | 규정 준수/위반을 뒷받침하는 증거 (코드 스니펫, 설정값 등) |
| **Finding** | 검사 결과 (PASS/FAIL/REVIEW) + 판정 근거 |
| **Citation** | Finding의 규정 원문 출처 참조 |
| **Provenance** | Evidence의 출처 추적 정보 (파일, 버전, 시점) |
| **HITL** | Human-in-the-Loop, 사람 검토 워크플로우 |
| **Guardrail** | 입출력 검증 장치 |
| **Continuous Compliance** | 주기적 감사가 아닌 상시 준수 상태 유지 패러다임 |

---

### 약어

| 약어 | 전체 명칭 |
|------|-----------|
| **PIPA** | Personal Information Protection Act (개인정보보호법) |
| **RAG** | Retrieval-Augmented Generation |
| **LLM** | Large Language Model |
| **HITL** | Human-in-the-Loop |
| **CI/CD** | Continuous Integration / Continuous Deployment |
| **TTL** | Time-to-Live (캐시 만료 시간) |
| **CCO** | Chief Compliance Officer (준법감시인) |

---

### 참고 문서

| 문서 | 위치 | 설명 |
|------|------|------|
| 아키텍처 상세 | `docs/IMPLEMENTATION_PLAN.md` | 기술 구현 상세 |
| API 명세 | `api/main.py` | FastAPI 엔드포인트 |
| 샘플 규정 | `samples/compliances/` | YAML 형식 규정 예시 |
| 데모 코드 | `demo.py` | 실행 가능한 데모 |

---

### 변경 이력

| 버전 | 일자 | 작성자 | 변경 내용 |
|------|------|--------|-----------|
| 0.1 | 2025-01-20 | - | 초안 작성 |

---

## Quick Reference

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│   Kompline = K-Compliance + Pipeline                                │
│   "주기적 감사에서 Continuous Compliance로"                          │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   🎯 Problem                                                         │
│   규제 산업의 감사는 감사자/피감사자 모두에게 부담이며,              │
│   감사 기간 사이 규정 위반 리스크가 상존                              │
│                                                                      │
│   💡 Solution                                                        │
│   코드·로그·데이터를 수시 분석하는 멀티에이전트 시스템으로           │
│   감사자 → 자동 점검, 피감사자 → 증빙 생성, 실무자 → 사전 검토       │
│                                                                      │
│   📊 Impact                                                          │
│   감사 시간 2-3주 → 2-3분 (80% 절감)                                 │
│   다중 규정 병렬 검사, 규제당국 제출용 리포트 자동 생성               │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   🏗️ Architecture                                                    │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐            │
│   │ Supabase DB │───▶│ Orchestrator│───▶│ Inspection  │            │
│   │ (Rules)     │    │ (병렬 조율)  │    │ Agents      │            │
│   └─────────────┘    └─────────────┘    └──────┬──────┘            │
│                                                 │                    │
│                              ┌─────────────────┬┴────────────────┐  │
│                              ▼                 ▼                 ▼  │
│                         ┌────────┐       ┌─────────┐      ┌──────┐ │
│                         │OpenAI  │       │   RAG   │      │ HITL │ │
│                         │gpt-4o  │       │Citation │      │Review│ │
│                         └────────┘       └─────────┘      └──────┘ │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   🎯 Target Customers                                                │
│   1. 금융사 (은행, 증권, 보험) - 내부 컴플라이언스팀                  │
│   2. 핀테크/플랫폼 - 예금·대출 비교 서비스                           │
│   3. 감사법인/컨설팅 - 외부 감사 업무 효율화                         │
│                                                                      │
│   🗺️ Roadmap                                                         │
│   v0.2 규정 확장 (PIPA, ISO 27001, SOC2)                            │
│   v0.3 CI/CD 통합 (GitHub Actions, Pre-commit)                      │
│   v0.4 대시보드 고도화 (경영진용 현황 시각화)                        │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   ✅ 해커톤 평가 기준 충족                                            │
│                                                                      │
│   아이디어 (30%)  │ 실제 B2B Pain Point, AI 필수 문제               │
│   기술 (40%)      │ 멀티에이전트, 에러 재분배, RAG Citation          │
│   완성도 (20%)    │ Guardrails, Fallback, 3분 이내 감사             │
│   문서화 (10%)    │ PRD, README, 실행 가능한 데모                    │
│   가산점          │ Safety, HITL, Observability                      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```
