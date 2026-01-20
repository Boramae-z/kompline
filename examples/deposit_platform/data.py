"""샘플 예금상품 데이터."""

from .models import (
    Bank,
    BankType,
    DepositProduct,
    InterestType,
    ProductType,
)


# 금융기관 데이터
BANKS: dict[str, Bank] = {
    "KB": Bank(
        code="KB",
        name="KB국민은행",
        type=BankType.COMMERCIAL,
        is_affiliate=False,
    ),
    "SHINHAN": Bank(
        code="SHINHAN",
        name="신한은행",
        type=BankType.COMMERCIAL,
        is_affiliate=False,
    ),
    "WOORI": Bank(
        code="WOORI",
        name="우리은행",
        type=BankType.COMMERCIAL,
        is_affiliate=False,
    ),
    "HANA": Bank(
        code="HANA",
        name="하나은행",
        type=BankType.COMMERCIAL,
        is_affiliate=False,
    ),
    "NH": Bank(
        code="NH",
        name="NH농협은행",
        type=BankType.SPECIALIZED,
        is_affiliate=False,
    ),
    "KAKAO": Bank(
        code="KAKAO",
        name="카카오뱅크",
        type=BankType.INTERNET,
        is_affiliate=True,  # 플랫폼 계열사 예시
    ),
    "TOSS": Bank(
        code="TOSS",
        name="토스뱅크",
        type=BankType.INTERNET,
        is_affiliate=False,
    ),
    "KBANK": Bank(
        code="KBANK",
        name="케이뱅크",
        type=BankType.INTERNET,
        is_affiliate=False,
    ),
    "DGB": Bank(
        code="DGB",
        name="DGB대구은행",
        type=BankType.REGIONAL,
        is_affiliate=False,
    ),
    "BNK": Bank(
        code="BNK",
        name="BNK부산은행",
        type=BankType.REGIONAL,
        is_affiliate=False,
    ),
}


