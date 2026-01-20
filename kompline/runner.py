"""Main runner for Kompline compliance analysis."""

from __future__ import annotations

import argparse
import asyncio
import tempfile
from pathlib import Path
from typing import Any

from kompline.agents.audit_orchestrator import create_audit_orchestrator
from kompline.agents.report_generator import create_report_generator
from kompline.demo_data import resolve_compliance_ids, register_file_artifact
from kompline.guardrails.input_validator import validate_python_source
from kompline.models import Finding, RunConfig
from kompline.tracing.logger import setup_tracing, log_agent_event, get_tracer

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


class KomplineRunner:
    """Main runner for the Kompline compliance analysis system."""

    def __init__(self, tracing_enabled: bool = True, parallel: bool = True):
        """Initialize the Kompline runner.

        Args:
            tracing_enabled: Whether to enable tracing/logging.
            parallel: Whether to run relations in parallel.
        """
        if tracing_enabled:
            setup_tracing()

        self.orchestrator = create_audit_orchestrator(parallel=parallel)
        self.report_generator = create_report_generator()

        log_agent_event("init", "runner", "Kompline Runner initialized")

    async def analyze(
        self,
        source_code: str | None = None,
        artifact_path: str | None = None,
        compliance_ids: list[str] | None = None,
        use_llm: bool = True,
        require_review: bool = True,
    ) -> dict[str, Any]:
        """Run compliance analysis on source code.

        Args:
            source_code: Optional Python source code to analyze.
            artifact_path: Optional path to a code artifact.
            compliance_ids: Optional list of compliance IDs to audit against.
            use_llm: Whether to use LLM evaluation (falls back if unavailable).
            require_review: Whether to require human review for uncertain results.

        Returns:
            Dictionary containing analysis results and report.
        """
        if not source_code and not artifact_path:
            return {
                "success": False,
                "error": "Either source_code or artifact_path must be provided",
            }

        temp_path: Path | None = None
        if source_code:
            validation = validate_python_source(source_code)
            if not validation.valid:
                return {
                    "success": False,
                    "error": "Invalid source code",
                    "details": validation.errors,
                }

            log_agent_event(
                "validation",
                "runner",
                "Input validation passed",
                {"warnings": validation.warnings},
            )

            temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
            temp_file.write(source_code)
            temp_file.close()
            temp_path = Path(temp_file.name)
            artifact_path = str(temp_path)

        if not artifact_path:
            return {
                "success": False,
                "error": "Artifact path could not be resolved",
            }

        log_agent_event(
            "start",
            "runner",
            "Starting compliance analysis",
            {"artifact_path": artifact_path},
        )

        try:
            compliance_ids = resolve_compliance_ids(compliance_ids)
            artifact_id = register_file_artifact(
                artifact_path,
                artifact_id="inline-code" if temp_path else None,
            )

            run_config = RunConfig(
                use_llm=use_llm,
                require_human_review_on_fail=require_review,
            )

            result = await self.orchestrator.audit(
                compliance_ids=compliance_ids,
                artifact_ids=[artifact_id],
                run_config=run_config,
            )

            report = self.report_generator.generate(result)
            report_markdown = report.to_markdown()

            output = {
                "success": True,
                "result": _serialize_audit_result(result),
                "report": _serialize_report(report),
                "report_markdown": report_markdown,
            }

            log_agent_event(
                "complete",
                "runner",
                "Analysis complete",
                {"success": True},
            )
        finally:
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass

        return output

    def get_trace(self) -> list[dict[str, Any]]:
        """Get the trace of events from this run."""
        return get_tracer().get_events()


async def run_analysis(source_code: str) -> dict[str, Any]:
    """Convenience function to run compliance analysis.

    Args:
        source_code: The Python source code to analyze.

    Returns:
        Analysis results dictionary.
    """
    runner = KomplineRunner()
    return await runner.analyze(source_code)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Kompline compliance analyzer")
    parser.add_argument("source", help="Path to the source code file to analyze")
    parser.add_argument(
        "--compliance",
        action="append",
        dest="compliance_ids",
        help="Compliance ID to apply (repeatable)",
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable LLM evaluation (use heuristic only)",
    )
    parser.add_argument(
        "--no-review",
        action="store_true",
        help="Disable human review requirement on FAIL/low confidence",
    )
    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.exists():
        print(f"Error: File not found: {source_path}")
        raise SystemExit(1)

    runner = KomplineRunner()
    result = asyncio.run(
        runner.analyze(
            artifact_path=str(source_path),
            compliance_ids=args.compliance_ids,
            use_llm=not args.no_llm,
            require_review=not args.no_review,
        )
    )

    if result.get("success"):
        summary = result.get("result", {})
        print("Analysis complete!")
        print(
            f"Findings: {summary.get('total_findings', 0)}, "
            f"Pass: {summary.get('total_passed', 0)}, "
            f"Fail: {summary.get('total_failed', 0)}, "
            f"Review: {summary.get('total_review', 0)}"
        )
        print(result.get("report_markdown", ""))
    else:
        print(f"Analysis failed: {result.get('error')}")
        for detail in result.get("details", []):
            print(f"  - {detail}")


def _serialize_finding(finding: Finding) -> dict[str, Any]:
    return {
        "id": finding.id,
        "rule_id": finding.rule_id,
        "status": finding.status.value,
        "confidence": finding.confidence,
        "reasoning": finding.reasoning,
        "recommendation": finding.recommendation,
        "evidence_refs": finding.evidence_refs,
        "requires_human_review": finding.requires_human_review,
        "review_status": finding.review_status.value if finding.review_status else None,
    }


def _serialize_audit_result(result: Any) -> dict[str, Any]:
    relations = []
    for rel in result.relations:
        relations.append(
            {
                "id": rel.id,
                "compliance_id": rel.compliance_id,
                "artifact_id": rel.artifact_id,
                "status": rel.status.value,
                "evidence_count": len(rel.evidence_collected),
                "findings": [_serialize_finding(f) for f in rel.findings],
            }
        )

    return {
        "total_findings": result.total_findings,
        "total_passed": result.total_passed,
        "total_failed": result.total_failed,
        "total_review": result.total_review,
        "is_compliant": result.is_compliant,
        "needs_review": result.needs_review,
        "relations": relations,
    }


def _serialize_report(report: Any) -> dict[str, Any]:
    return {
        "id": report.id,
        "template_id": report.template_id,
        "generated_at": report.generated_at.isoformat(),
        "compliance_ids": report.compliance_ids,
        "artifact_ids": report.artifact_ids,
        "summary": {
            "total": report.summary.total,
            "passed": report.summary.passed,
            "failed": report.summary.failed,
            "review": report.summary.review,
            "not_applicable": report.summary.not_applicable,
            "avg_confidence": report.summary.avg_confidence,
        },
        "findings": [_serialize_finding(f) for f in report.findings],
        "evidence_refs": report.evidence_refs,
        "is_compliant": report.is_compliant,
        "needs_review": report.needs_review,
    }


if __name__ == "__main__":
    main()
