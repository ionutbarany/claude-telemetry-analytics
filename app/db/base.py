"""SQLAlchemy declarative base for ORM model definitions."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy ORM models in this application.

    Every mapped class should inherit from ``Base`` so Alembic and the
    metadata registry share a single source of truth for table definitions.
    """


# Import models after ``Base`` is defined so mapped classes register with metadata.
import app.db.models  # noqa: E402, F401
