"""Tests for ETL normalization helpers."""

from __future__ import annotations

from etl.transformers.normalize import normalize_event_name


def test_normalize_event_name_maps_fully_qualified_names() -> None:
    """Fully qualified Claude Code event names should map to short canonical names."""
    assert normalize_event_name("claude_code.api_request") == "api_request"
    assert normalize_event_name("claude_code.user_prompt") == "user_prompt"


def test_normalize_event_name_passthrough_short_names() -> None:
    """Short event names should pass through unchanged."""
    assert normalize_event_name("api_request") == "api_request"
