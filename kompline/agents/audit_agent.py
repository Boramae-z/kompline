"""Audit Agent for per-relation compliance evaluation."""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agents import Agent

from kompline.agents.readers.base_reader import get_reader_for_artifact
from kompline.models import (
    AuditRelation,
    Compliance,
    Artifact,
    Evidence,
    EvidenceCollection,
    Finding,
    FindingStatus,
    Provenance,
    RunConfig,
)
from kompline.registry import get_artifact_registry, get_compliance_registry
from kompline.tracing.logger import log_agent_event


AUDIT_AGENT_INSTRUCTIONS = """You are the Audit Agent for Kompline compliance verification.

Your role is to evaluate a single (Compliance, Artifact) relation.

## Process

1. **Understand the Compliance**: Review all rules and evidence requirements
2. **Plan Evidence Collection**: Determine what evidence is needed from the artifact
3. **Collect Evidence**: Use Reader agents to extract relevant evidence
4. **Evaluate Rules**: For each rule, assess compliance based on evidence
5. **Generate Findings**: Create findings with status, confidence, and reasoning

## Evidence Requirements

For each rule, you need sufficient evidence to make a judgment:
- Code snippets showing relevant logic
- Configuration values
- Documentation excerpts

## Finding Status

- **PASS**: Evidence clearly shows compliance
- **FAIL**: Evidence clearly shows violation
- **REVIEW**: Uncertain, needs human review
- **NOT_APPLICABLE**: Rule doesn't apply to this artifact

## Confidence Scoring

Score your confidence (0.0 to 1.0):
- 0.9-1.0: Very confident, clear evidence
- 0.7-0.89: Confident with minor uncertainty
- 0.5-0.69: Uncertain, recommend review
- Below 0.5: Low confidence, needs human review

## Human Review Triggers

Request human review when:
1. Confidence < 0.7
2. New pattern not covered by rules
3. Any FAIL judgment (for confirmation)
4. Conflicting evidence found
"""


