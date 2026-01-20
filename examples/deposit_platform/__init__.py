"""예금상품 전시 플랫폼 예제.

이 패키지는 예금상품 비교/추천 플랫폼의 예제 구현입니다.
Kompline을 사용하여 알고리즘 공정성을 검증할 수 있습니다.

주요 모듈:
- models: 예금상품 데이터 모델
- data: 샘플 예금상품 데이터
- config: 정렬 알고리즘 설정 및 가중치
- ranking: 예금상품 정렬 알고리즘
- api: FastAPI 기반 REST API

사용 예시:
    >>> from examples.deposit_platform import rank_products, get_active_products
    >>> products = get_active_products()
    >>> rankings = rank_products(products)
    >>> for r in rankings[:5]:
    ...     print(f"{r.rank}. {r.product.name} ({r.score:.4f})")
"""

from .config import DEFAULT_CONFIG, BIASED_CONFIG, RankingConfig, RankingWeights
from .data import (
    BANKS,
    PRODUCTS,
    get_active_products,
    get_bank,
    get_product,
    get_products_by_bank,
)
from .models import (
    Bank,
    BankType,
    DepositProduct,
    InterestType,
    ProductRanking,
    ProductType,
)
from .ranking import DepositRanker, get_top_products, rank_products

__all__ = [
    # Config
    "DEFAULT_CONFIG",
    "BIASED_CONFIG",
    "RankingConfig",
    "RankingWeights",
    # Data
    "BANKS",
    "PRODUCTS",
    "get_active_products",
    "get_bank",
    "get_product",
    "get_products_by_bank",
    # Models
    "Bank",
    "BankType",
    "DepositProduct",
    "InterestType",
    "ProductRanking",
    "ProductType",
    # Ranking
    "DepositRanker",
    "get_top_products",
    "rank_products",
]
