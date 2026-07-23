"""Normalize and clean telemetry fields for downstream processing."""

from __future__ import annotations

# Canonical short names used by the ETL loader and analytics layer.
EVENT_ALIASES: dict[str, str] = {
    "claude_code.api_request": "api_request",
    "claude_code.user_prompt": "user_prompt",
    "claude_code.tool_result": "tool_result",
    "claude_code.api_error": "api_error",
}


def normalize_event_name(raw_name: str) -> str:
    """Map fully qualified Claude Code event names to canonical short names.

    Args:
        raw_name: Value from ``event.name`` or ``body`` in a telemetry record.

    Returns:
        Canonical event name (e.g. ``api_request``).
    """
    stripped = raw_name.strip()
    return EVENT_ALIASES.get(stripped, stripped)
