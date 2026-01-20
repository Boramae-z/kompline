"""예금상품 데이터 모델."""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class BankType(str, Enum):
    """은행 유형."""

    COMMERCIAL = "commercial"  # 시중은행
    REGIONAL = "regional"  # 지방은행
    INTERNET = "internet"  # 인터넷전문은행
    SPECIALIZED = "specialized"  # 특수은행


class ProductType(str, Enum):
    """예금상품 유형."""

    SAVINGS = "savings"  # 정기예금
    INSTALLMENT = "installment"  # 정기적금
    FREE_SAVINGS = "free_savings"  # 자유적금
    MMDA = "mmda"  # MMDA


class InterestType(str, Enum):
    """이자 지급 방식."""

    SIMPLE = "simple"  # 단리
    COMPOUND = "compound"  # 복리
    MONTHLY = "monthly"  # 월복리


@dataclass
class Bank:
    """금융기관 정보."""

    code: str  # 은행 코드
    name: str  # 은행명
    type: BankType
    is_affiliate: bool = False  # 계열사 여부
    logo_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DepositProduct:
    """예금상품 정보."""

    id: str
    bank_code: str
    name: str
    product_type: ProductType

    # 금리 정보
    base_rate: float  # 기본금리 (%)
    max_rate: float  # 최고금리 (%)
    interest_type: InterestType

    # 가입 조건
    min_amount: int  # 최소 가입금액 (원)
    max_amount: int | None  # 최대 가입금액 (원), None=무제한
    min_term_months: int  # 최소 가입기간 (개월)
    max_term_months: int  # 최대 가입기간 (개월)

    # 우대 조건
    preferential_conditions: list[str] = field(default_factory=list)

    # 기타 정보
    join_method: list[str] = field(default_factory=list)  # 가입방법: ["online", "branch", "app"]
    target_customers: list[str] = field(default_factory=list)  # 가입대상
    special_notes: str | None = None

    # 메타데이터
    created_at: date = field(default_factory=date.today)
    updated_at: date = field(default_factory=date.today)
    is_active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def rate_display(self) -> str:
        """금리 표시 문자열."""
        if self.base_rate == self.max_rate:
            return f"{self.base_rate:.2f}%"
        return f"{self.base_rate:.2f}% ~ {self.max_rate:.2f}%"

    @property
    def amount_display(self) -> str:
        """가입금액 표시 문자열."""
        min_str = f"{self.min_amount:,}원"
        if self.max_amount:
            return f"{min_str} ~ {self.max_amount:,}원"
        return f"{min_str} 이상"

    @property
    def term_display(self) -> str:
        """가입기간 표시 문자열."""
        if self.min_term_months == self.max_term_months:
            return f"{self.min_term_months}개월"
        return f"{self.min_term_months}~{self.max_term_months}개월"


@dataclass
class ProductRanking:
    """상품 순위 정보."""

    product: DepositProduct
    rank: int
    score: float
    score_breakdown: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환."""
        return {
            "rank": self.rank,
            "product_id": self.product.id,
            "product_name": self.product.name,
            "bank_code": self.product.bank_code,
            "rate": self.product.rate_display,
            "max_rate": self.product.max_rate,
            "score": round(self.score, 4),
            "score_breakdown": {k: round(v, 4) for k, v in self.score_breakdown.items()},
        }
