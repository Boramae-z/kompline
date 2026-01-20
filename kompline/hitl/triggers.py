"""Human-in-the-loop trigger conditions for Finding-based workflow."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from kompline.models import Finding, FindingStatus


class ReviewTrigger(Enum):
    """Reasons for triggering human review."""

    LOW_CONFIDENCE = "low_confidence"
    NEW_PATTERN = "new_pattern"
    FAIL_JUDGMENT = "fail_judgment"
    MULTIPLE_ISSUES = "multiple_issues"
    MANUAL_REQUEST = "manual_request"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    CRITICAL_RULE = "critical_rule"


@dataclass
class ReviewRequest:
    """Request for human review of a finding."""

    id: str
    finding_id: str
    trigger: ReviewTrigger
    priority: int  # 1 = highest, 5 = lowest
    created_at: datetime = field(default_factory=datetime.now)
    context: dict[str, Any] = field(default_factory=dict)
    assigned_to: str | None = None
    status: str = "pending"  # pending, in_review, resolved
    resolution: str | None = None
    resolved_at: datetime | None = None

    @property
    def is_resolved(self) -> bool:
        """Check if review is resolved."""
        return self.status == "resolved"


@dataclass
class ReviewContext:
    """Context for a review request."""

    trigger: ReviewTrigger
    rule_id: str | None
    confidence: float
    evidence: list[str]
    code_snippet: str | None
    agent_notes: str
    finding: Finding | None = None


class ReviewTriggerEvaluator:
    """Evaluates findings to determine if human review is needed."""

    def __init__(
        self,
        confidence_threshold: float = 0.7,
        known_patterns: set[str] | None = None,
    ):
        """Initialize the evaluator.

        Args:
            confidence_threshold: Minimum confidence for auto-approval.
            known_patterns: Set of known patterns that don't need review.
        """
        self.confidence_threshold = confidence_threshold
        self.known_patterns = known_patterns or KNOWN_PATTERNS

    def evaluate_finding(self, finding: Finding) -> tuple[bool, ReviewRequest | None]:
        """Evaluate a finding to determine if review is needed.

        Args:
            finding: The finding to evaluate.

        Returns:
            Tuple of (needs_review, review_request).
        """
        import uuid

        # Already marked for review
        if finding.requires_human_review:
            trigger = self._determine_trigger(finding)
            priority = self._calculate_priority(finding, trigger)

            request = ReviewRequest(
                id=f"review-{uuid.uuid4().hex[:8]}",
                finding_id=finding.id,
                trigger=trigger,
                priority=priority,
                context={
                    "rule_id": finding.rule_id,
                    "status": finding.status.value,
                    "confidence": finding.confidence,
                    "reasoning": finding.reasoning,
                    "evidence_count": len(finding.evidence_refs),
                },
            )
            return True, request

        # Additional checks
        needs_review, trigger = self._check_triggers(finding)

        if not needs_review:
            return False, None

        priority = self._calculate_priority(finding, trigger)

        request = ReviewRequest(
            id=f"review-{uuid.uuid4().hex[:8]}",
            finding_id=finding.id,
            trigger=trigger,
            priority=priority,
            context={
                "rule_id": finding.rule_id,
                "status": finding.status.value,
                "confidence": finding.confidence,
                "reasoning": finding.reasoning,
            },
        )

        return True, request

    def _determine_trigger(self, finding: Finding) -> ReviewTrigger:
        """Determine the primary trigger for a finding needing review."""
        if finding.status == FindingStatus.FAIL:
            return ReviewTrigger.FAIL_JUDGMENT

        if finding.confidence < self.confidence_threshold:
            return ReviewTrigger.LOW_CONFIDENCE

        if finding.status == FindingStatus.REVIEW:
            return ReviewTrigger.MANUAL_REQUEST

        return ReviewTrigger.LOW_CONFIDENCE

    def _check_triggers(self, finding: Finding) -> tuple[bool, ReviewTrigger | None]:
        """Check all trigger conditions for a finding.

        Args:
            finding: The finding to check.

        Returns:
            Tuple of (needs_review, trigger_reason).
        """
        # Trigger 1: Low confidence
        if finding.confidence < self.confidence_threshold:
            return True, ReviewTrigger.LOW_CONFIDENCE

        # Trigger 2: FAIL judgment always needs confirmation
        if finding.status == FindingStatus.FAIL:
            return True, ReviewTrigger.FAIL_JUDGMENT

        # Trigger 3: REVIEW status
        if finding.status == FindingStatus.REVIEW:
            return True, ReviewTrigger.MANUAL_REQUEST

        return False, None

    def _calculate_priority(self, finding: Finding, trigger: ReviewTrigger) -> int:
        """Calculate review priority (1 = highest, 5 = lowest).

        Args:
            finding: The finding.
            trigger: The trigger reason.

        Returns:
            Priority level (1-5).
        """
        # FAIL findings are highest priority
        if finding.status == FindingStatus.FAIL:
            return 1

        # Critical rules
        if trigger == ReviewTrigger.CRITICAL_RULE:
            return 1

        # Low confidence on important findings
        if trigger == ReviewTrigger.LOW_CONFIDENCE and finding.confidence < 0.5:
            return 2

        # Other FAIL-related triggers
        if trigger == ReviewTrigger.FAIL_JUDGMENT:
            return 2

        # Conflicting evidence
        if trigger == ReviewTrigger.CONFLICTING_EVIDENCE:
            return 3

        # Default priority
        return 4


# Known patterns that don't require special review
KNOWN_PATTERNS = {
    "SORTING_ALGORITHM",
    "WEIGHTED_CALCULATION",
    "RANKING_LOGIC",
    "FILTERING_LOGIC",
    "COMPARISON_LOGIC",
    "CONDITIONAL_LOGIC",
}


def should_request_review(
    status: str,
    confidence: float,
    patterns: list[str] | None = None,
    known_patterns: set[str] | None = None,
    issue_count: int = 0,
    confidence_threshold: float = 0.7,
) -> tuple[bool, ReviewTrigger | None]:
    """Determine if human review should be requested (legacy function).

    Args:
        status: The judgment status (PASS, FAIL, REVIEW).
        confidence: Confidence score (0.0 to 1.0).
        patterns: Detected patterns in the code.
        known_patterns: Set of known/documented patterns.
        issue_count: Number of issues found.
        confidence_threshold: Threshold below which review is needed.

    Returns:
        Tuple of (should_review, trigger_reason).
    """
    patterns = patterns or []
    known_patterns = known_patterns or KNOWN_PATTERNS

    # Trigger 1: Low confidence
    if confidence < confidence_threshold:
        return True, ReviewTrigger.LOW_CONFIDENCE

    # Trigger 2: New/unknown pattern
    unknown_patterns = [p for p in patterns if p not in known_patterns]
    if unknown_patterns:
        return True, ReviewTrigger.NEW_PATTERN

    # Trigger 3: FAIL judgment always needs confirmation
    if status == "FAIL":
        return True, ReviewTrigger.FAIL_JUDGMENT

    # Trigger 4: Multiple issues
    if issue_count >= 3:
        return True, ReviewTrigger.MULTIPLE_ISSUES

    return False, None


def evaluate_finding_for_review(finding: Finding) -> tuple[bool, ReviewRequest | None]:
    """Evaluate a Finding to determine if review is needed.

    Args:
        finding: The finding to evaluate.

    Returns:
        Tuple of (needs_review, review_request).
    """
    evaluator = ReviewTriggerEvaluator()
    return evaluator.evaluate_finding(finding)


def evaluate_check_result(check_result: dict[str, Any]) -> tuple[bool, ReviewContext | None]:
    """Evaluate a check result to determine if review is needed (legacy).

    Args:
        check_result: The compliance check result dictionary.

    Returns:
        Tuple of (needs_review, review_context).
    """
    status = check_result.get("status", "REVIEW")
    confidence = check_result.get("confidence", 0.0)
    patterns = check_result.get("patterns", [])
    issues = check_result.get("issues", [])

    needs_review, trigger = should_request_review(
        status=status,
        confidence=confidence,
        patterns=patterns,
        known_patterns=KNOWN_PATTERNS,
        issue_count=len(issues),
    )

    if not needs_review:
        return False, None

    context = ReviewContext(
        trigger=trigger,
        rule_id=check_result.get("rule_id"),
        confidence=confidence,
        evidence=check_result.get("evidence", []),
        code_snippet=check_result.get("code_snippet"),
        agent_notes=check_result.get("recommendation", ""),
    )

    return True, context