# 예금상품 데이터
PRODUCTS: list[DepositProduct] = [
    # KB국민은행
    DepositProduct(
        id="KB-001",
        bank_code="KB",
        name="KB Star 정기예금",
        product_type=ProductType.SAVINGS,
        base_rate=3.40,
        max_rate=3.60,
        interest_type=InterestType.SIMPLE,
        min_amount=1_000_000,
        max_amount=None,
        min_term_months=6,
        max_term_months=36,
        preferential_conditions=["급여이체 시 +0.1%", "KB카드 이용 시 +0.1%"],
        join_method=["online", "branch", "app"],
        target_customers=["개인"],
    ),
    DepositProduct(
        id="KB-002",
        bank_code="KB",
        name="KB 직장인 우대 정기예금",
        product_type=ProductType.SAVINGS,
        base_rate=3.50,
        max_rate=3.80,
        interest_type=InterestType.SIMPLE,
        min_amount=100_000,
        max_amount=50_000_000,
        min_term_months=12,
        max_term_months=24,
        preferential_conditions=["급여이체 필수", "재직증명 제출 시 +0.2%"],
        join_method=["online", "branch"],
        target_customers=["직장인"],
    ),

    # 신한은행
    DepositProduct(
        id="SHINHAN-001",
        bank_code="SHINHAN",
        name="쏠편한 정기예금",
        product_type=ProductType.SAVINGS,
        base_rate=3.45,
        max_rate=3.65,
        interest_type=InterestType.SIMPLE,
        min_amount=1_000_000,
        max_amount=None,
        min_term_months=6,
        max_term_months=36,
        preferential_conditions=["SOL 앱 가입 시 +0.1%", "자동이체 등록 시 +0.1%"],
        join_method=["online", "app"],
        target_customers=["개인"],
    ),

    # 우리은행
    DepositProduct(
        id="WOORI-001",
        bank_code="WOORI",
        name="WON플러스 예금",
        product_type=ProductType.SAVINGS,
        base_rate=3.35,
        max_rate=3.55,
        interest_type=InterestType.SIMPLE,
        min_amount=500_000,
        max_amount=100_000_000,
        min_term_months=3,
        max_term_months=36,
        preferential_conditions=["우리카드 이용 시 +0.1%"],
        join_method=["online", "branch", "app"],
        target_customers=["개인", "개인사업자"],
    ),

    # 하나은행
    DepositProduct(
        id="HANA-001",
        bank_code="HANA",
        name="하나 더블업 정기예금",
        product_type=ProductType.SAVINGS,
        base_rate=3.50,
        max_rate=3.70,
        interest_type=InterestType.SIMPLE,
        min_amount=1_000_000,
        max_amount=None,
        min_term_months=6,
        max_term_months=24,
        preferential_conditions=["하나머니 적립 시 +0.1%", "하나카드 이용 시 +0.1%"],
        join_method=["online", "branch", "app"],
        target_customers=["개인"],
    ),

    # NH농협
    DepositProduct(
        id="NH-001",
        bank_code="NH",
        name="NH올원e예금",
        product_type=ProductType.SAVINGS,
        base_rate=3.55,
        max_rate=3.75,
        interest_type=InterestType.SIMPLE,
        min_amount=100_000,
        max_amount=None,
        min_term_months=6,
        max_term_months=36,
        preferential_conditions=["비대면 가입 시 +0.1%", "NH카드 이용 시 +0.1%"],
        join_method=["online", "app"],
        target_customers=["개인"],
    ),

    # 카카오뱅크 (계열사)
    DepositProduct(
        id="KAKAO-001",
        bank_code="KAKAO",
        name="카카오뱅크 정기예금",
        product_type=ProductType.SAVINGS,
        base_rate=3.50,
        max_rate=3.50,
        interest_type=InterestType.SIMPLE,
        min_amount=100,
        max_amount=None,
        min_term_months=1,
        max_term_months=36,
        preferential_conditions=[],
        join_method=["app"],
        target_customers=["개인"],
        special_notes="중도해지 이자율 우대",
    ),
    DepositProduct(
        id="KAKAO-002",
        bank_code="KAKAO",
        name="카카오뱅크 자유적금",
        product_type=ProductType.FREE_SAVINGS,
        base_rate=3.00,
        max_rate=3.50,
        interest_type=InterestType.COMPOUND,
        min_amount=1_000,
        max_amount=300_000,
        min_term_months=6,
        max_term_months=24,
        preferential_conditions=["매일 저축 시 +0.5%"],
        join_method=["app"],
        target_customers=["개인"],
    ),

    # 토스뱅크
    DepositProduct(
        id="TOSS-001",
        bank_code="TOSS",
        name="토스뱅크 정기예금",
        product_type=ProductType.SAVINGS,
        base_rate=3.60,
        max_rate=3.60,
        interest_type=InterestType.SIMPLE,
        min_amount=100,
        max_amount=None,
        min_term_months=3,
        max_term_months=12,
        preferential_conditions=[],
        join_method=["app"],
        target_customers=["개인"],
    ),

    # 케이뱅크
    DepositProduct(
        id="KBANK-001",
        bank_code="KBANK",
        name="케이뱅크 플러스 정기예금",
        product_type=ProductType.SAVINGS,
        base_rate=3.55,
        max_rate=3.75,
        interest_type=InterestType.SIMPLE,
        min_amount=100,
        max_amount=500_000_000,
        min_term_months=6,
        max_term_months=36,
        preferential_conditions=["주거래 우대 +0.2%"],
        join_method=["app"],
        target_customers=["개인"],
    ),

    # DGB대구은행
    DepositProduct(
        id="DGB-001",
        bank_code="DGB",
        name="DGB주거래 정기예금",
        product_type=ProductType.SAVINGS,
        base_rate=3.60,
        max_rate=3.90,
        interest_type=InterestType.SIMPLE,
        min_amount=1_000_000,
        max_amount=100_000_000,
        min_term_months=12,
        max_term_months=36,
        preferential_conditions=["대구 거주 +0.1%", "급여이체 +0.2%"],
        join_method=["online", "branch"],
        target_customers=["개인", "개인사업자"],
    ),

    # BNK부산은행
    DepositProduct(
        id="BNK-001",
        bank_code="BNK",
        name="BNK더조은정기예금",
        product_type=ProductType.SAVINGS,
        base_rate=3.55,
        max_rate=3.85,
        interest_type=InterestType.SIMPLE,
        min_amount=500_000,
        max_amount=None,
        min_term_months=6,
        max_term_months=36,
        preferential_conditions=["부산/경남 거주 +0.1%", "급여이체 +0.2%"],
        join_method=["online", "branch", "app"],
        target_customers=["개인"],
    ),
]


def get_bank(code: str) -> Bank | None:
    """은행 코드로 은행 정보 조회."""
    return BANKS.get(code)


def get_product(product_id: str) -> DepositProduct | None:
    """상품 ID로 상품 정보 조회."""
    for product in PRODUCTS:
        if product.id == product_id:
            return product
    return None


def get_products_by_bank(bank_code: str) -> list[DepositProduct]:
    """은행별 상품 목록 조회."""
    return [p for p in PRODUCTS if p.bank_code == bank_code]


def get_active_products() -> list[DepositProduct]:
    """활성 상품 목록 조회."""
    return [p for p in PRODUCTS if p.is_active]
