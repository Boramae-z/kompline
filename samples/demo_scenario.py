"""Demo scenario for Kompline multi-compliance audit.

This demo shows:
1. Loading compliance definitions from YAML
2. Registering artifacts (code files)
3. Running multi-compliance audit with parallel execution
4. Generating reports in 별지5 format
"""

import asyncio
from pathlib import Path

from kompline.agents.audit_orchestrator import create_audit_orchestrator
from kompline.agents.report_generator import create_report_generator
from kompline.demo_data import register_demo_compliances, register_file_artifact


def setup_compliances() -> None:
    """Set up sample compliance definitions programmatically."""
    ids = register_demo_compliances()
    print(f"Registered compliances: {ids}")


def setup_artifacts() -> None:
    """Set up sample artifacts."""
    samples_dir = Path(__file__).parent
    deposit_code_path = samples_dir / "deposit_ranking.py"

    if deposit_code_path.exists():
        artifact_id = register_file_artifact(
            deposit_code_path,
            artifact_id="deposit-ranking-code",
            name="Deposit Ranking Algorithm",
            tags=["finance", "ranking", "demo"],
        )
        print(f"Registered artifact: {artifact_id} at {deposit_code_path}")
    else:
        print(f"Warning: {deposit_code_path} not found")


async def run_demo() -> None:
    """Run the multi-compliance demo."""
    print("\n" + "=" * 60)
    print("Kompline Multi-Compliance Audit Demo")
    print("=" * 60 + "\n")

    # 1. Setup
    print("1. Setting up compliances and artifacts...")
    setup_compliances()
    setup_artifacts()
    print()

    # 2. Create orchestrator
    print("2. Creating audit orchestrator...")
    orchestrator = create_audit_orchestrator(parallel=True)
    print(f"   Orchestrator ready (parallel={orchestrator.parallel})")
    print()

    # 3. Run audit
    print("3. Running audit...")
    print("   Compliance: byeolji5-fairness")
    print("   Artifact: deposit-ranking-code")
    print()

    try:
        result = await orchestrator.audit(
            compliance_ids=["byeolji5-fairness"],
            artifact_ids=["deposit-ranking-code"],
        )

        # 4. Display results
        print("4. Audit Results:")
        print(f"   Total relations: {len(result.relations)}")
        print(f"   Total findings: {result.total_findings}")
        print(f"   Passed: {result.total_passed}")
        print(f"   Failed: {result.total_failed}")
        print(f"   Review: {result.total_review}")
        print(f"   Is compliant: {result.is_compliant}")
        print()

        # 5. Show findings
        print("5. Detailed Findings:")
        for relation in result.relations:
            print(f"\n   Relation: {relation.id}")
            print(f"   Compliance: {relation.compliance_id}")
            print(f"   Artifact: {relation.artifact_id}")
            print(f"   Status: {relation.status.value}")
            print(f"   Evidence collected: {len(relation.evidence_collected)}")
            print(f"   Findings: {len(relation.findings)}")

            for finding in relation.findings:
                status_icon = {
                    "pass": "✅",
                    "fail": "❌",
                    "review": "🔍",
                    "not_applicable": "➖",
                }.get(finding.status.value, "❓")

                print(f"\n   {status_icon} {finding.rule_id}")
                print(f"      Status: {finding.status.value}")
                print(f"      Confidence: {finding.confidence:.1%}")
                print(f"      Reasoning: {finding.reasoning[:100]}...")
                if finding.requires_human_review:
                    print("      ⚠️  Requires human review")

        # 6. Generate report
        print("\n6. Generating 별지5 Report...")
        generator = create_report_generator()
        report_text = generator.generate_byeolji5(result)
        print(report_text)

        # 7. Review queue
        review_queue = orchestrator.get_review_queue(result)
        if review_queue:
            print(f"\n7. Review Queue: {len(review_queue)} items pending")
            for finding in review_queue:
                print(f"   - {finding.rule_id}: {finding.status.value}")
        else:
            print("\n7. Review Queue: Empty (all findings auto-approved)")

    except ValueError as e:
        print(f"Error: {e}")
        print("Make sure compliances and artifacts are registered before running audit.")

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


def main():
    """Main entry point."""
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()
