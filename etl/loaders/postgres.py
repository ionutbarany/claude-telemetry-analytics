"""Load transformed telemetry data into PostgreSQL."""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.db.models.api_request import FactApiRequest
from app.db.models.user import DimUser
from app.db.session import SessionLocal
from etl.loaders.batch import INSERT_BATCH_SIZE, chunk_sequence
from etl.parsers.events import TelemetryEvent
from etl.transformers.enrich import EmployeeRecord

logger = logging.getLogger(__name__)


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


def upsert_dim_users(
    employees: list[EmployeeRecord],
    session: Session | None = None,
) -> int:
    """Upsert employee metadata into ``dim_users`` keyed by email.

    Args:
        employees: Enriched employee records from ``employees.csv``.
        session: Optional SQLAlchemy session.

    Returns:
        Number of employee rows processed.
    """
    if not employees:
        logger.info("No employee records to upsert into dim_users")
        return 0

    own_session = session is None
    db = session or SessionLocal()
    processed = 0

    try:
        for batch in chunk_sequence(employees, INSERT_BATCH_SIZE):
            values = [
                {
                    "user_id": employee.email,
                    "email": employee.email,
                    "practice": employee.practice,
                    "level": employee.level,
                    "location": employee.location,
                }
                for employee in batch
            ]
            stmt = pg_insert(DimUser).values(values)
            stmt = stmt.on_conflict_do_update(
                index_elements=[DimUser.user_id],
                set_={
                    "email": stmt.excluded.email,
                    "practice": stmt.excluded.practice,
                    "level": stmt.excluded.level,
                    "location": stmt.excluded.location,
                },
            )
            db.execute(stmt)
            db.commit()
            processed += len(batch)

        logger.info("Upserted %s rows into dim_users", processed)
        return processed
    except Exception:
        db.rollback()
        logger.exception("Failed to upsert dim_users rows")
        raise
    finally:
        if own_session:
            db.close()


def sync_dim_users_from_events(
    events: list[TelemetryEvent],
    employees_by_email: dict[str, EmployeeRecord],
    session: Session | None = None,
) -> int:
    """Ensure ``dim_users`` contains every email observed in telemetry events.

    Employee CSV values take precedence over sparse telemetry resource fields.

    Args:
        events: Parsed telemetry events (any event type).
        employees_by_email: Employee lookup keyed by lowercase email.
        session: Optional SQLAlchemy session.

    Returns:
        Number of distinct user emails processed.
    """
    own_session = session is None
    db = session or SessionLocal()
    seen: set[str] = set()
    upsert_rows: list[EmployeeRecord] = []

    for event in events:
        email_key = event.user_email.lower()
        if email_key in seen:
            continue
        seen.add(email_key)

        employee = employees_by_email.get(email_key)
        if employee is not None:
            upsert_rows.append(employee)
            continue

        upsert_rows.append(
            EmployeeRecord(
                email=event.user_email,
                full_name=event.user_email,
                practice=event.practice or "Unknown",
                level=event.profile or "Unknown",
                location="Unknown",
            )
        )

    try:
        return upsert_dim_users(upsert_rows, session=db)
    finally:
        if own_session:
            db.close()


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
        for batch in chunk_sequence(events, INSERT_BATCH_SIZE):
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
