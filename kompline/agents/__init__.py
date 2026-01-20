"""Agent definitions for Kompline compliance system."""

# Lazy imports to avoid requiring the agents SDK at import time
__all__ = [
    "create_orchestrator_agent",
    "create_code_analyzer_agent",
    "create_rule_matcher_agent",
    "create_report_generator_agent",
]


def __getattr__(name: str):
    """Lazy import agent factory functions."""
    if name == "create_orchestrator_agent":
        from .orchestrator import create_orchestrator_agent
        return create_orchestrator_agent
    elif name == "create_code_analyzer_agent":
        from .code_analyzer import create_code_analyzer_agent
        return create_code_analyzer_agent
    elif name == "create_rule_matcher_agent":
        from .rule_matcher import create_rule_matcher_agent
        return create_rule_matcher_agent
    elif name == "create_report_generator_agent":
        from .report_generator import create_report_generator_agent
        return create_report_generator_agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
