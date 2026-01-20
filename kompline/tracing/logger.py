"""Tracing and logging for Kompline agents."""

import logging
import sys
from datetime import datetime
from typing import Any


class AgentTracer:
    """Tracer for agent events and workflows."""

    def __init__(self, name: str = "kompline"):
        self.logger = logging.getLogger(name)
        self._setup_handler()
        self.events: list[dict[str, Any]] = []

    def _setup_handler(self) -> None:
        """Setup console handler with formatting."""
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter(
                "[%(asctime)s] %(levelname)s - %(name)s - %(message)s",
                datefmt="%H:%M:%S",
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def log(
        self,
        event_type: str,
        agent: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Log an agent event.

        Args:
            event_type: Type of event (e.g., "handoff", "tool_call", "decision").
            agent: Name of the agent.
            message: Human-readable message.
            data: Optional additional data.
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "agent": agent,
            "message": message,
            "data": data or {},
        }
        self.events.append(event)

        log_msg = f"[{agent}] {event_type}: {message}"
        if data:
            log_msg += f" | {data}"
        self.logger.info(log_msg)

    def get_events(self, agent: str | None = None) -> list[dict[str, Any]]:
        """Get logged events, optionally filtered by agent."""
        if agent:
            return [e for e in self.events if e["agent"] == agent]
        return self.events.copy()

    def clear(self) -> None:
        """Clear all logged events."""
        self.events.clear()


# Global tracer instance
_tracer: AgentTracer | None = None


def setup_tracing(log_level: str = "INFO") -> AgentTracer:
    """Setup global tracing.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR).

    Returns:
        The configured AgentTracer instance.
    """
    global _tracer
    _tracer = AgentTracer()
    _tracer.logger.setLevel(getattr(logging, log_level.upper()))
    return _tracer


def get_tracer() -> AgentTracer:
    """Get the global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = AgentTracer()
    return _tracer


def log_agent_event(
    event_type: str,
    agent: str,
    message: str,
    data: dict[str, Any] | None = None,
) -> None:
    """Log an agent event using the global tracer.

    Args:
        event_type: Type of event.
        agent: Name of the agent.
        message: Human-readable message.
        data: Optional additional data.
    """
    get_tracer().log(event_type, agent, message, data)
