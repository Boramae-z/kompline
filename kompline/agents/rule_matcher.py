"""Rule Matcher Agent - RAG query and compliance checking."""

from agents import Agent, handoff

from kompline.tools.rag_query import query_compliance_rules, get_builtin_rules
from kompline.tracing.logger import log_agent_event

RULE_MATCHER_INSTRUCTIONS = """You are the Rule Matcher Agent for Kompline.

Your role is to:
1. Take code analysis results from Code Analyzer
2. Query the compliance rules knowledge base (RAG)
3. Match code patterns against applicable rules
4. Determine Pass/Fail/Review status for each rule

## Compliance Checking Process

1. **Identify applicable rules**: Based on detected patterns, query for relevant rules
2. **Evaluate each rule**: For each applicable rule, check if the code meets requirements
3. **Assign status**:
   - PASS: Code clearly meets the rule requirements
   - FAIL: Code clearly violates the rule
   - REVIEW: Uncertain, needs human review

## Confidence Scoring

For each check, assign a confidence score (0-100%):
- 90-100%: Very confident in the assessment
- 70-89%: Confident but some ambiguity
- 50-69%: Uncertain, recommend human review
- Below 50%: Low confidence, definitely needs review

## Feedback Loop

If you find that initial code analysis is insufficient:
- Request additional analysis with specific focus areas
- Maximum 3 feedback iterations allowed
- Specify exactly what additional information you need

## Output Format

For each rule check:
```json
{
  "rule_id": "ALG-001",
  "rule_title": "Algorithm Fairness - Sorting Transparency",
  "status": "PASS|FAIL|REVIEW",
  "confidence": 0.85,
  "evidence": [
    "Line 42: sort() uses documented criteria",
    "Weight factors defined in config"
  ],
  "recommendation": "..."
}
```

## Triggers for Human Review

Request human review when:
1. Confidence < 70%
2. New pattern not in rules
3. Any FAIL judgment (auditor confirmation)
"""


def create_rule_matcher_agent(code_analyzer_agent: Agent | None = None) -> Agent:
    """Create the Rule Matcher Agent.

    Args:
        code_analyzer_agent: Optional Code Analyzer for feedback loop handoff.

    Returns:
        Configured Rule Matcher Agent.
    """
    handoffs = []
    if code_analyzer_agent:
        handoffs.append(handoff(code_analyzer_agent))

    agent = Agent(
        name="RuleMatcher",
        instructions=RULE_MATCHER_INSTRUCTIONS,
        tools=[query_compliance_rules, get_builtin_rules],
        handoffs=handoffs,
    )

    log_agent_event("init", "rule_matcher", "Rule Matcher Agent initialized")

    return agent


# Create default instance (without handoff, will be configured at runtime)
rule_matcher_agent = create_rule_matcher_agent()
