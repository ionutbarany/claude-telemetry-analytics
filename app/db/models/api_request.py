"""ORM model for API request telemetry facts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, Identity, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FactApiRequest(Base):
    """Persisted API request event with token usage, cost, and timing metrics."""

    __tablename__ = "fact_api_requests"

    request_sk: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        primary_key=True,
    )
    user_email: Mapped[str] = mapped_column(String, index=True)
    event_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    model_name: Mapped[str] = mapped_column(String, index=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cache_creation_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("0"))
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
    )

    def __repr__(self) -> str:
        """Return a concise debug representation of the row."""
        return (
            f"FactApiRequest("
            f"request_sk={self.request_sk!r}, "
            f"user_email={self.user_email!r}, "
            f"event_ts={self.event_ts!r}, "
            f"model_name={self.model_name!r}, "
            f"cost_usd={self.cost_usd!r})"
        )
