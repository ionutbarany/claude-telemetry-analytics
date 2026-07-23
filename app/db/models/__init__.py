"""SQLAlchemy ORM models for dimension and fact tables.

Import all mapped classes here so ``Base.metadata`` is fully populated
before Alembic autogenerate runs.
"""

from app.db.models.user import DimUser

__all__ = [
    "DimUser",
]
