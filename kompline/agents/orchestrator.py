"""Orchestrator Agent - Triage and workflow control."""

from agents import Agent, handoff

from kompline.tracing.logger import log_agent_event

ORCHESTRATOR_INSTRUCTIONS = """You are the Orchestrator Agent for Kompline, a compliance verification system
for Korean financial regulations.

Your role is to:
1. Receive source code submissions for compliance analysis
2. Triage the request and determine the analysis workflow
3. Coordinate handoffs between specialized agents
4. Track the overall analysis progress

## Workflow

1. When you receive source code, first validate it's Python code
2. Hand off to Code Analyzer Agent to parse and understand the code
3. Once analysis is complete, hand off to Rule Matcher Agent for compliance checking
4. After compliance checks, hand off to Report Generator Agent for final report
5. If Rule Matcher requests re-analysis (feedback loop), coordinate with Code Analyzer

## Handoff Rules

- Always provide context when handing off to another agent
- Include relevant findings from previous steps
- Track iteration count for feedback loops (max 3 iterations)
- If max iterations reached, proceed to Report Generator with current results

## Response Format

When reporting status, use this format:
- Current step: [step name]
- Agent: [current agent]
- Status: [in_progress/completed/needs_review]
- Findings: [summary of findings so far]
"""


def create_orchestrator_agent(
    code_analyzer_agent: Agent,
    rule_matcher_agent: Agent,
    report_generator_agent: Agent,
) -> Agent:
    """Create the Orchestrator Agent with handoffs configured.

    Args:
        code_analyzer_agent: The Code Analyzer Agent for parsing code.
        rule_matcher_agent: The Rule Matcher Agent for compliance checking.
        report_generator_agent: The Report Generator Agent for creating reports.

    Returns:
        Configured Orchestrator Agent.
    """

    def on_handoff(from_agent: str, to_agent: str, context: str) -> None:
        log_agent_event(
            "handoff",
            "orchestrator",
            f"Handing off from {from_agent} to {to_agent}",
            {"context": context[:200]},
        )

    orchestrator = Agent(
        name="Orchestrator",
        instructions=ORCHESTRATOR_INSTRUCTIONS,
        handoffs=[
            handoff(code_analyzer_agent),
            handoff(rule_matcher_agent),
            handoff(report_generator_agent),
        ],
    )

    log_agent_event("init", "orchestrator", "Orchestrator Agent initialized")

    return orchestrator


# Default agent instance (will be configured at runtime)
orchestrator_agent: Agent | None = None
