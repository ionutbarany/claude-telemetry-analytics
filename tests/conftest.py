"""Shared pytest fixtures for API tests."""

from __future__ import annotations

import os
from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://test:test@localhost:5432/test",
)

from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def mock_db() -> MagicMock:
    """Return a stand-in SQLAlchemy session for dependency overrides."""
    return MagicMock()


@pytest.fixture
def client(mock_db: MagicMock) -> Generator[TestClient, None, None]:
    """Provide a TestClient with the database dependency replaced by a mock."""
    def override_get_db() -> Generator[MagicMock, None, None]:
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