class AuditAgent:
    """Agent for evaluating a single (Compliance, Artifact) relation.

    This agent is responsible for:
    1. Collecting evidence from the artifact using appropriate readers
    2. Evaluating each rule in the compliance against collected evidence
    3. Generating findings with status, confidence, and reasoning
    """

    def __init__(
        self,
        use_ast: bool = True,
        critical_only: bool = False,
    ):
        """Initialize the audit agent.

        Args:
            use_ast: Whether to use AST parsing (disable for text-only fallback).
            critical_only: Whether to only evaluate critical rules (reduced scope).
        """
        self.name = "AuditAgent"
        self.use_ast = use_ast
        self.critical_only = critical_only
        self._agent: "Agent | None" = None
        self._llm_agent: "Agent | None" = None
        self._llm_model: str | None = None
        self._current_run_config: RunConfig | None = None

    @property
    def agent(self) -> "Agent":
        """Get or create the underlying agent."""
        if self._agent is None:
            self._agent = self._create_agent()
            log_agent_event("init", "audit_agent", "Audit Agent initialized")
        return self._agent

    def _create_agent(self) -> "Agent":
        """Create the underlying Agent instance."""
        from agents import Agent
        return Agent(
            name=self.name,
            instructions=AUDIT_AGENT_INSTRUCTIONS,
            tools=[],  # Tools will be added dynamically based on readers
        )

    async def evaluate(self, relation: AuditRelation) -> AuditRelation:
        """Evaluate a compliance-artifact relation.

        Args:
            relation: The audit relation to evaluate.

        Returns:
            Updated relation with evidence and findings.
        """
        log_agent_event("start", "audit_agent", f"Starting audit for relation {relation.id}")
        relation.start()

        try:
            # Get compliance and artifact
            compliance_registry = get_compliance_registry()
            artifact_registry = get_artifact_registry()

            compliance = compliance_registry.get(relation.compliance_id)
            artifact = artifact_registry.get(relation.artifact_id)

            if not compliance:
                relation.fail(f"Compliance '{relation.compliance_id}' not found")
                return relation

            if not artifact:
                relation.fail(f"Artifact '{relation.artifact_id}' not found")
                return relation

            # Collect evidence
            evidence_collection = await self._collect_evidence(
                compliance, artifact, relation.id
            )

            for evidence in evidence_collection:
                relation.add_evidence(evidence)

            # Filter rules if critical_only mode
            rules_to_evaluate = compliance.rules
            if self.critical_only:
                from kompline.models import RuleSeverity
                rules_to_evaluate = [
                    r for r in compliance.rules
                    if r.severity in (RuleSeverity.CRITICAL, RuleSeverity.HIGH)
                ]
                log_agent_event(
                    "reduced_scope", "audit_agent",
                    f"Critical-only mode: evaluating {len(rules_to_evaluate)}/{len(compliance.rules)} rules"
                )

            # Evaluate rules (LLM-assisted when enabled)
            self._current_run_config = relation.run_config
            findings = []
            if self._should_use_llm(relation.run_config):
                findings = await self._llm_evaluate_all_rules(
                    compliance, evidence_collection, relation.id
                )

            # Fallback to heuristic for missing or failed LLM results
            if not findings:
                for rule in rules_to_evaluate:
                    findings.append(
                        await self._evaluate_rule(
                            rule, evidence_collection, relation.id
                        )
                    )
            else:
                # Ensure every rule has a finding
                existing = {f.rule_id for f in findings}
                for rule in rules_to_evaluate:
                    if rule.id not in existing:
                        findings.append(
                            await self._evaluate_rule(
                                rule, evidence_collection, relation.id
                            )
                        )

            for finding in findings:
                relation.add_finding(finding)

            relation.complete()
            log_agent_event(
                "complete", "audit_agent",
                f"Completed audit for relation {relation.id}: "
                f"{len(relation.findings)} findings"
            )

        except Exception as e:
            relation.fail(str(e))
            log_agent_event("error", "audit_agent", f"Audit failed: {e}")

        return relation

    def _should_use_llm(self, run_config: RunConfig) -> bool:
        """Decide whether to use LLM evaluation."""
        if run_config.metadata.get("use_llm") is not None:
            return bool(run_config.metadata.get("use_llm"))
        return run_config.use_llm

    def _get_llm_agent(self) -> "Agent":
        """Create (or reuse) the LLM evaluation agent."""
        model = None
        if self._current_run_config:
            model = self._current_run_config.llm_model
        if self._llm_agent is None or model != self._llm_model:
            from agents import Agent
            kwargs = {"model": model} if model else {}
            self._llm_agent = Agent(
                name="AuditLLMEvaluator",
                instructions=(
                    "You are an audit evaluator. Output JSON only.\n"
                    "Return an object: {\"findings\": [ ... ]}.\n"
                    "Each finding: rule_id, status (pass|fail|review|not_applicable), "
                    "confidence (0-1), reasoning, recommendation (optional), "
                    "evidence_ids (list of evidence IDs).\n"
                    "Only use evidence_ids from the provided evidence list."
                ),
                **kwargs,
            )
            self._llm_model = model
        return self._llm_agent

    async def _llm_evaluate_all_rules(
        self,
        compliance: Compliance,
        evidence: EvidenceCollection,
        relation_id: str,
    ) -> list[Finding]:
        """Evaluate all rules using LLM, returning findings list."""
        try:
            from agents import Runner
            from kompline.utils import extract_json
            import uuid

            rules_payload = [
                {
                    "rule_id": r.id,
                    "title": r.title,
                    "description": r.description,
                    "check_points": r.check_points,
                    "pass_criteria": r.pass_criteria,
                    "fail_examples": r.fail_examples,
                }
                for r in compliance.rules
            ]

            evidence_payload = [
                {
                    "id": ev.id,
                    "type": ev.type.value,
                    "source": ev.source,
                    "location": ev.location_str,
                    "content": ev.content[:400],
                    "metadata": ev.metadata,
                }
                for ev in evidence
            ]

            prompt = (
                "Evaluate the compliance rules using the evidence.\n\n"
                f"COMPLIANCE: {compliance.id} - {compliance.name}\n"
                f"RULES: {rules_payload}\n\n"
                f"EVIDENCE: {evidence_payload}\n\n"
                "Return JSON only."
            )

            result = await Runner.run(self._get_llm_agent(), prompt)
            payload = extract_json(result.final_output)
            if not payload:
                return []

            findings_raw = payload.get("findings") if isinstance(payload, dict) else payload
            if not isinstance(findings_raw, list):
                return []

            rule_ids = {r.id for r in compliance.rules}
            evidence_ids = {ev.id for ev in evidence}
            findings: list[Finding] = []

            for item in findings_raw:
                rule_id = str(item.get("rule_id", "")).strip()
                if not rule_id or rule_id not in rule_ids:
                    continue

                status_raw = str(item.get("status", "review")).lower()
                status_map = {
                    "pass": FindingStatus.PASS,
                    "fail": FindingStatus.FAIL,
                    "review": FindingStatus.REVIEW,
                    "not_applicable": FindingStatus.NOT_APPLICABLE,
                }
                status = status_map.get(status_raw, FindingStatus.REVIEW)

                confidence = item.get("confidence", 0.6)
                try:
                    confidence = float(confidence)
                except Exception:
                    confidence = 0.6
                confidence = max(0.0, min(1.0, confidence))

                evidence_refs = [
                    ev_id for ev_id in item.get("evidence_ids", []) if ev_id in evidence_ids
                ]

                reasoning = str(item.get("reasoning", "")).strip() or "LLM evaluation"
                recommendation = item.get("recommendation")

                finding = Finding(
                    id=f"find-{uuid.uuid4().hex[:8]}",
                    relation_id=relation_id,
                    rule_id=rule_id,
                    status=status,
                    confidence=confidence,
                    evidence_refs=evidence_refs,
                    reasoning=reasoning,
                    recommendation=recommendation,
                )
                findings.append(finding)

            return findings
        except Exception as e:
            log_agent_event("warning", "audit_agent", f"LLM evaluation failed: {e}")
            return []

    async def _collect_evidence(
        self,
        compliance: Compliance,
        artifact: Artifact,
        relation_id: str,
    ) -> EvidenceCollection:
        """Collect evidence from artifact based on compliance requirements.

        Args:
            compliance: The compliance framework with requirements.
            artifact: The artifact to extract evidence from.
            relation_id: The relation ID for tracking.

        Returns:
            Collection of extracted evidence.
        """
        reader = get_reader_for_artifact(artifact)
        if not reader:
            log_agent_event(
                "warning", "audit_agent",
                f"No reader found for artifact type {artifact.type}"
            )
            return EvidenceCollection(relation_id=relation_id)

        # Configure reader based on agent settings
        if hasattr(reader, 'use_ast'):
            reader.use_ast = self.use_ast

        # Collect all evidence requirements from compliance and rules
        all_requirements = list(compliance.evidence_requirements)
        for rule in compliance.rules:
            all_requirements.extend(rule.evidence_requirements)

        try:
            evidence = await reader.extract_evidence(
                artifact, all_requirements, relation_id
            )
        except Exception as e:
            # If AST parsing fails and we're using AST, try text-only fallback
            if self.use_ast and "parse" in str(e).lower():
                log_agent_event(
                    "fallback", "audit_agent",
                    f"AST parsing failed, trying text-only extraction: {e}"
                )
                if hasattr(reader, 'use_ast'):
                    reader.use_ast = False
                evidence = await reader.extract_evidence(
                    artifact, all_requirements, relation_id
                )
            else:
                raise

        log_agent_event(
            "evidence", "audit_agent",
            f"Collected {len(evidence)} evidence items from {artifact.name}"
        )

        return evidence

    async def _evaluate_rule(
        self,
        rule: Any,  # Rule type
        evidence: EvidenceCollection,
        relation_id: str,
    ) -> Finding:
        """Evaluate a single rule against collected evidence.

        Args:
            rule: The rule to evaluate.
            evidence: Collected evidence.
            relation_id: The relation ID.

        Returns:
            Finding with evaluation result.
        """
        import uuid

        # Get evidence relevant to this rule
        relevant_evidence = evidence.get_by_rule(rule.id)

        # If no specific evidence, use all evidence
        if not relevant_evidence:
            relevant_evidence = list(evidence)

        # Simple heuristic evaluation (can be enhanced with LLM)
        status, confidence, reasoning = self._heuristic_evaluate(rule, relevant_evidence)

        # Check for HITL triggers
        requires_review = (
            status == FindingStatus.FAIL or
            status == FindingStatus.REVIEW or
            confidence < 0.7
        )

        recommendation = None
        if status == FindingStatus.FAIL:
            recommendation = f"Review and address: {rule.title}"

        finding = Finding(
            id=f"find-{uuid.uuid4().hex[:8]}",
            relation_id=relation_id,
            rule_id=rule.id,
            status=status,
            confidence=confidence,
            evidence_refs=[e.id for e in relevant_evidence],
            reasoning=reasoning,
            recommendation=recommendation,
            requires_human_review=requires_review,
        )

        return finding

    def _heuristic_evaluate(
        self,
        rule: Any,
        evidence: list[Evidence],
    ) -> tuple[FindingStatus, float, str]:
        """Simple heuristic rule evaluation.

        Args:
            rule: The rule to evaluate.
            evidence: List of evidence items.

        Returns:
            Tuple of (status, confidence, reasoning).
        """
        if not evidence:
            return (
                FindingStatus.REVIEW,
                0.5,
                "Insufficient evidence to evaluate this rule"
            )

        # Check for issues in evidence metadata
        issues_found = []
        patterns_found = []

        for ev in evidence:
            metadata = ev.metadata or {}
            if metadata.get("is_issue"):
                issues_found.append(ev.content)
            if metadata.get("pattern"):
                patterns_found.append(metadata["pattern"])
            if metadata.get("category") == "potential_bias":
                issues_found.append(ev.content)

        # Determine status based on findings
        if issues_found:
            return (
                FindingStatus.FAIL,
                0.85,
                f"Issues detected: {'; '.join(issues_found[:3])}"
            )

        # Check rule check_points against patterns
        if hasattr(rule, 'check_points'):
            covered_points = 0
            for check_point in rule.check_points:
                check_lower = check_point.lower()
                for ev in evidence:
                    if any(word in ev.content.lower() for word in check_lower.split()):
                        covered_points += 1
                        break

            coverage = covered_points / len(rule.check_points) if rule.check_points else 1.0

            if coverage >= 0.8:
                return (
                    FindingStatus.PASS,
                    0.8 + (coverage * 0.15),
                    f"Evidence covers {covered_points}/{len(rule.check_points)} check points"
                )
            elif coverage >= 0.5:
                return (
                    FindingStatus.REVIEW,
                    0.6 + (coverage * 0.1),
                    f"Partial coverage: {covered_points}/{len(rule.check_points)} check points"
                )

        # Default to review if uncertain
        return (
            FindingStatus.REVIEW,
            0.6,
            "Evidence found but requires human review for final judgment"
        )


def create_audit_agent() -> AuditAgent:
    """Create an Audit Agent instance."""
    return AuditAgent()
