"""Health check endpoints for service monitoring."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.schemas.health import HealthResponse
from app.db.session import get_db

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


def _utc_timestamp() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()


@router.get("/health", response_model=HealthResponse)
def get_health(
    response: Response,
    db: Session = Depends(get_db),
) -> HealthResponse:
    """Return API and database health for orchestrators and load balancers."""
    timestamp = _utc_timestamp()

    try:
        db.execute(text("SELECT 1")).scalar_one()
    except Exception:
        logger.warning("Health check database probe failed", exc_info=True)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="error", database="error", timestamp=timestamp)

    return HealthResponse(status="ok", database="ok", timestamp=timestamp)
