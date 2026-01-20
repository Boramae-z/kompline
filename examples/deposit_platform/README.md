# 예금상품 전시 플랫폼 예제

금융상품 비교·추천 플랫폼의 예제 구현입니다. Kompline을 사용하여 알고리즘 공정성을 검증할 수 있습니다.

## 구조

```
deposit_platform/
├── __init__.py      # 패키지 초기화 및 공개 API
├── models.py        # 데이터 모델 (Bank, DepositProduct, ProductRanking)
├── data.py          # 샘플 예금상품 데이터
├── config.py        # 정렬 알고리즘 설정 및 가중치
├── ranking.py       # 예금상품 정렬 알고리즘 (감사 대상)
├── api.py           # FastAPI REST API
└── README.md
```

## 빠른 시작

### Python에서 사용

```python
from examples.deposit_platform import (
    get_active_products,
    rank_products,
    get_top_products,
    DEFAULT_CONFIG,
)

# 모든 활성 상품 조회
products = get_active_products()

# 상품 정렬
rankings = rank_products(products)

# 상위 5개 출력
for r in rankings[:5]:
    print(f"{r.rank}. {r.product.name}")
    print(f"   은행: {r.product.bank_code}")
    print(f"   금리: {r.product.rate_display}")
    print(f"   점수: {r.score:.4f}")
    print(f"   점수 상세: {r.score_breakdown}")
```

### API 서버 실행

```bash
# 프로젝트 루트에서
cd examples/deposit_platform
uvicorn api:app --reload --port 8000
```

API 문서: http://localhost:8000/docs

### 주요 API 엔드포인트

| 엔드포인트 | 설명 |
|-----------|------|
| `GET /products` | 예금상품 목록 조회 |
| `GET /products/{id}` | 상품 상세 조회 |
| `GET /ranking` | 상품 순위 조회 |
| `GET /ranking/top` | 상위 N개 상품 |
| `GET /config` | 현재 정렬 설정 조회 |
| `GET /banks` | 금융기관 목록 |

## 정렬 알고리즘

### 가중치 설정 (`config.py`)

```python
RankingWeights:
  max_rate: 0.50      # 최고금리 (가장 중요)
  base_rate: 0.20     # 기본금리
  accessibility: 0.15  # 접근성 (최소금액, 가입방법)
  flexibility: 0.10   # 기간 유연성
  benefits: 0.05      # 우대조건 수
```

### 점수 계산 공식

```
총점 = Σ(요소별 점수 × 가중치) + 계열사 부스트
```

각 요소는 0~1로 정규화된 후 가중치가 적용됩니다.

## Kompline으로 감사하기

### 감사 대상 파일

- `ranking.py` - 정렬 알고리즘
- `config.py` - 가중치 설정

### 감사 실행

```python
from kompline.registry import get_artifact_registry, get_compliance_registry
from kompline.agents.audit_orchestrator import AuditOrchestrator
from kompline.models import Artifact, ArtifactType, AccessMethod, Provenance, RunConfig

# 아티팩트 등록
artifact = Artifact(
    id="deposit-ranking",
    name="예금상품 정렬 알고리즘",
    type=ArtifactType.CODE,
    locator="examples/deposit_platform/ranking.py",
    access_method=AccessMethod.FILE_READ,
    provenance=Provenance(source="examples/deposit_platform/"),
)
get_artifact_registry().register_or_update(artifact)

# 감사 실행
orchestrator = AuditOrchestrator()
result = await orchestrator.audit(
    compliance_ids=["byeolji5-fairness"],
    artifact_ids=["deposit-ranking"],
    run_config=RunConfig(use_llm=True),
)

print(f"적합 여부: {result.is_compliant}")
```

### 예상 감사 결과

| 규칙 ID | 제목 | 기대 결과 |
|--------|------|----------|
| ALG-001 | 정렬 기준 투명성 | PASS - 가중치 문서화됨 |
| ALG-002 | 계열사 편향 금지 | PASS/FAIL - config에 따라 |
| ALG-003 | 무작위화 공개 | PASS - 시드 설정됨 |
| ALG-004 | 가중치 문서화 | PASS - 명시적 정의 |

### 계열사 편향 테스트

```python
from examples.deposit_platform import BIASED_CONFIG, rank_products, get_active_products

# 계열사 우대가 적용된 설정으로 정렬
products = get_active_products()
rankings = rank_products(products, config=BIASED_CONFIG)

# 카카오뱅크(계열사)가 부당하게 높은 순위로 올라감
```

## 커스터마이징

### 새 상품 추가

`data.py`의 `PRODUCTS` 리스트에 추가:

```python
DepositProduct(
    id="NEW-001",
    bank_code="KB",
    name="새 예금상품",
    product_type=ProductType.SAVINGS,
    base_rate=3.50,
    max_rate=3.80,
    interest_type=InterestType.SIMPLE,
    min_amount=1_000_000,
    max_amount=None,
    min_term_months=6,
    max_term_months=24,
    preferential_conditions=["조건1", "조건2"],
    join_method=["app", "online"],
    target_customers=["개인"],
)
```

### 가중치 변경

```python
from examples.deposit_platform import RankingConfig, RankingWeights

custom_config = RankingConfig(
    weights=RankingWeights(
        max_rate=0.60,  # 금리 중시
        base_rate=0.15,
        accessibility=0.10,
        flexibility=0.10,
        benefits=0.05,
    )
)
```

## 라이선스

MIT
