"""Parse and validate raw telemetry event records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class TelemetryEvent:
    """Normalized telemetry event extracted from a CloudWatch-style log record."""

    event_name: str
    event_ts: datetime
    user_email: str
    practice: str | None
    profile: str | None
    model_name: str | None
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_creation_tokens: int
    cost_usd: float
    duration_ms: int | None
    raw: dict


def parse_event(record: dict) -> TelemetryEvent:
    """Parse a CloudWatch-style telemetry record into a ``TelemetryEvent``.

    Attribute values are read from ``record["logEvents"][0]["attributes"]``.
    Resource metadata is read from ``record["resource"]``.

    Args:
        record: Raw telemetry record containing ``logEvents`` and ``resource``.

    Returns:
        Parsed and validated telemetry event.

    Raises:
        TypeError: If required top-level fields have invalid types.
        ValueError: If required fields are missing or malformed.
    """
    log_events = _require_list(record.get("logEvents"), "logEvents")
    if not log_events:
        raise ValueError("record['logEvents'] must contain at least one log event")

    first_event = log_events[0]
    attributes = _require_dict(first_event.get("attributes"), "logEvents[0].attributes")
    resource = _require_dict(record.get("resource"), "resource")

    event_name = _require_non_empty_str(attributes.get("event.name"), "event.name")
    event_ts = _parse_timestamp(attributes.get("event.timestamp"), "event.timestamp")
    user_email = _resolve_user_email(attributes, resource)
    practice = _optional_str(resource.get("user.practice"))
    profile = _optional_str(resource.get("user.profile"))
    model_name = _optional_str(attributes.get("model"))

    return TelemetryEvent(
        event_name=event_name,
        event_ts=event_ts,
        user_email=user_email,
        practice=practice,
        profile=profile,
        model_name=model_name,
        input_tokens=_parse_int(attributes.get("input_tokens"), "input_tokens"),
        output_tokens=_parse_int(attributes.get("output_tokens"), "output_tokens"),
        cache_read_tokens=_parse_int(attributes.get("cache_read_tokens"), "cache_read_tokens"),
        cache_creation_tokens=_parse_int(
            attributes.get("cache_creation_tokens"),
            "cache_creation_tokens",
        ),
        cost_usd=_parse_float(attributes.get("cost_usd"), "cost_usd"),
        duration_ms=_parse_optional_int(attributes.get("duration_ms"), "duration_ms"),
        raw=record,
    )


def _require_list(value: Any, field_name: str) -> list[Any]:
    """Return ``value`` when it is a list; otherwise raise a clear error."""
    if not isinstance(value, list):
        raise TypeError(f"record['{field_name}'] must be a list, got {type(value).__name__}")
    return value


def _require_dict(value: Any, field_name: str) -> dict[str, Any]:
    """Return ``value`` when it is a dict; otherwise raise a clear error."""
    if not isinstance(value, dict):
        raise TypeError(f"record['{field_name}'] must be a dict, got {type(value).__name__}")
    return value


def _require_non_empty_str(value: Any, field_name: str) -> str:
    """Return a stripped non-empty string or raise ``ValueError``."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a non-empty string, got {type(value).__name__}")
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} must be a non-empty string")
    return stripped


def _optional_str(value: Any) -> str | None:
    """Return a stripped string or ``None`` when the value is missing or blank."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"expected string or null, got {type(value).__name__}")
    stripped = value.strip()
    return stripped or None


def _resolve_user_email(attributes: dict[str, Any], resource: dict[str, Any]) -> str:
    """Resolve user email from attributes, falling back to resource metadata."""
    for source_name, payload in (("attributes", attributes), ("resource", resource)):
        email = payload.get("user.email")
        if email is None:
            continue
        if not isinstance(email, str) or not email.strip():
            raise ValueError(
                f"user.email in {source_name} must be a non-empty string when present"
            )
        return email.strip()

    raise ValueError("user.email is required in logEvents[0].attributes or resource")


def _parse_timestamp(value: Any, field_name: str) -> datetime:
    """Parse an ISO-8601 timestamp into an aware ``datetime``."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty ISO-8601 timestamp string")

    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"{field_name} is not a valid ISO-8601 timestamp: {value}") from exc

    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must include a timezone offset")
    return parsed


def _parse_int(value: Any, field_name: str, *, default: int = 0) -> int:
    """Parse an integer field, defaulting missing values to ``default``."""
    if value is None:
        return default
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer, got bool")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        raise ValueError(f"{field_name} must be an integer, got float {value}")
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return default
        try:
            return int(stripped)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be an integer, got {value!r}") from exc
    raise ValueError(f"{field_name} must be an integer, got {type(value).__name__}")


def _parse_float(value: Any, field_name: str, *, default: float = 0.0) -> float:
    """Parse a float field, defaulting missing values to ``default``."""
    if value is None:
        return default
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a float, got bool")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return default
        try:
            return float(stripped)
        except ValueError as exc:
            raise ValueError(f"{field_name} must be a float, got {value!r}") from exc
    raise ValueError(f"{field_name} must be a float, got {type(value).__name__}")


def _parse_optional_int(value: Any, field_name: str) -> int | None:
    """Parse an optional integer field, returning ``None`` when absent."""
    if value is None:
        return None
    return _parse_int(value, field_name)
