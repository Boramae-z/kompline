"""Audit Orchestrator for managing multi-relation compliance audits."""

import asyncio
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agents import Agent

from kompline.agents.audit_agent import AuditAgent
from kompline.models import (
    AuditRelation,
    AuditStatus,
    Finding,
    FindingSummary,
    RunConfig,
    create_audit_relations,
)
from kompline.registry import get_artifact_registry, get_compliance_registry
from kompline.tracing.logger import log_agent_event


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3  # Maximum retry attempts
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 30.0  # Maximum delay in seconds
    exponential_base: float = 2.0  # Exponential backoff base
    jitter: bool = True  # Add random jitter to prevent thundering herd

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for a given attempt using exponential backoff.

        Args:
            attempt: The current attempt number (0-indexed).

        Returns:
            Delay in seconds.
        """
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        if self.jitter:
            delay = delay * (0.5 + random.random())
        return delay


class RetryableError(Exception):
    """Error that can be retried."""

    def __init__(self, message: str, can_redistribute: bool = False):
        """Initialize the error.

        Args:
            message: Error message.
            can_redistribute: Whether redistribution to alternative strategy might help.
        """
        super().__init__(message)
        self.can_redistribute = can_redistribute


class FallbackStrategy:
    """Fallback strategies for failed operations."""

    TEXT_ANALYSIS = "text_analysis"  # Fallback from AST to text analysis
    REDUCED_SCOPE = "reduced_scope"  # Reduce scope of analysis
    SKIP_RULE = "skip_rule"  # Mark rule as not applicable


@dataclass
class AuditResult:
    """Result of a complete audit run."""

    relations: list[AuditRelation]
    summaries: dict[str, FindingSummary]  # relation_id -> summary
    total_findings: int = 0
    total_passed: int = 0
    total_failed: int = 0
    total_review: int = 0

    @classmethod
    def from_relations(cls, relations: list[AuditRelation]) -> "AuditResult":
        """Create result from completed relations."""
        summaries = {}
        total_findings = 0
        total_passed = 0
        total_failed = 0
        total_review = 0

        for rel in relations:
            summary = FindingSummary.from_findings(rel.id, rel.findings)
            summaries[rel.id] = summary
            total_findings += summary.total
            total_passed += summary.passed
            total_failed += summary.failed
            total_review += summary.review

        return cls(
            relations=relations,
            summaries=summaries,
            total_findings=total_findings,
            total_passed=total_passed,
            total_failed=total_failed,
            total_review=total_review,
        )

    @property
    def is_compliant(self) -> bool:
        """Check if all relations pass."""
        return self.total_failed == 0 and self.total_review == 0

    @property
    def needs_review(self) -> bool:
        """Check if any findings need human review."""
        return self.total_review > 0 or self.total_failed > 0


class AuditOrchestrator:
    """Orchestrates multi-relation compliance audits.

    Responsibilities:
    1. Build audit relations from compliance and artifact IDs
    2. Spawn Audit Agents per relation (parallel execution)
    3. Aggregate findings into unified result
    4. Handle errors with retry and redistribution
    5. Trigger report generation
    """

    def __init__(
        self,
        parallel: bool = True,
        retry_config: RetryConfig | None = None,
    ):
        """Initialize the orchestrator.

        Args:
            parallel: Whether to run audits in parallel.
            retry_config: Configuration for retry behavior.
        """
        self.parallel = parallel
        self.retry_config = retry_config or RetryConfig()
        self._compliance_registry = get_compliance_registry()
        self._artifact_registry = get_artifact_registry()
        self._failed_relations: list[tuple[AuditRelation, str]] = []  # (relation, error)

    async def audit(
        self,
        compliance_ids: list[str],
        artifact_ids: list[str],
        run_config: RunConfig | None = None,
    ) -> AuditResult:
        """Run a compliance audit.

        Creates (Compliance, Artifact) relations and evaluates each.

        Args:
            compliance_ids: IDs of compliance frameworks to audit against.
            artifact_ids: IDs of artifacts to audit.
            run_config: Optional run configuration.

        Returns:
            AuditResult with all findings.
        """
        log_agent_event(
            "start", "orchestrator",
            f"Starting audit: {len(compliance_ids)} compliances × {len(artifact_ids)} artifacts"
        )

        # Validate inputs
        self._validate_inputs(compliance_ids, artifact_ids)

        # Create audit relations
        relations = create_audit_relations(compliance_ids, artifact_ids, run_config)

        log_agent_event(
            "relations", "orchestrator",
            f"Created {len(relations)} audit relations"
        )

        # Run audits
        if self.parallel and len(relations) > 1:
            completed = await self._run_parallel(relations)
        else:
            completed = await self._run_sequential(relations)

        # Aggregate results
        result = AuditResult.from_relations(completed)

        log_agent_event(
            "complete", "orchestrator",
            f"Audit complete: {result.total_passed} passed, "
            f"{result.total_failed} failed, {result.total_review} review"
        )

        return result

    async def audit_single(
        self,
        compliance_id: str,
        artifact_id: str,
        run_config: RunConfig | None = None,
    ) -> AuditRelation:
        """Run a single (Compliance, Artifact) audit.

        Args:
            compliance_id: The compliance framework ID.
            artifact_id: The artifact ID.
            run_config: Optional run configuration.

        Returns:
            The completed AuditRelation.
        """
        relations = create_audit_relations([compliance_id], [artifact_id], run_config)
        if not relations:
            raise ValueError("Failed to create audit relation")

        agent = AuditAgent()
        return await agent.evaluate(relations[0])

    def _validate_inputs(
        self,
        compliance_ids: list[str],
        artifact_ids: list[str],
    ) -> None:
        """Validate compliance and artifact IDs exist."""
        for comp_id in compliance_ids:
            if not self._compliance_registry.get(comp_id):
                raise ValueError(f"Compliance '{comp_id}' not found in registry")

        for art_id in artifact_ids:
            if not self._artifact_registry.get(art_id):
                raise ValueError(f"Artifact '{art_id}' not found in registry")

    async def _run_parallel(
        self,
        relations: list[AuditRelation],
    ) -> list[AuditRelation]:
        """Run audits in parallel with retry logic.

        Args:
            relations: The relations to audit.

        Returns:
            List of completed relations.
        """
        log_agent_event(
            "parallel", "orchestrator",
            f"Running {len(relations)} audits in parallel"
        )

        tasks = [self._run_with_retry(rel) for rel in relations]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        completed = []
        for rel, result in zip(relations, results):
            if isinstance(result, Exception):
                rel.fail(str(result))
                self._failed_relations.append((rel, str(result)))
                completed.append(rel)
            else:
                completed.append(result)

        # Attempt redistribution for failed relations
        if self._failed_relations:
            redistributed = await self._attempt_redistribution()
            # Update completed relations with redistributed results
            for orig_rel, new_result in redistributed:
                for i, rel in enumerate(completed):
                    if rel.id == orig_rel.id:
                        completed[i] = new_result
                        break

        return completed

    async def _run_with_retry(
        self,
        relation: AuditRelation,
    ) -> AuditRelation:
        """Run a single audit with retry logic.

        Args:
            relation: The relation to audit.

        Returns:
            Completed relation.

        Raises:
            Exception: If all retries fail.
        """
        last_error: Exception | None = None

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                agent = AuditAgent()
                result = await agent.evaluate(relation)

                if attempt > 0:
                    log_agent_event(
                        "retry_success", "orchestrator",
                        f"Relation {relation.id} succeeded on attempt {attempt + 1}"
                    )

                return result

            except Exception as e:
                last_error = e
                error_type = type(e).__name__

                if attempt < self.retry_config.max_retries:
                    delay = self.retry_config.get_delay(attempt)
                    log_agent_event(
                        "retry", "orchestrator",
                        f"Relation {relation.id} failed ({error_type}), "
                        f"retrying in {delay:.1f}s (attempt {attempt + 1}/{self.retry_config.max_retries})"
                    )
                    await asyncio.sleep(delay)
                else:
                    log_agent_event(
                        "retry_exhausted", "orchestrator",
                        f"Relation {relation.id} failed after {self.retry_config.max_retries} retries: {e}"
                    )

        raise last_error or Exception("Unknown error during retry")

    async def _attempt_redistribution(
        self,
    ) -> list[tuple[AuditRelation, AuditRelation]]:
        """Attempt to redistribute failed relations using alternative strategies.

        Returns:
            List of (original_relation, new_result) tuples for successful redistributions.
        """
        if not self._failed_relations:
            return []

        log_agent_event(
            "redistribute", "orchestrator",
            f"Attempting redistribution for {len(self._failed_relations)} failed relations"
        )

        redistributed = []

        for relation, error in self._failed_relations:
            # Determine redistribution strategy based on error type
            strategy = self._determine_fallback_strategy(error)

            if strategy == FallbackStrategy.TEXT_ANALYSIS:
                # Try text-based analysis instead of AST
                log_agent_event(
                    "fallback", "orchestrator",
                    f"Using text analysis fallback for {relation.id}"
                )
                try:
                    agent = AuditAgent(use_ast=False)
                    result = await agent.evaluate(relation)
                    redistributed.append((relation, result))
                    log_agent_event(
                        "fallback_success", "orchestrator",
                        f"Text analysis fallback succeeded for {relation.id}"
                    )
                except Exception as e:
                    log_agent_event(
                        "fallback_failed", "orchestrator",
                        f"Text analysis fallback failed for {relation.id}: {e}"
                    )

            elif strategy == FallbackStrategy.REDUCED_SCOPE:
                # Reduce scope - only evaluate critical rules
                log_agent_event(
                    "fallback", "orchestrator",
                    f"Using reduced scope for {relation.id}"
                )
                try:
                    agent = AuditAgent(critical_only=True)
                    result = await agent.evaluate(relation)
                    redistributed.append((relation, result))
                    log_agent_event(
                        "fallback_success", "orchestrator",
                        f"Reduced scope succeeded for {relation.id}"
                    )
                except Exception as e:
                    log_agent_event(
                        "fallback_failed", "orchestrator",
                        f"Reduced scope failed for {relation.id}: {e}"
                    )

        # Clear processed failures
        self._failed_relations = [
            (rel, err) for rel, err in self._failed_relations
            if rel not in [r for r, _ in redistributed]
        ]

        return redistributed

    def _determine_fallback_strategy(self, error: str) -> str:
        """Determine the appropriate fallback strategy based on error type.

        Args:
            error: The error message.

        Returns:
            Fallback strategy identifier.
        """
        error_lower = error.lower()

        if "syntax" in error_lower or "parse" in error_lower or "ast" in error_lower:
            return FallbackStrategy.TEXT_ANALYSIS

        if "timeout" in error_lower or "rate limit" in error_lower:
            return FallbackStrategy.REDUCED_SCOPE

        if "not found" in error_lower or "missing" in error_lower:
            return FallbackStrategy.SKIP_RULE

        # Default to text analysis as safest fallback
        return FallbackStrategy.TEXT_ANALYSIS

    async def _run_sequential(
        self,
        relations: list[AuditRelation],
    ) -> list[AuditRelation]:
        """Run audits sequentially with retry logic.

        Args:
            relations: The relations to audit.

        Returns:
            List of completed relations.
        """
        log_agent_event(
            "sequential", "orchestrator",
            f"Running {len(relations)} audits sequentially"
        )

        completed = []
        for relation in relations:
            try:
                result = await self._run_with_retry(relation)
                completed.append(result)
            except Exception as e:
                relation.fail(str(e))
                self._failed_relations.append((relation, str(e)))
                completed.append(relation)

        # Attempt redistribution for failed relations
        if self._failed_relations:
            redistributed = await self._attempt_redistribution()
            # Update completed relations with redistributed results
            for orig_rel, new_result in redistributed:
                for i, rel in enumerate(completed):
                    if rel.id == orig_rel.id:
                        completed[i] = new_result
                        break

        return completed

    def get_review_queue(self, result: AuditResult) -> list[Finding]:
        """Get findings that need human review.

        Args:
            result: The audit result.

        Returns:
            List of findings needing review.
        """
        review_queue = []
        for relation in result.relations:
            for finding in relation.findings:
                if finding.requires_human_review and not finding.is_reviewed:
                    review_queue.append(finding)
        return review_queue


def create_audit_orchestrator(
    parallel: bool = True,
    retry_config: RetryConfig | None = None,
) -> AuditOrchestrator:
    """Create an Audit Orchestrator instance.

    Args:
        parallel: Whether to run audits in parallel.
        retry_config: Configuration for retry behavior.

    Returns:
        Configured AuditOrchestrator.
    """
    return AuditOrchestrator(parallel=parallel, retry_config=retry_config)
