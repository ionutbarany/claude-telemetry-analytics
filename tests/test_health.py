"""Tests for the health check endpoint."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient


def test_health_returns_ok(client: TestClient, mock_db: MagicMock) -> None:
    """GET /health should report a healthy API and database."""
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 1
    mock_db.execute.return_value = mock_result

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
