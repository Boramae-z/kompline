"""Report Generator Agent - Template-based compliance report generation."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agents import Agent

from kompline.agents.audit_orchestrator import AuditResult
from kompline.models import AuditRelation, Finding, FindingStatus, FindingSummary
from kompline.registry import get_compliance_registry
from kompline.tools.report_export import (
    export_to_pdf,
    format_report_as_markdown,
    generate_report,
)
from kompline.tracing.logger import log_agent_event


class ReportFormat(str, Enum):
    """Output format for reports."""

    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    JSON = "json"


@dataclass
class ReportTemplate:
    """Template for generating compliance reports."""

    id: str  # e.g., "byeolji5", "soc2", "internal"
    name: str  # e.g., "별지5 자가평가서"
    description: str
    sections: list[str]  # Section IDs to include
    language: str = "ko"  # Primary language: "ko", "en"
    include_evidence: bool = True
    include_recommendations: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)


# Built-in report templates
BYEOLJI5_TEMPLATE = ReportTemplate(
    id="byeolji5",
    name="별지5 알고리즘 자가평가서",
    description="Korean financial regulation algorithm fairness self-assessment",
    sections=[
        "basic_info",
        "summary",
        "detailed_results",
        "evidence_references",
        "auditor_notes",
    ],
    language="ko",
    include_evidence=True,
    include_recommendations=True,
)

INTERNAL_TEMPLATE = ReportTemplate(
    id="internal",
    name="Internal Compliance Report",
    description="Internal compliance audit report",
    sections=[
        "basic_info",
        "summary",
        "detailed_results",
        "recommendations",
    ],
    language="en",
    include_evidence=True,
    include_recommendations=True,
)


REPORT_GENERATOR_INSTRUCTIONS = """You are the Report Generator Agent for Kompline.

Your role is to generate compliance reports in various formats based on templates.

## Available Templates

1. **별지5 (byeolji5)**: Korean financial regulation self-assessment
2. **Internal**: Standard internal audit report

## Report Structure

### 1. 기본 정보 (Basic Information)
- Report ID, generated timestamp
- Compliance frameworks evaluated
- Artifacts audited

### 2. 요약 (Summary)
- Overall compliance status
- Count by status (PASS/FAIL/REVIEW)
- Key findings

### 3. 상세 점검 결과 (Detailed Check Results)
For each finding:
- Rule ID and title
- Status (PASS/FAIL/REVIEW)
- Confidence score
- Evidence citations
- Recommendations

### 4. 감사자 의견 (Auditor Notes)
- Human review results
- Additional context

## Output Guidelines

