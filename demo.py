#!/usr/bin/env python3
"""Kompline Demo Script - 금융규제 준수 자동 감사 시스템.

This demo shows the end-to-end compliance audit pipeline:
1. Load compliance rules from YAML
2. Register code artifact for audit
3. Run multi-agent audit pipeline
4. Display findings with HITL triggers

Usage:
    python demo.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from kompline.registry import get_compliance_registry, get_artifact_registry
from kompline.agents.audit_orchestrator import AuditOrchestrator, AuditResult


def print_header(title: str) -> None:
    """Print a formatted header."""
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_finding(finding, rule_title: str) -> None:
    """Print a finding with formatting."""
    status_map = {
        "pass": ("✅", "PASS", "\033[92m"),
        "fail": ("❌", "FAIL", "\033[91m"),
        "review": ("⚠️", "REVIEW", "\033[93m"),
        "not_applicable": ("➖", "N/A", "\033[90m"),
    }
    emoji, label, color = status_map.get(finding.status.value, ("?", "?", ""))
    reset = "\033[0m"

    print(f"\n{emoji} [{finding.rule_id}] {rule_title}")
    print(f"   Status: {color}{label}{reset} (Confidence: {finding.confidence:.0%})")
    print(f"   Reasoning: {finding.reasoning[:200]}")
    if finding.recommendation:
        print(f"   Recommendation: {finding.recommendation}")
    if finding.requires_human_review:
        print(f"   ⚡ Human Review Required")


def display_results(result: AuditResult, compliance) -> None:
    """Display audit results."""
    print_header("감사 결과 (Audit Results)")

    print(f"\n📊 Summary:")
    print(f"   Total Findings: {result.total_findings}")
    print(f"   ✅ Passed: {result.total_passed}")
    print(f"   ❌ Failed: {result.total_failed}")
    print(f"   ⚠️ Need Review: {result.total_review}")
    print(f"\n   Compliant: {'Yes' if result.is_compliant else 'No'}")

    # Build rule title map
    rule_titles = {rule.id: rule.title for rule in compliance.rules}

    print_header("세부 결과 (Detailed Findings)")

    for relation in result.relations:
        print(f"\n📋 Relation: {relation.compliance_id} × {relation.artifact_id}")
        print(f"   Status: {relation.status.value}")

        for finding in relation.findings:
            rule_title = rule_titles.get(finding.rule_id, "Unknown Rule")
            print_finding(finding, rule_title)

    # HITL Queue
    review_queue = [f for rel in result.relations for f in rel.findings if f.requires_human_review]
    if review_queue:
        print_header("인간 검토 대기열 (Human Review Queue)")
        print(f"\n{len(review_queue)} findings require human review:")
        for i, f in enumerate(review_queue, 1):
            print(f"   {i}. {f.rule_id}: {f.status.value.upper()}")


async def run_demo():
    """Run the compliance audit demo."""
    print_header("Kompline - 금융규제 준수 자동 감사 시스템")
    print("\n🚀 Multi-Agent Compliance Audit Demo")
    print("   별지5 알고리즘 공정성 자가평가")

    # Step 1: Load compliance
    print_header("Step 1: 규정 로드 (Load Compliance)")
    from kompline.demo_data import register_demo_compliances
    register_demo_compliances(include_privacy=False)
    comp_registry = get_compliance_registry()
    compliance = comp_registry.get("byeolji5-fairness")

    print(f"\n📜 Loaded: {compliance.name}")
    print(f"   Version: {compliance.version}")
    print(f"   Jurisdiction: {compliance.jurisdiction}")
    print(f"   Rules: {len(compliance.rules)}")
    for rule in compliance.rules:
        severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}.get(rule.severity.value, "⚪")
        print(f"     {severity_emoji} {rule.id}: {rule.title}")

    # Step 2: Register artifact
    print_header("Step 2: 감사 대상 등록 (Register Artifact)")
    from kompline.demo_data import register_file_artifact
    art_registry = get_artifact_registry()
    artifact_id = register_file_artifact(
        "samples/deposit_ranking.py",
        artifact_id="deposit-ranking",
        name="예금상품 추천 알고리즘",
        tags=["algorithm", "ranking", "deposit"],
    )
    artifact = art_registry.get(artifact_id)

    print(f"\n📁 Registered: {artifact.name}")
    print(f"   ID: {artifact.id}")
    print(f"   Type: {artifact.type.value}")
    print(f"   Path: {artifact.locator}")

    # Step 3: Run audit
    print_header("Step 3: 감사 실행 (Run Audit)")
    print("\n🔍 Running multi-agent audit pipeline...")
    print("   - AuditOrchestrator: Coordinating audit")
    print("   - AuditAgent: Evaluating compliance")
    print("   - CodeReader: Extracting evidence")
    print("   - RuleEvaluator: Assessing rules")

    orchestrator = AuditOrchestrator(parallel=False)
    result = await orchestrator.audit(
        compliance_ids=[compliance.id],
        artifact_ids=[artifact.id],
    )

    # Step 4: Display results
    display_results(result, compliance)

    # Summary
    print_header("Demo Complete")
    if result.is_compliant:
        print("\n✅ The artifact PASSES all compliance checks.")
    else:
        print("\n❌ The artifact has compliance issues that need attention.")
        print("   Review the findings above and address the issues.")

    print("\n💡 Next Steps:")
    print("   1. Review HITL queue items")
    print("   2. Fix identified issues in code")
    print("   3. Re-run audit to verify fixes")
    print("   4. Generate compliance report")
    print()


def main():
    """Entry point."""
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("\n\nDemo interrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
