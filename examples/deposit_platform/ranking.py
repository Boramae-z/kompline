"""예금상품 정렬 알고리즘.

이 모듈은 예금상품을 정렬하는 핵심 알고리즘을 구현합니다.
알고리즘 공정성 자가평가의 주요 감사 대상입니다.

감사 항목:
- ALG-001: 정렬 기준 투명성
- ALG-002: 계열사 편향 금지
- ALG-003: 무작위화 공개
- ALG-004: 가중치 문서화
"""

import random
from typing import Callable

from .config import DEFAULT_CONFIG, RankingConfig
from .data import BANKS, get_bank
from .models import DepositProduct, ProductRanking


class DepositRanker:
    """예금상품 정렬기.

    설정된 가중치와 기준에 따라 예금상품을 정렬합니다.
    모든 정렬 기준은 투명하게 문서화되어 있습니다.
    """

    def __init__(self, config: RankingConfig | None = None):
        """정렬기 초기화.

        Args:
            config: 정렬 설정. None이면 기본 설정 사용.
        """
        self.config = config or DEFAULT_CONFIG
        self._validate_config()

    def _validate_config(self) -> None:
        """설정 유효성 검증."""
        warnings = self.config.validate()
        if warnings and self.config.debug_mode:
            for w in warnings:
                print(f"[WARNING] {w}")

    def rank(
        self,
        products: list[DepositProduct],
        sort_key: str = "score",
        ascending: bool = False,
    ) -> list[ProductRanking]:
        """상품 목록을 정렬합니다.

        Args:
            products: 정렬할 상품 목록
            sort_key: 정렬 기준 ("score", "max_rate", "base_rate")
            ascending: 오름차순 정렬 여부

        Returns:
            정렬된 ProductRanking 목록
        """
        # 각 상품의 점수 계산
        rankings: list[ProductRanking] = []
        for product in products:
            score, breakdown = self._calculate_score(product)
            rankings.append(
                ProductRanking(
                    product=product,
                    rank=0,  # 정렬 후 설정
                    score=score,
                    score_breakdown=breakdown,
                )
            )

        # 정렬 키 선택
        key_func = self._get_sort_key(sort_key)

        # 정렬 수행
        rankings.sort(key=key_func, reverse=not ascending)

        # 무작위화 처리 (동점인 경우)
        if self.config.enable_randomization:
            rankings = self._apply_randomization(rankings)

        # 순위 부여
        for i, ranking in enumerate(rankings, 1):
            ranking.rank = i

        return rankings

    def _calculate_score(
        self, product: DepositProduct
    ) -> tuple[float, dict[str, float]]:
        """상품 점수 계산.

        점수 계산 공식:
        총점 = (최고금리 점수 × 가중치) + (기본금리 점수 × 가중치)
             + (접근성 점수 × 가중치) + (유연성 점수 × 가중치)
             + (혜택 점수 × 가중치) + 계열사 부스트

        Args:
            product: 점수를 계산할 상품

        Returns:
            (총점, 항목별 점수 딕셔너리)
        """
        weights = self.config.weights
        breakdown = {}

        # 1. 최고금리 점수 (0~1 정규화)
        max_rate_score = self._normalize_rate(product.max_rate)
        breakdown["max_rate"] = max_rate_score * weights.max_rate

        # 2. 기본금리 점수 (0~1 정규화)
        base_rate_score = self._normalize_rate(product.base_rate)
        breakdown["base_rate"] = base_rate_score * weights.base_rate

        # 3. 접근성 점수
        accessibility_score = self._calculate_accessibility(product)
        breakdown["accessibility"] = accessibility_score * weights.accessibility

        # 4. 유연성 점수
        flexibility_score = self._calculate_flexibility(product)
        breakdown["flexibility"] = flexibility_score * weights.flexibility

        # 5. 혜택 점수
        benefits_score = self._calculate_benefits(product)
        breakdown["benefits"] = benefits_score * weights.benefits

        # 기본 총점
        total = sum(breakdown.values())

        # === 계열사 부스트 (감사 대상) ===
        # WARNING: affiliate_boost > 0 이면 ALG-002 위반
        if self.config.affiliate_boost > 0:
            bank = get_bank(product.bank_code)
            if bank and bank.is_affiliate:
                affiliate_bonus = self.config.affiliate_boost
                breakdown["affiliate_boost"] = affiliate_bonus
                total += affiliate_bonus

        return total, breakdown

    def _normalize_rate(self, rate: float) -> float:
        """금리를 0~1 범위로 정규화.

        Args:
            rate: 금리 (%)

        Returns:
            정규화된 점수 (0~1)
        """
        min_rate = self.config.rate_normalization_min
        max_rate = self.config.rate_normalization_max

        if rate <= min_rate:
            return 0.0
        if rate >= max_rate:
            return 1.0
        return (rate - min_rate) / (max_rate - min_rate)

    def _calculate_accessibility(self, product: DepositProduct) -> float:
        """접근성 점수 계산.

        최소 가입금액과 가입 방법을 기준으로 계산합니다.

        Args:
            product: 상품

        Returns:
            접근성 점수 (0~1)
        """
        # 최소 가입금액 점수
        amount_score = 0.0
        for threshold, score in self.config.min_amount_thresholds:
            if product.min_amount <= threshold:
                amount_score = score
                break

        # 가입 방법 점수
        method_score = sum(
            self.config.join_method_scores.get(method, 0)
            for method in product.join_method
        )
        method_score = min(method_score, 1.0)  # 최대 1.0

        # 평균
        return (amount_score + method_score) / 2

    def _calculate_flexibility(self, product: DepositProduct) -> float:
        """기간 유연성 점수 계산.

        가입 가능 기간 범위가 넓을수록 높은 점수.

        Args:
            product: 상품

        Returns:
            유연성 점수 (0~1)
        """
        term_range = product.max_term_months - product.min_term_months
        max_range = self.config.term_flexibility_max_months

        return min(term_range / max_range, 1.0)

    def _calculate_benefits(self, product: DepositProduct) -> float:
        """혜택 점수 계산.

        우대조건 수에 따라 점수 부여.

        Args:
            product: 상품

        Returns:
            혜택 점수 (0~1)
        """
        num_benefits = len(product.preferential_conditions)
        # 최대 5개까지 고려
        return min(num_benefits / 5, 1.0)

    def _get_sort_key(self, sort_key: str) -> Callable[[ProductRanking], float]:
        """정렬 키 함수 반환.

        Args:
            sort_key: 정렬 기준

        Returns:
            정렬 키 함수
        """
        if sort_key == "max_rate":
            return lambda r: r.product.max_rate
        elif sort_key == "base_rate":
            return lambda r: r.product.base_rate
        else:  # "score" (default)
            return lambda r: r.score

    def _apply_randomization(
        self, rankings: list[ProductRanking]
    ) -> list[ProductRanking]:
        """동점 상품에 대한 무작위화 적용.

        동점인 상품들의 순서를 무작위로 섞습니다.
        이 기능이 활성화된 경우 사용자에게 공개해야 합니다.

        Args:
            rankings: 정렬된 랭킹 목록

        Returns:
            동점 무작위화가 적용된 랭킹 목록
        """
        if self.config.random_seed is not None:
            random.seed(self.config.random_seed)

        # 동점 그룹 찾기 및 섞기
        result = []
        i = 0
        while i < len(rankings):
            # 현재 점수와 같은 점수를 가진 상품들 찾기
            current_score = rankings[i].score
            group = [rankings[i]]
            j = i + 1
            while j < len(rankings) and abs(rankings[j].score - current_score) < 0.0001:
                group.append(rankings[j])
                j += 1

            # 그룹 섞기
            if len(group) > 1:
                random.shuffle(group)

            result.extend(group)
            i = j

        return result


def rank_products(
    products: list[DepositProduct],
    config: RankingConfig | None = None,
) -> list[ProductRanking]:
    """상품 정렬 편의 함수.

    Args:
        products: 정렬할 상품 목록
        config: 정렬 설정

    Returns:
        정렬된 랭킹 목록
    """
    ranker = DepositRanker(config)
    return ranker.rank(products)


def get_top_products(
    products: list[DepositProduct],
    n: int = 5,
    config: RankingConfig | None = None,
) -> list[ProductRanking]:
    """상위 N개 상품 조회.

    Args:
        products: 상품 목록
        n: 조회할 상품 수
        config: 정렬 설정

    Returns:
        상위 N개 랭킹 목록
    """
    rankings = rank_products(products, config)
    return rankings[:n]
