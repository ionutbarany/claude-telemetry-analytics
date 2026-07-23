"""SQLAlchemy ORM models for dimension and fact tables.

Import all mapped classes here so ``Base.metadata`` is fully populated
before Alembic autogenerate runs.
"""

from app.db.models.user import DimUser
from app.db.models.api_request import FactApiRequest

__all__ = [
    "DimUser",
    "FactApiRequest",
]
