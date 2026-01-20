"""Human-in-the-loop review request and response handling."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from .triggers import ReviewContext, ReviewTrigger


class ReviewerRole(Enum):
    """Role of the reviewer."""

    AUDITEE = "auditee"  # 피감사자 (Developer)
    AUDITOR = "auditor"  # 감사자 (Auditor)


class ReviewAction(Enum):
    """Actions available to reviewers."""

    APPROVE = "approve"  # Confirm the judgment
    REJECT = "reject"  # Reject the judgment
    REQUEST_ANALYSIS = "request_analysis"  # Request additional analysis
    ADD_CONTEXT = "add_context"  # Add context/explanation


@dataclass
class ReviewRequest:
    """A request for human review."""

    id: str
    created_at: str
    context: ReviewContext
    target_role: ReviewerRole
    status: str = "pending"  # pending, in_progress, completed
    assigned_to: str | None = None

    @classmethod
    def create(
        cls,
        context: ReviewContext,
        target_role: ReviewerRole = ReviewerRole.AUDITOR,
    ) -> "ReviewRequest":
        """Create a new review request."""
        return cls(
            id=f"REV-{uuid4().hex[:8].upper()}",
            created_at=datetime.now().isoformat(),
            context=context,
            target_role=target_role,
        )


@dataclass
class ReviewResponse:
    """Response from a human reviewer."""

    request_id: str
    reviewer_role: ReviewerRole
    action: ReviewAction
    comment: str
    additional_context: str | None = None
    selected_options: list[str] = field(default_factory=list)
    responded_at: str = field(default_factory=lambda: datetime.now().isoformat())


_TRIGGER_SPECIFIC_OPTIONS: dict[ReviewTrigger, list[dict[str, str]]] = {
    ReviewTrigger.LOW_CONFIDENCE: [
        {
            "id": "add_context",
            "label": "컨텍스트 추가",
            "description": "추가 설명을 제공하여 신뢰도를 높입니다",
        },
    ],
    ReviewTrigger.NEW_PATTERN: [
        {
            "id": "document_pattern",
            "label": "패턴 문서화",
            "description": "새로운 패턴을 규정에 추가합니다",
        },
    ],
    ReviewTrigger.FAIL_JUDGMENT: [
        {
            "id": "request_fix",
            "label": "수정 요청",
            "description": "코드 수정을 요청합니다",
        },
        {
            "id": "false_positive",
            "label": "오탐 (False Positive)",
            "description": "실제로는 문제가 없음을 확인합니다",
        },
    ],
}


def create_review_options(trigger: ReviewTrigger) -> list[dict[str, str]]:
    """Create review options based on the trigger reason.

    Args:
        trigger: The trigger that caused the review request.

    Returns:
        List of option dictionaries with id, label, and description.
    """
    options = [
        {
            "id": "approve",
            "label": "승인 (Approve)",
            "description": "판정 결과를 승인합니다",
        },
        {
            "id": "reject",
            "label": "거부 (Reject)",
            "description": "판정 결과를 거부하고 재검토를 요청합니다",
        },
    ]
    options.extend(_TRIGGER_SPECIFIC_OPTIONS.get(trigger, []))
    return options


def handle_review(
    request: ReviewRequest,
    response: ReviewResponse,
) -> dict[str, Any]:
    """Process a review response.

    Args:
        request: The original review request.
        response: The reviewer's response.

    Returns:
        Dictionary with processing result and next steps.
    """
    result = {
        "request_id": request.id,
        "status": "processed",
        "action_taken": response.action.value,
        "reviewer_role": response.reviewer_role.value,
        "next_steps": [],
    }

    if response.action == ReviewAction.APPROVE:
        result["final_status"] = request.context.confidence >= 0.7
        result["next_steps"].append("Proceed to report generation")

    elif response.action == ReviewAction.REJECT:
        result["final_status"] = "rejected"
        result["next_steps"].append("Re-analyze with feedback")
        if response.comment:
            result["feedback"] = response.comment

    elif response.action == ReviewAction.REQUEST_ANALYSIS:
        result["final_status"] = "pending"
        result["next_steps"].append("Trigger feedback loop to Code Analyzer")
        result["analysis_focus"] = response.additional_context

    elif response.action == ReviewAction.ADD_CONTEXT:
        result["final_status"] = "updated"
        result["next_steps"].append("Re-evaluate with new context")
        result["new_context"] = response.additional_context

    return result


class ReviewQueue:
    """Queue for managing review requests."""

    def __init__(self):
        self.pending: list[ReviewRequest] = []
        self.completed: list[tuple[ReviewRequest, ReviewResponse]] = []

    def add(self, request: ReviewRequest) -> str:
        """Add a review request to the queue."""
        self.pending.append(request)
        return request.id

    def get_pending(self, role: ReviewerRole | None = None) -> list[ReviewRequest]:
        """Get pending reviews, optionally filtered by role."""
        if role:
            return [r for r in self.pending if r.target_role == role]
        return self.pending.copy()

    def complete(self, request_id: str, response: ReviewResponse) -> dict[str, Any]:
        """Complete a review with a response."""
        for i, request in enumerate(self.pending):
            if request.id == request_id:
                request.status = "completed"
                self.pending.pop(i)
                self.completed.append((request, response))
                return handle_review(request, response)
        return {"error": f"Request {request_id} not found"}


# Global review queue
review_queue = ReviewQueue()
