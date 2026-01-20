"""Rule Evaluator for compliance rule assessment."""

import uuid
from typing import Any

from kompline.models import (
    Citation,
    Evidence,
    EvidenceCollection,
    Finding,
    FindingStatus,
    Rule,
    RuleCategory,
    RuleSeverity,
)
from kompline.tools.rag_query import get_builtin_rules, get_citation_for_rule, query_compliance_rules
from kompline.tracing.logger import log_agent_event


class RuleEvaluator:
    """Evaluates compliance rules against collected evidence.

    This class provides methods for evaluating rules using:
    - Heuristic pattern matching
    - RAG-based rule lookup
    - Built-in rule evaluation
    """

    def __init__(self, use_rag: bool = True):
        """Initialize the rule evaluator.

        Args:
            use_rag: Whether to use RAG for rule lookup.
        """
        self.use_rag = use_rag

    async def evaluate_rule(
        self,
        rule: Rule,
        evidence: EvidenceCollection,
        relation_id: str,
    ) -> Finding:
        """Evaluate a single rule against evidence.

        Args:
            rule: The rule to evaluate.
            evidence: Collected evidence.
            relation_id: The audit relation ID.

        Returns:
            Finding with evaluation result.
        """
        # Get evidence relevant to this rule
        relevant_evidence = evidence.get_by_rule(rule.id)
        if not relevant_evidence:
            relevant_evidence = list(evidence)

        # Evaluate based on rule category
        if rule.category == RuleCategory.ALGORITHM_FAIRNESS:
            status, confidence, reasoning = self._evaluate_algorithm_fairness(
                rule, relevant_evidence
            )
        elif rule.category == RuleCategory.TRANSPARENCY:
            status, confidence, reasoning = self._evaluate_transparency(
                rule, relevant_evidence
            )
        elif rule.category == RuleCategory.DISCLOSURE:
            status, confidence, reasoning = self._evaluate_disclosure(
                rule, relevant_evidence
            )
        else:
            status, confidence, reasoning = self._evaluate_generic(
                rule, relevant_evidence
            )

        # Determine if human review is needed
        requires_review = self._needs_human_review(status, confidence, rule)

        # Generate recommendation if failed
        recommendation = None
        if status == FindingStatus.FAIL:
            recommendation = self._generate_recommendation(rule, relevant_evidence)

        # Get citation for rule
        citations = self._get_citations_for_rule(rule)

        finding = Finding(
            id=f"find-{uuid.uuid4().hex[:8]}",
            relation_id=relation_id,
            rule_id=rule.id,
            status=status,
            confidence=confidence,
            evidence_refs=[e.id for e in relevant_evidence],
            reasoning=reasoning,
            recommendation=recommendation,
            citations=citations,
            requires_human_review=requires_review,
        )

        log_agent_event(
            "evaluation", "rule_evaluator",
            f"Rule {rule.id}: {status.value} (confidence: {confidence:.2f})"
        )

        return finding

    def _evaluate_algorithm_fairness(
        self,
        rule: Rule,
        evidence: list[Evidence],
    ) -> tuple[FindingStatus, float, str]:
        """Evaluate algorithm fairness rules.

        Checks for:
        - Undocumented sorting/ranking factors
        - Affiliate/sponsor bias
        - Hidden weights or preferences
        """
        if not evidence:
            return (
                FindingStatus.REVIEW,
                0.5,
                "Insufficient evidence for algorithm fairness evaluation"
            )

        issues = []
        passes = []

        for ev in evidence:
            content_lower = ev.content.lower()
            metadata = ev.metadata or {}

            # Check for bias indicators
            bias_keywords = ["affiliate", "sponsor", "preferred", "boost", "is_affiliated"]
            if any(kw in content_lower for kw in bias_keywords):
                if metadata.get("is_issue") or "boost" in content_lower:
                    issues.append(f"Potential bias detected at {ev.location_str}: {ev.content[:100]}")

            # Check for documented weights
            if metadata.get("category") == "weighting":
                if "RANKING_WEIGHTS" in ev.content or "documented" in content_lower:
                    passes.append("Weight factors are documented")
                else:
                    issues.append("Undocumented weight factors found")

            # Check for sorting transparency
            if "sort" in content_lower:
                if "key=" in content_lower or "documented" in content_lower:
                    passes.append("Sorting criteria documented")

        if issues:
            return (
                FindingStatus.FAIL,
                0.85,
                f"Algorithm fairness issues: {'; '.join(issues[:3])}"
            )

        if passes:
            return (
                FindingStatus.PASS,
                0.80,
                f"Algorithm fairness checks passed: {'; '.join(passes[:3])}"
            )

        return (
            FindingStatus.REVIEW,
            0.60,
            "Algorithm patterns found but require human review"
        )

    def _evaluate_transparency(
        self,
        rule: Rule,
        evidence: list[Evidence],
    ) -> tuple[FindingStatus, float, str]:
        """Evaluate transparency rules.

        Checks for:
        - Documentation of decision factors
        - Clear explanation of logic
        """
        if not evidence:
            return (
                FindingStatus.REVIEW,
                0.5,
                "Insufficient evidence for transparency evaluation"
            )

        has_documentation = False
        has_comments = False

        for ev in evidence:
            metadata = ev.metadata or {}

            # Check for docstrings
            if metadata.get("docstring"):
                has_documentation = True

            # Check for comments explaining logic
            if "#" in ev.content and any(
                word in ev.content.lower() for word in ["criteria", "factor", "weight", "logic"]
            ):
                has_comments = True

        if has_documentation and has_comments:
            return (
                FindingStatus.PASS,
                0.85,
                "Code has documentation and explanatory comments"
            )
        elif has_documentation or has_comments:
            return (
                FindingStatus.REVIEW,
                0.65,
                "Partial documentation found, human review recommended"
            )

        return (
            FindingStatus.FAIL,
            0.75,
            "Insufficient documentation of decision logic"
        )

    def _evaluate_disclosure(
        self,
        rule: Rule,
        evidence: list[Evidence],
    ) -> tuple[FindingStatus, float, str]:
        """Evaluate disclosure rules.

        Checks for:
        - Randomization disclosure
        - Factor disclosure to users
        """
        if not evidence:
            return (
                FindingStatus.REVIEW,
                0.5,
                "Insufficient evidence for disclosure evaluation"
            )

        has_randomization = False
        randomization_disclosed = False

        for ev in evidence:
            content_lower = ev.content.lower()

            if "random" in content_lower or "shuffle" in content_lower:
                has_randomization = True
                # Check if disclosed
                if "disclosed" in content_lower or "warning" in ev.content:
                    randomization_disclosed = True

        if has_randomization and not randomization_disclosed:
            return (
                FindingStatus.FAIL,
                0.90,
                "Randomization detected without disclosure"
            )

        if has_randomization and randomization_disclosed:
            return (
                FindingStatus.PASS,
                0.85,
                "Randomization is disclosed"
            )

        return (
            FindingStatus.PASS,
            0.80,
            "No undisclosed randomization found"
        )

    def _evaluate_generic(
        self,
        rule: Rule,
        evidence: list[Evidence],
    ) -> tuple[FindingStatus, float, str]:
        """Generic rule evaluation using check points.

        Counts how many check points are covered by evidence.
        """
        if not evidence:
            return (
                FindingStatus.REVIEW,
                0.5,
                "Insufficient evidence to evaluate this rule"
            )

        if not rule.check_points:
            return (
                FindingStatus.REVIEW,
                0.6,
                "Rule has no check points defined"
            )

        # Check coverage of check points
        covered_points = 0
        for check_point in rule.check_points:
            check_words = check_point.lower().split()
            for ev in evidence:
                if any(word in ev.content.lower() for word in check_words if len(word) > 3):
                    covered_points += 1
                    break

        coverage = covered_points / len(rule.check_points)

        if coverage >= 0.8:
            return (
                FindingStatus.PASS,
                0.75 + (coverage * 0.2),
                f"Evidence covers {covered_points}/{len(rule.check_points)} check points"
            )
        elif coverage >= 0.5:
            return (
                FindingStatus.REVIEW,
                0.55 + (coverage * 0.15),
                f"Partial coverage: {covered_points}/{len(rule.check_points)} check points"
            )

        return (
            FindingStatus.REVIEW,
            0.5,
            f"Low coverage: {covered_points}/{len(rule.check_points)} check points"
        )

    def _needs_human_review(
        self,
        status: FindingStatus,
        confidence: float,
        rule: Rule,
    ) -> bool:
        """Determine if human review is needed.

        Args:
            status: The finding status.
            confidence: The confidence score.
            rule: The evaluated rule.

        Returns:
            True if human review is needed.
        """
        # Always review failures
        if status == FindingStatus.FAIL:
            return True

        # Low confidence
        if confidence < 0.7:
            return True

        # Review status
        if status == FindingStatus.REVIEW:
            return True

        # Critical rules always need verification
        if rule.severity == RuleSeverity.CRITICAL:
            return True

        return False

    def _get_citations_for_rule(self, rule: Rule) -> list[Citation]:
        """Get citations for a rule from builtin rules or RAG.

        Args:
            rule: The rule to get citations for.

        Returns:
            List of Citation objects.
        """
        citations = []

        # Try to get citation from builtin rules
        citation_dict = get_citation_for_rule(rule.id)
        if citation_dict:
            citations.append(
                Citation(
                    source=citation_dict.get("source", rule.id),
                    text=citation_dict.get("text", rule.description),
                    relevance=citation_dict.get("relevance", 1.0),
                    page=citation_dict.get("page"),
                    section=citation_dict.get("section"),
                )
            )
        else:
            # Create a citation from rule metadata
            citations.append(
                Citation(
                    source=f"Rule {rule.id}",
                    text=rule.description,
                    relevance=1.0,
                    section=rule.category.value if rule.category else None,
                )
            )

        return citations

    def _generate_recommendation(
        self,
        rule: Rule,
        evidence: list[Evidence],
    ) -> str:
        """Generate a recommendation for failed rules.

        Args:
            rule: The failed rule.
            evidence: Related evidence.

        Returns:
            Recommendation string.
        """
        recommendations = []

        if rule.category == RuleCategory.ALGORITHM_FAIRNESS:
            recommendations.append(
                "Review and document all ranking/sorting factors"
            )
            recommendations.append(
                "Remove or disclose any affiliate/sponsor preferences"
            )

        elif rule.category == RuleCategory.TRANSPARENCY:
            recommendations.append(
                "Add documentation explaining decision logic"
            )
            recommendations.append(
                "Include comments describing weight factors"
            )

        elif rule.category == RuleCategory.DISCLOSURE:
            recommendations.append(
                "Disclose all randomization to users"
            )
            recommendations.append(
                "Document any factors that affect ordering"
            )

        if rule.fail_examples:
            recommendations.append(
                f"Avoid patterns like: {rule.fail_examples[0]}"
            )

        return "; ".join(recommendations[:3])


def create_rule_evaluator(use_rag: bool = True) -> RuleEvaluator:
    """Create a RuleEvaluator instance.

    Args:
        use_rag: Whether to use RAG for rule lookup.

    Returns:
        Configured RuleEvaluator.
    """
    return RuleEvaluator(use_rag=use_rag)
