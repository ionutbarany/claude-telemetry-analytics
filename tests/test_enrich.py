"""Tests for employee CSV enrichment."""

from __future__ import annotations

from pathlib import Path

import pytest

from etl.transformers.enrich import employees_by_email, load_employees_csv


def test_load_employees_csv_parses_records(tmp_path: Path) -> None:
    """load_employees_csv should return validated employee records."""
    csv_path = tmp_path / "employees.csv"
    csv_path.write_text(
        "email,full_name,practice,level,location\n"
        "alice@example.com,Alice,Platform,L5,US\n",
        encoding="utf-8",
    )

    records = load_employees_csv(csv_path)

    assert len(records) == 1
    assert records[0].email == "alice@example.com"
    assert records[0].practice == "Platform"
    assert employees_by_email(records)["alice@example.com"].level == "L5"


def test_load_employees_csv_requires_columns(tmp_path: Path) -> None:
    """load_employees_csv should fail when required columns are missing."""
    csv_path = tmp_path / "employees.csv"
    csv_path.write_text("email,full_name\nbob@example.com,Bob\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing required columns"):
        load_employees_csv(csv_path)
