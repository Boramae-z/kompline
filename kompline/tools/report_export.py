"""Report generation and export tools."""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

try:
    from agents import function_tool
except ImportError:
    def function_tool(func=None, **kwargs):
        """Fallback decorator when agents SDK not installed."""
        def decorator(f):
            f.func = f
            return f
        if func is not None:
            return decorator(func)
        return decorator


@dataclass
class ComplianceCheckResult:
    """Result of a single compliance check."""

    rule_id: str
    rule_title: str
    status: str  # "PASS", "FAIL", "REVIEW"
    confidence: float
    evidence: list[str]
    recommendation: str | None = None


@dataclass
class ComplianceReport:
    """Full compliance report in 별지5 format."""

    report_id: str
    generated_at: str
    target_code: str
    summary: dict[str, int]  # status -> count
    checks: list[ComplianceCheckResult]
    overall_status: str
    auditor_notes: str | None = None


def _generate_report_id() -> str:
    """Generate unique report ID."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"KPL-{timestamp}"


@function_tool(strict_mode=False)
def generate_report(
    target_code: str,
    check_results: list[dict[str, Any]],
    auditor_notes: str | None = None,
) -> dict[str, Any]:
    """Generate a compliance report in 별지5 format.

    Args:
        target_code: The source code that was analyzed.
        check_results: List of compliance check results.
        auditor_notes: Optional notes from the auditor.

    Returns:
        Dictionary containing the generated report.
    """
    checks = []
    for result in check_results:
        checks.append(
            ComplianceCheckResult(
                rule_id=result.get("rule_id", "UNKNOWN"),
                rule_title=result.get("rule_title", ""),
                status=result.get("status", "REVIEW"),
                confidence=result.get("confidence", 0.0),
                evidence=result.get("evidence", []),
                recommendation=result.get("recommendation"),
            )
        )

    summary = {"PASS": 0, "FAIL": 0, "REVIEW": 0}
    for check in checks:
        if check.status in summary:
            summary[check.status] += 1

    if summary["FAIL"] > 0:
        overall_status = "NON_COMPLIANT"
    elif summary["REVIEW"] > 0:
        overall_status = "PENDING_REVIEW"
    else:
        overall_status = "COMPLIANT"

    report = ComplianceReport(
        report_id=_generate_report_id(),
        generated_at=datetime.now().isoformat(),
        target_code=target_code[:500] + "..." if len(target_code) > 500 else target_code,
        summary=summary,
        checks=checks,
        overall_status=overall_status,
        auditor_notes=auditor_notes,
    )

    return {
        "success": True,
        "report": {
            "report_id": report.report_id,
            "generated_at": report.generated_at,
            "target_code_preview": report.target_code,
            "summary": report.summary,
            "checks": [
                {
                    "rule_id": c.rule_id,
                    "rule_title": c.rule_title,
                    "status": c.status,
                    "confidence": c.confidence,
                    "evidence": c.evidence,
                    "recommendation": c.recommendation,
                }
                for c in report.checks
            ],
            "overall_status": report.overall_status,
            "auditor_notes": report.auditor_notes,
        },
    }


@function_tool(strict_mode=False)
def export_to_pdf(report: dict[str, Any], output_path: str) -> dict[str, Any]:
    """Export a compliance report to PDF format.

    Note: This is a placeholder that exports to JSON.
    Full PDF export requires additional dependencies.

    Args:
        report: The compliance report dictionary.
        output_path: Path to save the exported file.

    Returns:
        Dictionary with export status and file path.
    """
    json_path = output_path.replace(".pdf", ".json")

    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "format": "json",
            "path": json_path,
            "message": "Report exported as JSON (PDF export requires additional setup)",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


@function_tool(strict_mode=False)
def format_report_as_markdown(report: dict[str, Any]) -> str:
    """Format a compliance report as Markdown for display.

    Args:
        report: The compliance report dictionary.

    Returns:
        Markdown-formatted report string.
    """
    r = report.get("report", report)

    md = f"""# 알고리즘 공정성 자가평가서 (별지5)

## 기본 정보
- **보고서 ID**: {r.get('report_id', 'N/A')}
- **생성일시**: {r.get('generated_at', 'N/A')}
- **전체 상태**: {r.get('overall_status', 'N/A')}

## 요약
| 상태 | 건수 |
|------|------|
| PASS | {r.get('summary', {}).get('PASS', 0)} |
| FAIL | {r.get('summary', {}).get('FAIL', 0)} |
| REVIEW | {r.get('summary', {}).get('REVIEW', 0)} |

## 상세 점검 결과
"""

    for check in r.get("checks", []):
        status_emoji = {"PASS": "✅", "FAIL": "❌", "REVIEW": "⚠️"}.get(check["status"], "❓")
        md += f"""
### {status_emoji} {check.get('rule_id', '')} - {check.get('rule_title', '')}
- **상태**: {check.get('status', '')}
- **신뢰도**: {check.get('confidence', 0):.1%}
- **근거**:
"""
        for evidence in check.get("evidence", []):
            md += f"  - {evidence}\n"

        if check.get("recommendation"):
            md += f"- **권고사항**: {check['recommendation']}\n"

    if r.get("auditor_notes"):
        md += f"""
## 감사자 의견
{r['auditor_notes']}
"""

    md += f"""
---
*본 보고서는 Kompline 시스템에 의해 자동 생성되었습니다.*
"""

    return md