1. Be precise and formal (regulatory document)
2. Include all evidence supporting judgments
3. For FAIL items, include remediation steps
4. For REVIEW items, explain why review needed
5. Support both Korean and English
"""


@dataclass
class ComplianceReport:
    """Generated compliance report."""

    id: str
    template_id: str
    generated_at: datetime
    compliance_ids: list[str]
    artifact_ids: list[str]
    summary: FindingSummary
    findings: list[Finding]
    evidence_refs: dict[str, str]  # evidence_id -> citation
    is_compliant: bool
    needs_review: bool
    content: dict[str, Any] = field(default_factory=dict)  # Rendered sections

    def to_markdown(self) -> str:
        """Render report as Markdown."""
        lines = []

        # Header
        lines.append(f"# Compliance Report: {self.id}")
        lines.append(f"Generated: {self.generated_at.isoformat()}")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append(f"- **Status**: {'Compliant' if self.is_compliant else 'Non-Compliant'}")
        lines.append(f"- **Total Findings**: {self.summary.total}")
        lines.append(f"- **Passed**: {self.summary.passed}")
        lines.append(f"- **Failed**: {self.summary.failed}")
        lines.append(f"- **Pending Review**: {self.summary.review}")
        lines.append(f"- **Confidence**: {self.summary.avg_confidence:.1%}")
        lines.append("")

        # Findings
        lines.append("## Detailed Findings")
        for finding in self.findings:
            status_emoji = {
                FindingStatus.PASS: "✅",
                FindingStatus.FAIL: "❌",
                FindingStatus.REVIEW: "🔍",
                FindingStatus.NOT_APPLICABLE: "➖",
            }.get(finding.status, "❓")

            lines.append(f"### {status_emoji} {finding.rule_id}")
            lines.append(f"- **Status**: {finding.status.value.upper()}")
            lines.append(f"- **Confidence**: {finding.confidence:.1%}")
            lines.append(f"- **Reasoning**: {finding.reasoning}")

            # Include citations for traceability
            if finding.citations:
                lines.append("- **Citations**:")
                for citation in finding.citations:
                    lines.append(f"  - [{citation.source}] {citation.text[:100]}...")

            if finding.recommendation:
                lines.append(f"- **Recommendation**: {finding.recommendation}")
            if finding.requires_human_review:
                lines.append("- ⚠️ **Requires Human Review**")
            lines.append("")

        # Evidence References
        if self.evidence_refs:
            lines.append("## Evidence References")
            for ev_id, citation in self.evidence_refs.items():
                lines.append(f"- `{ev_id}`: {citation}")
            lines.append("")

        return "\n".join(lines)


class ReportGenerator:
    """Generator for compliance reports."""

    def __init__(self):
        """Initialize the report generator."""
        self.name = "ReportGenerator"
        self._templates: dict[str, ReportTemplate] = {
            "byeolji5": BYEOLJI5_TEMPLATE,
            "internal": INTERNAL_TEMPLATE,
        }
        self._agent: "Agent | None" = None

    def register_template(self, template: ReportTemplate) -> None:
        """Register a custom report template."""
        self._templates[template.id] = template

    def get_template(self, template_id: str) -> ReportTemplate | None:
        """Get a template by ID."""
        return self._templates.get(template_id)

    @property
    def agent(self) -> "Agent":
        """Get or create the underlying agent."""
        if self._agent is None:
            self._agent = self._create_agent()
            log_agent_event("init", "report_generator", "Report Generator initialized")
        return self._agent

    def _create_agent(self) -> "Agent":
        """Create the underlying Agent instance."""
        from agents import Agent
        return Agent(
            name=self.name,
            instructions=REPORT_GENERATOR_INSTRUCTIONS,
            tools=[generate_report, export_to_pdf, format_report_as_markdown],
        )

    def generate(
        self,
        audit_result: AuditResult,
        template_id: str = "byeolji5",
    ) -> ComplianceReport:
        """Generate a compliance report from audit results.

        Args:
            audit_result: The audit result to report on.
            template_id: The template to use.

        Returns:
            Generated ComplianceReport.
        """
        import uuid

        template = self.get_template(template_id)
        if not template:
            template = BYEOLJI5_TEMPLATE

        # Collect all findings
        all_findings = []
        evidence_refs = {}
        compliance_ids = set()
        artifact_ids = set()

        for relation in audit_result.relations:
            compliance_ids.add(relation.compliance_id)
            artifact_ids.add(relation.artifact_id)
            all_findings.extend(relation.findings)

            # Collect evidence citations
            for ev in relation.evidence_collected:
                evidence_refs[ev.id] = ev.to_citation()

        # Calculate combined summary
        combined_summary = FindingSummary.from_findings("combined", all_findings)

        report = ComplianceReport(
            id=f"report-{uuid.uuid4().hex[:8]}",
            template_id=template_id,
            generated_at=datetime.now(),
            compliance_ids=list(compliance_ids),
            artifact_ids=list(artifact_ids),
            summary=combined_summary,
            findings=all_findings,
            evidence_refs=evidence_refs,
            is_compliant=audit_result.is_compliant,
            needs_review=audit_result.needs_review,
        )

        log_agent_event(
            "generate", "report_generator",
            f"Generated report {report.id} with {len(all_findings)} findings"
        )

        return report

    def generate_byeolji5(self, audit_result: AuditResult) -> str:
        """Generate 별지5 format report.

        Args:
            audit_result: The audit result.

        Returns:
            Formatted report string in 별지5 format.
        """
        report = self.generate(audit_result, "byeolji5")

        lines = []
        lines.append("=" * 60)
        lines.append("별지5. 알고리즘 자가평가서")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"보고서 ID: {report.id}")
        lines.append(f"생성일시: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        lines.append("-" * 40)
        lines.append("1. 평가 요약")
        lines.append("-" * 40)
        status_kr = "적합" if report.is_compliant else "부적합"
        lines.append(f"  - 종합 판정: {status_kr}")
        lines.append(f"  - 총 점검 항목: {report.summary.total}개")
        lines.append(f"  - 적합: {report.summary.passed}개")
        lines.append(f"  - 부적합: {report.summary.failed}개")
        lines.append(f"  - 검토 필요: {report.summary.review}개")
        lines.append(f"  - 평균 신뢰도: {report.summary.avg_confidence:.1%}")
        lines.append("")

        lines.append("-" * 40)
        lines.append("2. 상세 점검 결과")
        lines.append("-" * 40)

        for i, finding in enumerate(report.findings, 1):
            status_kr = {
                FindingStatus.PASS: "적합",
                FindingStatus.FAIL: "부적합",
                FindingStatus.REVIEW: "검토필요",
                FindingStatus.NOT_APPLICABLE: "해당없음",
            }.get(finding.status, "미정")

            lines.append(f"\n[{i}] {finding.rule_id}")
            lines.append(f"    판정: {status_kr} (신뢰도: {finding.confidence:.1%})")
            lines.append(f"    근거: {finding.reasoning}")

            # Include citations for traceability
            if finding.citations:
                lines.append("    출처:")
                for citation in finding.citations:
                    source = citation.source
                    text = citation.text[:80] + "..." if len(citation.text) > 80 else citation.text
                    lines.append(f"      - [{source}] {text}")

            if finding.recommendation:
                lines.append(f"    권고: {finding.recommendation}")
            if finding.requires_human_review:
                lines.append("    ※ 감사자 검토 필요")

        lines.append("")
        lines.append("=" * 60)
        lines.append("끝")
        lines.append("=" * 60)

        return "\n".join(lines)


def create_report_generator() -> ReportGenerator:
    """Create a ReportGenerator instance."""
    return ReportGenerator()


# Legacy function for backward compatibility
def create_report_generator_agent() -> "Agent":
    """Create the Report Generator Agent (legacy).

    Returns:
        Configured Report Generator Agent.
    """
    return create_report_generator().agent


# Create default instance (legacy)
try:
    report_generator_agent = create_report_generator_agent()
except ImportError:
    report_generator_agent = None
