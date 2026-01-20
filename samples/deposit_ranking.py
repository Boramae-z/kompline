"""Sample deposit ranking algorithm for compliance testing.

This sample demonstrates various patterns that should be checked
for algorithm fairness compliance (별지5 자가평가서).
"""

from dataclasses import dataclass
from typing import Callable


@dataclass
class DepositProduct:
    """A deposit product from a financial institution."""

    id: str
    name: str
    bank_name: str
    interest_rate: float  # Annual interest rate (%)
    min_amount: int  # Minimum deposit amount (KRW)
    max_amount: int  # Maximum deposit amount (KRW)
    term_months: int  # Deposit term in months
    is_special_rate: bool  # Whether this is a promotional rate
    is_affiliated: bool  # Whether bank is affiliated with platform


# Weight factors for ranking (documented for compliance)
RANKING_WEIGHTS = {
    "interest_rate": 0.5,  # 50% weight on interest rate
    "accessibility": 0.2,  # 20% weight on min/max amount accessibility
    "term_flexibility": 0.15,  # 15% weight on term options
    "stability": 0.15,  # 15% weight on bank stability rating
}


def calculate_accessibility_score(product: DepositProduct) -> float:
    """Calculate accessibility score based on deposit amount requirements.

    Lower minimum and higher maximum = more accessible.

    Args:
        product: The deposit product to score.

    Returns:
        Accessibility score between 0 and 1.
    """
    # Lower min_amount is better (normalized to 0-1)
    min_score = max(0, 1 - (product.min_amount / 10_000_000))

    # Higher max_amount is better (normalized to 0-1)
    max_score = min(1, product.max_amount / 1_000_000_000)

    return (min_score + max_score) / 2


def calculate_term_flexibility_score(product: DepositProduct) -> float:
    """Calculate term flexibility score.

    Shorter minimum terms are considered more flexible.

    Args:
        product: The deposit product to score.

    Returns:
        Term flexibility score between 0 and 1.
    """
    # 12 months or less = full score, decreasing for longer terms
    if product.term_months <= 12:
        return 1.0
    elif product.term_months <= 24:
        return 0.8
    elif product.term_months <= 36:
        return 0.6
    else:
        return 0.4


def calculate_ranking_score(
    product: DepositProduct,
    stability_ratings: dict[str, float] | None = None,
) -> float:
    """Calculate the overall ranking score for a product.

    All factors and weights are documented for regulatory compliance.

    Args:
        product: The deposit product to score.
        stability_ratings: Optional dict of bank stability ratings (0-1).

    Returns:
        Overall ranking score.
    """
    stability_ratings = stability_ratings or {}

    # Normalize interest rate to 0-1 scale (assuming max rate of 10%)
    interest_score = min(1.0, product.interest_rate / 10.0)

    # Get component scores
    accessibility_score = calculate_accessibility_score(product)
    term_score = calculate_term_flexibility_score(product)
    stability_score = stability_ratings.get(product.bank_name, 0.5)

    # Calculate weighted score
    total_score = (
        RANKING_WEIGHTS["interest_rate"] * interest_score
        + RANKING_WEIGHTS["accessibility"] * accessibility_score
        + RANKING_WEIGHTS["term_flexibility"] * term_score
        + RANKING_WEIGHTS["stability"] * stability_score
    )

    return total_score


def rank_deposits(
    products: list[DepositProduct],
    stability_ratings: dict[str, float] | None = None,
) -> list[tuple[DepositProduct, float]]:
    """Rank deposit products by compliance-transparent criteria.

    Ranking criteria:
    1. Interest rate (50% weight)
    2. Accessibility - min/max amounts (20% weight)
    3. Term flexibility (15% weight)
    4. Bank stability rating (15% weight)

    NO consideration given to:
    - Affiliate status
    - Sponsorship
    - Commission rates

    Args:
        products: List of deposit products to rank.
        stability_ratings: Optional bank stability ratings.

    Returns:
        List of (product, score) tuples sorted by score descending.
    """
    scored = [
        (product, calculate_ranking_score(product, stability_ratings))
        for product in products
    ]

    # Sort by score descending
    scored.sort(key=lambda x: x[1], reverse=True)

    return scored


# ============================================================
# SAMPLE WITH COMPLIANCE ISSUES (for testing detection)
# ============================================================


def rank_deposits_with_bias(
    products: list[DepositProduct],
    preferred_banks: list[str] | None = None,
) -> list[tuple[DepositProduct, float]]:
    """WARNING: This function contains compliance issues for testing.

    Issues:
    1. Undocumented preference for affiliated products
    2. Undocumented 'preferred_banks' boost
    """
    preferred_banks = preferred_banks or []

    scored = []
    for product in products:
        base_score = calculate_ranking_score(product)

        # ISSUE: Undocumented affiliate boost
        if product.is_affiliated:
            base_score *= 1.2  # 20% boost for affiliates

        # ISSUE: Undocumented preferred bank boost
        if product.bank_name in preferred_banks:
            base_score *= 1.1  # 10% boost for preferred banks

        scored.append((product, base_score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def rank_deposits_random(products: list[DepositProduct]) -> list[DepositProduct]:
    """WARNING: Uses randomization without disclosure.

    Issue: Random shuffling affects results without user knowledge.
    """
    import random

    # ISSUE: Undocumented randomization
    random.shuffle(products)
    return products


# ============================================================
# DEMO DATA
# ============================================================


def get_sample_products() -> list[DepositProduct]:
    """Get sample deposit products for testing."""
    return [
        DepositProduct(
            id="DEP001",
            name="정기예금 스페셜",
            bank_name="국민은행",
            interest_rate=4.5,
            min_amount=1_000_000,
            max_amount=100_000_000,
            term_months=12,
            is_special_rate=True,
            is_affiliated=False,
        ),
        DepositProduct(
            id="DEP002",
            name="자유적금",
            bank_name="신한은행",
            interest_rate=4.2,
            min_amount=100_000,
            max_amount=50_000_000,
            term_months=6,
            is_special_rate=False,
            is_affiliated=True,
        ),
        DepositProduct(
            id="DEP003",
            name="청년희망예금",
            bank_name="우리은행",
            interest_rate=5.0,
            min_amount=10_000,
            max_amount=10_000_000,
            term_months=24,
            is_special_rate=True,
            is_affiliated=False,
        ),
        DepositProduct(
            id="DEP004",
            name="VIP 정기예금",
            bank_name="하나은행",
            interest_rate=4.8,
            min_amount=50_000_000,
            max_amount=1_000_000_000,
            term_months=12,
            is_special_rate=False,
            is_affiliated=True,
        ),
    ]


if __name__ == "__main__":
    # Demo the ranking
    products = get_sample_products()
    stability = {
        "국민은행": 0.95,
        "신한은행": 0.90,
        "우리은행": 0.88,
        "하나은행": 0.92,
    }

    print("=== Compliant Ranking ===")
    ranked = rank_deposits(products, stability)
    for i, (product, score) in enumerate(ranked, 1):
        print(f"{i}. {product.name} ({product.bank_name}) - Score: {score:.3f}")

    print("\n=== Biased Ranking (for testing) ===")
    biased = rank_deposits_with_bias(products, ["신한은행"])
    for i, (product, score) in enumerate(biased, 1):
        affiliate = "★" if product.is_affiliated else ""
        print(f"{i}. {product.name} ({product.bank_name}) {affiliate} - Score: {score:.3f}")
