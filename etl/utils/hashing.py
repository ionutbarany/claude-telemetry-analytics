"""Hashing utilities for deduplication and idempotent loads."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def hash_event_payload(payload: dict[str, Any]) -> str:
    """Return a stable SHA-256 hex digest for a telemetry event payload.

    Args:
        payload: Raw event dictionary (attributes + resource subset).

    Returns:
        Lowercase hex digest suitable for deduplication keys.
    """
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
