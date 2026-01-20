"""정렬 알고리즘 설정.

이 파일은 예금상품 정렬에 사용되는 가중치와 설정을 정의합니다.
알고리즘 공정성 자가평가의 핵심 감사 대상입니다.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RankingWeights:
    """정렬 점수 가중치 설정.

    각 요소의 가중치 합계는 1.0이어야 합니다.
    모든 가중치는 공정성 검증을 위해 명시적으로 문서화됩니다.
    """

    # 금리 관련 가중치
    max_rate: float = 0.50  # 최고금리 가중치 (가장 중요한 요소)
    base_rate: float = 0.20  # 기본금리 가중치

    # 접근성 가중치
    accessibility: float = 0.15  # 가입 편의성 (최소금액, 가입방법 등)

    # 유연성 가중치
    flexibility: float = 0.10  # 가입 기간 유연성

    # 부가 서비스 가중치
    benefits: float = 0.05  # 우대조건 수

    def validate(self) -> bool:
        """가중치 합계 검증."""
        total = (
            self.max_rate
            + self.base_rate
            + self.accessibility
            + self.flexibility
            + self.benefits
        )
        return abs(total - 1.0) < 0.001

    def to_dict(self) -> dict[str, float]:
        """딕셔너리로 변환."""
        return {
            "max_rate": self.max_rate,
            "base_rate": self.base_rate,
            "accessibility": self.accessibility,
            "flexibility": self.flexibility,
            "benefits": self.benefits,
        }


@dataclass
class RankingConfig:
    """정렬 알고리즘 전체 설정."""

    # 가중치 설정
    weights: RankingWeights = field(default_factory=RankingWeights)

    # 정규화 설정
    rate_normalization_max: float = 5.0  # 최대 금리 기준 (%)
    rate_normalization_min: float = 2.0  # 최소 금리 기준 (%)

    # 접근성 점수 기준
    min_amount_thresholds: list[tuple[int, float]] = field(
        default_factory=lambda: [
            (100, 1.0),  # 100원 이하: 최고 점수
            (100_000, 0.9),  # 10만원 이하
            (500_000, 0.7),  # 50만원 이하
            (1_000_000, 0.5),  # 100만원 이하
            (10_000_000, 0.3),  # 1000만원 이하
        ]
    )

    # 가입방법 점수
    join_method_scores: dict[str, float] = field(
        default_factory=lambda: {
            "app": 0.4,  # 앱 가입 가능
            "online": 0.3,  # 온라인 가입 가능
            "branch": 0.3,  # 영업점 가입 가능
        }
    )

    # 기간 유연성 점수
    term_flexibility_max_months: int = 36  # 최대 가입기간 기준

    # === 공정성 관련 설정 ===

    # 계열사 우대 설정 (기본값: 비활성화)
    # WARNING: 이 값이 0보다 크면 계열사 편향 위반 가능성
    affiliate_boost: float = 0.0

    # 무작위화 설정
    enable_randomization: bool = False  # 동점 처리 시 무작위화
    random_seed: int | None = None  # 재현 가능한 무작위화를 위한 시드

    # 디버그 설정
    debug_mode: bool = False  # 점수 상세 로깅

    def validate(self) -> list[str]:
        """설정 유효성 검증.

        Returns:
            경고 메시지 목록 (빈 리스트면 문제 없음)
        """
        warnings = []

        # 가중치 검증
        if not self.weights.validate():
            warnings.append("가중치 합계가 1.0이 아닙니다")

        # 계열사 우대 검증
        if self.affiliate_boost > 0:
            warnings.append(
                f"계열사 우대 부스트({self.affiliate_boost})가 설정됨 - "
                "알고리즘 공정성 위반 가능성"
            )

        # 무작위화 검증
        if self.enable_randomization and self.random_seed is None:
            warnings.append(
                "무작위화가 활성화되었지만 시드가 미설정 - "
                "결과 재현 불가능"
            )

        return warnings


# 기본 설정 인스턴스
DEFAULT_CONFIG = RankingConfig()

# 테스트용 설정 (계열사 우대 포함 - 감사 시 FAIL 예상)
BIASED_CONFIG = RankingConfig(
    affiliate_boost=0.15,  # 계열사 15% 부스트 (위반)
)

# 무작위화 포함 설정
RANDOMIZED_CONFIG = RankingConfig(
    enable_randomization=True,
    random_seed=42,
)
