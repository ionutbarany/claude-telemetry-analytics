"""Enrich telemetry events with employee metadata from ``employees.csv``."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import polars as pl

logger = logging.getLogger(__name__)

_REQUIRED_COLUMNS = ("email", "full_name", "practice", "level", "location")


@dataclass(frozen=True, slots=True)
class EmployeeRecord:
    """Employee metadata joined onto telemetry users during ETL."""

    email: str
    full_name: str
    practice: str
    level: str
    location: str


def load_employees_csv(path: Path) -> list[EmployeeRecord]:
    """Load and validate employee records from a CSV file using Polars.

    Args:
        path: Path to ``employees.csv`` produced by ``generate_fake_data.py``.

    Returns:
        Parsed employee records keyed by email.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        ValueError: If required columns are missing or rows are invalid.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Employee file not found: {path}")

    frame = pl.read_csv(path)
    missing = [column for column in _REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"employees.csv missing required columns: {', '.join(missing)}")

    records: list[EmployeeRecord] = []
    for row in frame.select(_REQUIRED_COLUMNS).iter_rows(named=True):
        email = str(row["email"]).strip()
        if not email:
            logger.warning("Skipping employee row with empty email")
            continue
        records.append(
            EmployeeRecord(
                email=email,
                full_name=str(row["full_name"]).strip(),
                practice=str(row["practice"]).strip(),
                level=str(row["level"]).strip(),
                location=str(row["location"]).strip(),
            )
        )

    logger.info("Loaded %s employee records from %s", len(records), path)
    return records


def employees_by_email(records: list[EmployeeRecord]) -> dict[str, EmployeeRecord]:
    """Index employee records by normalized email address."""
    return {record.email.lower(): record for record in records}
