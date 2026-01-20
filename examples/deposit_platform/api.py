"""예금상품 전시 API.

FastAPI 기반의 예금상품 조회 및 비교 API입니다.
"""

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import DEFAULT_CONFIG, BIASED_CONFIG, RankingConfig, RankingWeights
from .data import BANKS, PRODUCTS, get_active_products, get_bank, get_product
from .models import BankType, ProductType
from .ranking import DepositRanker, get_top_products, rank_products

app = FastAPI(
    title="예금상품 비교 플랫폼",
    description="예금상품 조회 및 비교를 위한 API",
    version="1.0.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Response Models ===


class BankResponse(BaseModel):
    """은행 정보 응답."""

    code: str
    name: str
    type: str
    is_affiliate: bool


class ProductResponse(BaseModel):
    """상품 정보 응답."""

    id: str
    bank_code: str
    bank_name: str
    name: str
    product_type: str
    base_rate: float
    max_rate: float
    rate_display: str
    min_amount: int
    max_amount: int | None
    amount_display: str
    term_display: str
    preferential_conditions: list[str]
    join_method: list[str]


class RankingResponse(BaseModel):
    """순위 정보 응답."""

    rank: int
    product_id: str
    product_name: str
    bank_code: str
    bank_name: str
    max_rate: float
    rate_display: str
    score: float
    score_breakdown: dict[str, float]


class ConfigResponse(BaseModel):
    """설정 정보 응답."""

    weights: dict[str, float]
    affiliate_boost: float
    enable_randomization: bool
    random_seed: int | None


# === API Endpoints ===


@app.get("/")
def root():
    """API 상태 확인."""
    return {
        "status": "ok",
        "message": "예금상품 비교 플랫폼 API",
        "version": "1.0.0",
    }


@app.get("/banks", response_model=list[BankResponse])
def list_banks():
    """금융기관 목록 조회."""
    return [
        BankResponse(
            code=bank.code,
            name=bank.name,
            type=bank.type.value,
            is_affiliate=bank.is_affiliate,
        )
        for bank in BANKS.values()
    ]


@app.get("/banks/{bank_code}", response_model=BankResponse)
def get_bank_detail(bank_code: str):
    """금융기관 상세 조회."""
    bank = get_bank(bank_code)
    if not bank:
        return {"error": "Bank not found"}
    return BankResponse(
        code=bank.code,
        name=bank.name,
        type=bank.type.value,
        is_affiliate=bank.is_affiliate,
    )


@app.get("/products", response_model=list[ProductResponse])
def list_products(
    bank_code: str | None = Query(None, description="은행 코드 필터"),
    product_type: str | None = Query(None, description="상품 유형 필터"),
    min_rate: float | None = Query(None, description="최소 금리 필터"),
):
    """예금상품 목록 조회."""
    products = get_active_products()

    # 필터링
    if bank_code:
        products = [p for p in products if p.bank_code == bank_code]
    if product_type:
        products = [p for p in products if p.product_type.value == product_type]
    if min_rate:
        products = [p for p in products if p.max_rate >= min_rate]

    return [_product_to_response(p) for p in products]


@app.get("/products/{product_id}", response_model=ProductResponse)
def get_product_detail(product_id: str):
    """예금상품 상세 조회."""
    product = get_product(product_id)
    if not product:
        return {"error": "Product not found"}
    return _product_to_response(product)


@app.get("/ranking", response_model=list[RankingResponse])
def get_ranking(
    limit: int = Query(10, ge=1, le=50, description="조회할 상품 수"),
    sort_by: str = Query("score", description="정렬 기준: score, max_rate, base_rate"),
    bank_type: str | None = Query(None, description="은행 유형 필터"),
    product_type: str | None = Query(None, description="상품 유형 필터"),
    use_biased: bool = Query(False, description="계열사 우대 적용 (테스트용)"),
):
    """예금상품 순위 조회.

    정렬 알고리즘에 따라 상품을 순위화하여 반환합니다.
    """
    products = get_active_products()

    # 필터링
    if bank_type:
        products = [
            p for p in products if get_bank(p.bank_code).type.value == bank_type
        ]
    if product_type:
        products = [p for p in products if p.product_type.value == product_type]

    # 설정 선택
    config = BIASED_CONFIG if use_biased else DEFAULT_CONFIG

    # 정렬
    ranker = DepositRanker(config)
    rankings = ranker.rank(products, sort_key=sort_by)[:limit]

    return [_ranking_to_response(r) for r in rankings]


@app.get("/ranking/top", response_model=list[RankingResponse])
def get_top_ranking(
    n: int = Query(5, ge=1, le=20, description="상위 N개"),
):
    """상위 N개 상품 조회."""
    products = get_active_products()
    rankings = get_top_products(products, n=n)
    return [_ranking_to_response(r) for r in rankings]


@app.get("/config", response_model=ConfigResponse)
def get_current_config():
    """현재 정렬 설정 조회.

    알고리즘 투명성을 위해 현재 적용 중인 설정을 공개합니다.
    """
    config = DEFAULT_CONFIG
    return ConfigResponse(
        weights=config.weights.to_dict(),
        affiliate_boost=config.affiliate_boost,
        enable_randomization=config.enable_randomization,
        random_seed=config.random_seed,
    )


@app.get("/config/validate")
def validate_config():
    """설정 유효성 검증.

    현재 설정의 공정성 문제를 검사합니다.
    """
    warnings = DEFAULT_CONFIG.validate()
    return {
        "valid": len(warnings) == 0,
        "warnings": warnings,
    }


# === Helper Functions ===


def _product_to_response(product) -> ProductResponse:
    """상품을 응답 모델로 변환."""
    bank = get_bank(product.bank_code)
    return ProductResponse(
        id=product.id,
        bank_code=product.bank_code,
        bank_name=bank.name if bank else product.bank_code,
        name=product.name,
        product_type=product.product_type.value,
        base_rate=product.base_rate,
        max_rate=product.max_rate,
        rate_display=product.rate_display,
        min_amount=product.min_amount,
        max_amount=product.max_amount,
        amount_display=product.amount_display,
        term_display=product.term_display,
        preferential_conditions=product.preferential_conditions,
        join_method=product.join_method,
    )


def _ranking_to_response(ranking) -> RankingResponse:
    """랭킹을 응답 모델로 변환."""
    bank = get_bank(ranking.product.bank_code)
    return RankingResponse(
        rank=ranking.rank,
        product_id=ranking.product.id,
        product_name=ranking.product.name,
        bank_code=ranking.product.bank_code,
        bank_name=bank.name if bank else ranking.product.bank_code,
        max_rate=ranking.product.max_rate,
        rate_display=ranking.product.rate_display,
        score=round(ranking.score, 4),
        score_breakdown={k: round(v, 4) for k, v in ranking.score_breakdown.items()},
    )


# === Run Server ===

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
