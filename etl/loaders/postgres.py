"""Load transformed telemetry data into PostgreSQL."""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy.orm import Session

from app.db.models.api_request import FactApiRequest
from app.db.session import SessionLocal
from etl.parsers.events import TelemetryEvent

logger = logging.getLogger(__name__)

_INSERT_BATCH_SIZE = 1000


def _telemetry_event_to_row(event: TelemetryEvent) -> FactApiRequest:
    """Map a parsed telemetry event to a ``FactApiRequest`` ORM row."""
    return FactApiRequest(
        user_email=event.user_email,
        event_ts=event.event_ts,
        model_name=event.model_name or "unknown",
        input_tokens=event.input_tokens,
        output_tokens=event.output_tokens,
        cache_read_tokens=event.cache_read_tokens,
        cache_creation_tokens=event.cache_creation_tokens,
        cost_usd=Decimal(str(event.cost_usd)),
        duration_ms=event.duration_ms,
    )


def insert_api_requests(events: list[TelemetryEvent], session: Session | None = None) -> int:
    """Insert parsed API request telemetry events into ``fact_api_requests``.

    Args:
        events: Parsed ``api_request`` telemetry events to persist.
        session: Optional SQLAlchemy session. When omitted, a new session is created
            and closed after the insert completes.

    Returns:
        Number of rows inserted.
    """
    if not events:
        logger.info("No api_request events to insert")
        return 0

    own_session = session is None
    db = session or SessionLocal()
    inserted = 0

    try:
        for batch_start in range(0, len(events), _INSERT_BATCH_SIZE):
            batch = events[batch_start : batch_start + _INSERT_BATCH_SIZE]
            rows = [_telemetry_event_to_row(event) for event in batch]
            db.add_all(rows)
            db.commit()
            inserted += len(rows)
            logger.debug(
                "Inserted batch of %s api_request rows (%s total so far)",
                len(rows),
                inserted,
            )

        logger.info("Inserted %s api_request rows into fact_api_requests", inserted)
        return inserted
    except Exception:
        db.rollback()
        logger.exception("Failed to insert api_request rows")
        raise
    finally:
        if own_session:
            db.close()
