"""Demo data helpers for Kompline.

Keeps sample compliance definitions and artifact registration in one place
so CLI, API, and UI can share the same setup flow.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from kompline.models import (
    AccessMethod,
    Artifact,
    ArtifactType,
    Compliance,
    EvidenceRequirement,
    Provenance,
    Rule,
    RuleCategory,
    RuleSeverity,
)
from kompline.registry import get_artifact_registry, get_compliance_registry


def register_demo_compliances(include_privacy: bool = True) -> list[str]:
    """Register built-in demo compliances if missing.

    Returns a list of compliance IDs registered or already present.
    """
    registry = get_compliance_registry()
    registered: list[str] = []

    if not registry.get("byeolji5-fairness"):
        registry.register(
            Compliance(
                id="byeolji5-fairness",
                name="알고리즘 공정성 자가평가",
                version="2024.01",
                jurisdiction="KR",
                scope=["algorithm", "ranking"],
                report_template="byeolji5",
                description="금융상품 비교·추천 플랫폼의 알고리즘 공정성 자가평가 (별지5 양식)",
                rules=[
                    Rule(
                        id="ALG-001",
                        title="정렬 기준 투명성",
                        description="정렬 알고리즘은 명확하고 문서화된 기준을 가져야 합니다",
                        category=RuleCategory.ALGORITHM_FAIRNESS,
                        severity=RuleSeverity.HIGH,
                        check_points=[
                            "Sorting criteria must be explicitly defined",
                            "Weight factors must be documented",
                        ],
                        pass_criteria="All sorting factors are documented",
                        fail_examples=["Undocumented weight factors"],
                    ),
                    Rule(
                        id="ALG-002",
                        title="계열사 편향 금지",
                        description="계열사 상품에 대한 부당한 우대 금지",
                        category=RuleCategory.ALGORITHM_FAIRNESS,
                        severity=RuleSeverity.CRITICAL,
                        check_points=[
                            "No preferential ranking for affiliates",
                            "Affiliate status must not affect score",
                        ],
                        pass_criteria="No affiliate bias in ranking",
                        fail_examples=["is_affiliated check", "affiliate_boost"],
                    ),
                    Rule(
                        id="ALG-003",
                        title="무작위화 공개",
                        description="결과에 영향을 미치는 무작위화는 공개해야 합니다",
                        category=RuleCategory.DISCLOSURE,
                        severity=RuleSeverity.HIGH,
                        check_points=[
                            "Randomization must be disclosed",
                            "No hidden shuffle",
                        ],
                        pass_criteria="Randomization is disclosed",
                        fail_examples=["Hidden shuffle()"],
                    ),
                ],
                evidence_requirements=[
                    EvidenceRequirement(
                        id="ER-001",
                        description="Source code of ranking algorithm",
                        artifact_types=["code"],
                        extraction_hints=["sort", "rank", "weight"],
                    ),
                ],
            )
        )
        registered.append("byeolji5-fairness")
    else:
        registered.append("byeolji5-fairness")

    if include_privacy:
        if not registry.get("pipa-kr-2024"):
            registry.register(
                Compliance(
                    id="pipa-kr-2024",
                    name="개인정보보호법",
                    version="2024.01",
                    jurisdiction="KR",
                    scope=["data_handling", "privacy"],
                    report_template="internal",
                    description="개인정보의 수집, 이용, 제공, 관리에 관한 규정",
                    rules=[
                        Rule(
                            id="PIPA-001",
                            title="최소 수집 원칙",
                            description="목적에 필요한 최소한의 개인정보만 수집",
                            category=RuleCategory.PRIVACY,
                            severity=RuleSeverity.HIGH,
                            check_points=[
                                "Data collection limited to purpose",
                                "No excessive data fields",
                            ],
                            pass_criteria="Only essential information collected",
                            fail_examples=["Collecting unnecessary fields"],
                        ),
                    ],
                    evidence_requirements=[],
                )
            )
            registered.append("pipa-kr-2024")
        else:
            registered.append("pipa-kr-2024")

    return registered


def register_file_artifact(
    file_path: str | Path,
    artifact_id: str | None = None,
    name: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """Register a local file as a code artifact.

    Returns the artifact ID.
    """
    path = Path(file_path)
    registry = get_artifact_registry()

    artifact = Artifact(
        id=artifact_id or path.stem,
        name=name or path.name,
        type=ArtifactType.CODE,
        locator=str(path.absolute()),
        access_method=AccessMethod.FILE_READ,
        provenance=Provenance(source=str(path.absolute())),
        tags=tags or [],
    )
    registry.register_or_update(artifact)
    return artifact.id


def register_repository_artifact(
    repo_url: str,
    artifact_id: str,
    name: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """Register a git repository artifact."""
    registry = get_artifact_registry()
    artifact = Artifact(
        id=artifact_id,
        name=name or artifact_id,
        type=ArtifactType.CODE,
        locator=repo_url,
        access_method=AccessMethod.GIT_CLONE,
        tags=tags or [],
    )
    registry.register_or_update(artifact)
    return artifact.id


def resolve_compliance_ids(requested: Iterable[str] | None) -> list[str]:
    """Resolve compliance IDs, registering demo defaults if needed."""
    register_demo_compliances()
    if not requested:
        return ["byeolji5-fairness"]
    return list(requested)
