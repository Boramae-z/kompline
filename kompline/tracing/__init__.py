"""Tracing and logging for Kompline agents."""

from .logger import setup_tracing, log_agent_event

__all__ = [
    "setup_tracing",
    "log_agent_event",
]
