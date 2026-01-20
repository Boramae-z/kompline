"""Output guardrails for quality checking compliance results."""

from dataclasses import dataclass
from typing import Any

from agents import output_guardrail, GuardrailFunctionOutput


@dataclass
class QualityCheckResult:
    """Result of output quality check."""

    passed: bool
    issues: list[str]
    suggestions: list[str]
    score: float  # 0.0 to 1.0


def check_compliance_output_quality(output: dict[str, Any]) -> QualityCheckResult:
    """Check the quality of compliance check output.

    Args:
        output: The compliance check output dictionary.

    Returns:
        QualityCheckResult with quality assessment.
    """
    issues = []
    suggestions = []
    score = 1.0

    # Check for required fields
    required_fields = ["rule_id", "status", "confidence", "evidence"]
    for field in required_fields:
        if field not in output:
            issues.append(f"Missing required field: {field}")
            score -= 0.2

    # Check status value
    valid_statuses = {"PASS", "FAIL", "REVIEW"}
    if output.get("status") not in valid_statuses:
        issues.append(f"Invalid status: {output.get('status')}")
        score -= 0.15

    # Check confidence range
    confidence = output.get("confidence", 0)
    if not isinstance(confidence, (int, float)):
        issues.append("Confidence must be a number")
        score -= 0.1
    elif not 0 <= confidence <= 1:
        issues.append("Confidence must be between 0 and 1")
        score -= 0.1

    # Check evidence quality
    evidence = output.get("evidence", [])
    if not evidence:
        issues.append("No evidence provided")
        score -= 0.2
    elif len(evidence) < 2:
        suggestions.append("Consider providing more evidence points")
        score -= 0.05

    # Check for FAIL without recommendation
    if output.get("status") == "FAIL" and not output.get("recommendation"):
        issues.append("FAIL status requires a recommendation")
        score -= 0.15

    # Check for low confidence without explanation
    if confidence < 0.7 and not output.get("notes"):
        suggestions.append("Low confidence results should include explanatory notes")

    # Ensure score is in valid range
    score = max(0.0, min(1.0, score))

    return QualityCheckResult(
        passed=len(issues) == 0,
        issues=issues,
        suggestions=suggestions,
        score=score,
    )


def check_report_output_quality(report: dict[str, Any]) -> QualityCheckResult:
    """Check the quality of a generated report.

    Args:
        report: The compliance report dictionary.

    Returns:
        QualityCheckResult with quality assessment.
    """
    issues = []
    suggestions = []
    score = 1.0

    # Check for required report fields
    required_fields = ["report_id", "generated_at", "summary", "checks", "overall_status"]
    for field in required_fields:
        if field not in report:
            issues.append(f"Missing required report field: {field}")
            score -= 0.15

    # Check summary structure
    summary = report.get("summary", {})
    expected_keys = {"PASS", "FAIL", "REVIEW"}
    if not all(k in summary for k in expected_keys):
        issues.append("Summary must include PASS, FAIL, and REVIEW counts")
        score -= 0.1

    # Check that checks is a list with content
    checks = report.get("checks", [])
    if not isinstance(checks, list):
        issues.append("Checks must be a list")
        score -= 0.2
    elif not checks:
        suggestions.append("Report has no compliance checks")
        score -= 0.05

    # Validate each check in the report
    for i, check in enumerate(checks):
        check_result = check_compliance_output_quality(check)
        if not check_result.passed:
            for issue in check_result.issues:
                issues.append(f"Check {i+1}: {issue}")
            score -= 0.05

    # Check overall status consistency
    overall = report.get("overall_status")
    valid_overall = {"COMPLIANT", "NON_COMPLIANT", "PENDING_REVIEW"}
    if overall not in valid_overall:
        issues.append(f"Invalid overall status: {overall}")
        score -= 0.1

    # Verify summary matches checks
    if checks:
        calculated_summary = {"PASS": 0, "FAIL": 0, "REVIEW": 0}
        for check in checks:
            status = check.get("status", "REVIEW")
            if status in calculated_summary:
                calculated_summary[status] += 1

        if summary != calculated_summary:
            issues.append("Summary counts don't match actual check results")
            score -= 0.1

    score = max(0.0, min(1.0, score))

    return QualityCheckResult(
        passed=len(issues) == 0,
        issues=issues,
        suggestions=suggestions,
        score=score,
    )


def _passthrough_output(output_type: str) -> GuardrailFunctionOutput:
    """Return a passthrough result for unrecognized output types."""
    return GuardrailFunctionOutput(
        output_info={"type": output_type, "passed": True},
        tripwire_triggered=False,
    )


@output_guardrail
async def quality_check_guardrail(
    ctx,
    agent,
    output: Any,
) -> GuardrailFunctionOutput:
    """Guardrail to validate output quality.

    Args:
        ctx: The run context.
        agent: The agent producing the output.
        output: The output to validate.

    Returns:
        GuardrailFunctionOutput indicating whether the output is acceptable.
    """
    if not isinstance(output, dict):
        return _passthrough_output("non_dict")

    # Determine output type and validate accordingly
    is_report = "report_id" in output or "report" in output
    is_compliance_check = "rule_id" in output or "status" in output

    if is_report:
        report = output.get("report", output)
        result = check_report_output_quality(report)
    elif is_compliance_check:
        result = check_compliance_output_quality(output)
    else:
        return _passthrough_output("unknown")

    return GuardrailFunctionOutput(
        output_info={
            "passed": result.passed,
            "score": result.score,
            "issues": result.issues,
            "suggestions": result.suggestions,
        },
        tripwire_triggered=result.score < 0.5,
    )


# Alias for import
QualityCheckGuardrail = quality_check_guardrail
