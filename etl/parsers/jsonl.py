"""Parse JSONL telemetry event files."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path

logger = logging.getLogger(__name__)


def read_jsonl(path: Path) -> Iterator[dict]:
    """Yield one parsed JSON object per non-empty line in a JSONL file.

    Args:
        path: Path to a UTF-8 encoded JSONL file.

    Yields:
        Parsed JSON objects, one per line.

    Raises:
        RuntimeError: If a non-empty line contains invalid JSON.
    """
    logger.info("Reading JSONL from %s", path)

    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                logger.debug("Skipping empty line %s in %s", line_number, path)
                continue

            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise RuntimeError(
                    f"Invalid JSON on line {line_number} of {path}: {exc.msg}"
                ) from exc

            yield record
