"""Tests for practice and trend analytics endpoints."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock

from fastapi.testclient import TestClient


def test_analytics_practices_returns_expected_keys(
    client: TestClient,
    mock_db: MagicMock,
) -> None:
    """GET /analytics/practices should return practice rollup payloads."""
    mock_row = MagicMock()
    mock_row.practice = "Platform"
    mock_row.requests = 10
    mock_row.total_cost_usd = Decimal("25.00")
    mock_row.unique_users = 3

    mock_result = MagicMock()
    mock_result.all.return_value = [mock_row]
    mock_db.execute.return_value = mock_result

    response = client.get("/analytics/practices")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert set(payload[0].keys()) == {
        "practice",
        "requests",
        "total_cost_usd",
        "unique_users",
    }


def test_analytics_trends_returns_expected_keys(
    client: TestClient,
    mock_db: MagicMock,
) -> None:
    """GET /analytics/trends should return daily trend payloads."""
    mock_row = MagicMock()
    mock_row.event_date = datetime(2026, 7, 1, tzinfo=timezone.utc)
    mock_row.requests = 100
    mock_row.total_cost_usd = Decimal("42.00")

    mock_result = MagicMock()
    mock_result.all.return_value = [mock_row]
    mock_db.execute.return_value = mock_result

    response = client.get("/analytics/trends")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["event_date"] == date(2026, 7, 1).isoformat()
    assert set(payload[0].keys()) == {"event_date", "requests", "total_cost_usd"}
