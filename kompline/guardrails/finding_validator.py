"""Finding validation guardrails."""

from dataclasses import dataclass
from typing import Any

from kompline.guardrails.evidence_validator import ValidationResult
from kompline.models import Finding, FindingStatus


class FindingValidator:
    """Validates findings for consistency and completeness."""

    def __init__(
        self,
        min_confidence: float = 0.0,
        max_confidence: float = 1.0,
        require_evidence_for_fail: bool = True,
        require_recommendation_for_fail: bool = True,
        min_reasoning_length: int = 10,
    ):
        """Initialize the validator.

        Args:
            min_confidence: Minimum allowed confidence.
            max_confidence: Maximum allowed confidence.
            require_evidence_for_fail: Whether FAIL findings need evidence.
            require_recommendation_for_fail: Whether FAIL findings need recommendations.
            min_reasoning_length: Minimum reasoning text length.
        """
        self.min_confidence = min_confidence
        self.max_confidence = max_confidence
        self.require_evidence_for_fail = require_evidence_for_fail
        self.require_recommendation_for_fail = require_recommendation_for_fail
        self.min_reasoning_length = min_reasoning_length

    def validate(self, finding: Finding) -> ValidationResult:
        """Validate a finding.

        Args:
            finding: The finding to validate.

        Returns:
            ValidationResult with any errors or warnings.
        """
        errors = []
        warnings = []

        # Check required fields
        if not finding.id:
            errors.append("Finding ID is required")

        if not finding.relation_id:
            errors.append("Relation ID is required")

        if not finding.rule_id:
            errors.append("Rule ID is required")

        # Check confidence bounds
        if finding.confidence < self.min_confidence:
            errors.append(f"Confidence {finding.confidence} is below minimum {self.min_confidence}")
        if finding.confidence > self.max_confidence:
            errors.append(f"Confidence {finding.confidence} exceeds maximum {self.max_confidence}")

        # Check reasoning
        if not finding.reasoning:
            errors.append("Finding reasoning is required")
        elif len(finding.reasoning) < self.min_reasoning_length:
            warnings.append(f"Finding reasoning is very short ({len(finding.reasoning)} chars)")

        # Status-specific validation
        status_result = self._validate_by_status(finding)
        errors.extend(status_result.errors)
        warnings.extend(status_result.warnings)

        # Consistency checks
        consistency_result = self._check_consistency(finding)
        errors.extend(consistency_result.errors)
        warnings.extend(consistency_result.warnings)

        if errors:
            return ValidationResult.invalid(errors, warnings)
        return ValidationResult.valid(warnings)

    def _validate_by_status(self, finding: Finding) -> ValidationResult:
        """Validate finding based on its status.

        Args:
            finding: The finding to validate.

        Returns:
            ValidationResult for status-specific checks.
        """
        errors = []
        warnings = []

        if finding.status == FindingStatus.FAIL:
            # FAIL findings should have evidence
            if self.require_evidence_for_fail and not finding.evidence_refs:
                errors.append("FAIL findings must have supporting evidence")

            # FAIL findings should have recommendations
            if self.require_recommendation_for_fail and not finding.recommendation:
                warnings.append("FAIL findings should include recommendations")

            # FAIL findings should trigger human review
            if not finding.requires_human_review:
                warnings.append("FAIL findings should require human review")

        elif finding.status == FindingStatus.REVIEW:
            # REVIEW findings must require human review
            if not finding.requires_human_review:
                errors.append("REVIEW findings must require human review")

        elif finding.status == FindingStatus.PASS:
            # PASS findings with low confidence should be REVIEW
            if finding.confidence < 0.7:
                warnings.append("PASS finding has low confidence, consider REVIEW status")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _check_consistency(self, finding: Finding) -> ValidationResult:
        """Check finding for internal consistency.

        Args:
            finding: The finding to check.

        Returns:
            ValidationResult for consistency checks.
        """
        warnings = []

        # High confidence should not have REVIEW status
        if finding.status == FindingStatus.REVIEW and finding.confidence > 0.9:
            warnings.append("REVIEW status with very high confidence is unusual")

        # Low confidence PASS is suspicious
        if finding.status == FindingStatus.PASS and finding.confidence < 0.5:
            warnings.append("PASS status with low confidence (<50%) is unusual")

        # Review requirements consistency
        if finding.requires_human_review and finding.is_reviewed:
            # Check review status is set
            if not finding.review_status:
                warnings.append("Reviewed finding should have review_status set")

        return ValidationResult.valid(warnings)

    def validate_findings(self, findings: list[Finding]) -> ValidationResult:
        """Validate a list of findings.

        Args:
            findings: The findings to validate.

        Returns:
            Aggregated validation result.
        """
        all_errors = []
        all_warnings = []

        if not findings:
            all_warnings.append("No findings to validate")

        for finding in findings:
            result = self.validate(finding)
            all_errors.extend(result.errors)
            all_warnings.extend(result.warnings)

        # Check for duplicate IDs
        ids = [f.id for f in findings]
        if len(ids) != len(set(ids)):
            all_errors.append("Duplicate finding IDs found")

        # Check for same rule evaluated differently
        rule_statuses: dict[str, list[FindingStatus]] = {}
        for f in findings:
            if f.rule_id not in rule_statuses:
                rule_statuses[f.rule_id] = []
            rule_statuses[f.rule_id].append(f.status)

        for rule_id, statuses in rule_statuses.items():
            unique_statuses = set(statuses)
            if len(unique_statuses) > 1:
                all_warnings.append(
                    f"Rule {rule_id} has inconsistent statuses: {unique_statuses}"
                )

        if all_errors:
            return ValidationResult.invalid(all_errors, all_warnings)
        return ValidationResult.valid(all_warnings)


def validate_finding(finding: Finding) -> ValidationResult:
    """Validate a finding using default settings.

    Args:
        finding: The finding to validate.

    Returns:
        ValidationResult.
    """
    validator = FindingValidator()
    return validator.validate(finding)


def validate_findings(findings: list[Finding]) -> ValidationResult:
    """Validate a list of findings using default settings.

    Args:
        findings: The findings to validate.

    Returns:
        ValidationResult.
    """
    validator = FindingValidator()
    return validator.validate_findings(findings)
