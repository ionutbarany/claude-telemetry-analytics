"""Tests for the analytics overview endpoint."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

EXPECTED_OVERVIEW_KEYS = {
    "total_requests",
    "total_cost_usd",
    "total_input_tokens",
    "total_output_tokens",
    "avg_latency_ms",
    "unique_users",
}


def test_analytics_overview_returns_expected_keys(
    client: TestClient,
    mock_db: MagicMock,
) -> None:
    """GET /analytics/overview should return the full overview payload shape."""
    mock_row = MagicMock()
    mock_row.total_requests = 42
    mock_row.total_cost_usd = Decimal("12.50")
    mock_row.total_input_tokens = 1000
    mock_row.total_output_tokens = 500
    mock_row.avg_latency_ms = Decimal("250.5")
    mock_row.unique_users = 7

    mock_result = MagicMock()
    mock_result.one.return_value = mock_row
    mock_db.execute.return_value = mock_result

    response = client.get("/analytics/overview")

    assert response.status_code == 200
    assert set(response.json().keys()) == EXPECTED_OVERVIEW_KEYS
