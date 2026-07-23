"""Domain queries for analytics aggregations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.api_request import FactApiRequest
from app.db.models.user import DimUser


@dataclass(frozen=True, slots=True)
class OverviewMetrics:
    """Platform-wide aggregate metrics."""

    total_requests: int
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    avg_latency_ms: float
    unique_users: int


@dataclass(frozen=True, slots=True)
class ModelMetrics:
    """Per-model usage rollup."""

    model_name: str
    requests: int
    total_cost_usd: float
    avg_latency_ms: float


@dataclass(frozen=True, slots=True)
class TopUserMetrics:
    """Per-user cost rollup."""

    user_email: str
    total_cost_usd: float
    total_tokens: int


@dataclass(frozen=True, slots=True)
class PracticeMetrics:
    """Per-practice cost and usage rollup."""

    practice: str
    requests: int
    total_cost_usd: float
    unique_users: int


@dataclass(frozen=True, slots=True)
class LevelMetrics:
    """Per-level cost and usage rollup."""

    level: str
    requests: int
    total_cost_usd: float
    unique_users: int


@dataclass(frozen=True, slots=True)
class TrendMetrics:
    """Daily cost and request trend point."""

    event_date: date
    requests: int
    total_cost_usd: float


def _as_float(value: Decimal | float | int | None) -> float:
    """Convert a numeric aggregate to float, defaulting missing values to zero."""
    if value is None:
        return 0.0
    return float(value)


def _as_int(value: int | None) -> int:
    """Convert an integer aggregate to int, defaulting missing values to zero."""
    return 0 if value is None else int(value)


def fetch_overview_metrics(db: Session) -> OverviewMetrics:
    """Return platform-wide totals for requests, cost, tokens, latency, and users."""
    stmt = select(
        func.count(FactApiRequest.request_sk).label("total_requests"),
        func.coalesce(func.sum(FactApiRequest.cost_usd), 0).label("total_cost_usd"),
        func.coalesce(func.sum(FactApiRequest.input_tokens), 0).label("total_input_tokens"),
        func.coalesce(func.sum(FactApiRequest.output_tokens), 0).label("total_output_tokens"),
        func.coalesce(func.avg(FactApiRequest.duration_ms), 0).label("avg_latency_ms"),
        func.count(func.distinct(FactApiRequest.user_email)).label("unique_users"),
    )
    row = db.execute(stmt).one()
    return OverviewMetrics(
        total_requests=_as_int(row.total_requests),
        total_cost_usd=_as_float(row.total_cost_usd),
        total_input_tokens=_as_int(row.total_input_tokens),
        total_output_tokens=_as_int(row.total_output_tokens),
        avg_latency_ms=_as_float(row.avg_latency_ms),
        unique_users=_as_int(row.unique_users),
    )


def fetch_model_metrics(db: Session) -> list[ModelMetrics]:
    """Return per-model request counts, cost, and average latency."""
    stmt = (
        select(
            FactApiRequest.model_name.label("model_name"),
            func.count(FactApiRequest.request_sk).label("requests"),
            func.coalesce(func.sum(FactApiRequest.cost_usd), 0).label("total_cost_usd"),
            func.coalesce(func.avg(FactApiRequest.duration_ms), 0).label("avg_latency_ms"),
        )
        .group_by(FactApiRequest.model_name)
        .order_by(func.coalesce(func.sum(FactApiRequest.cost_usd), 0).desc())
    )
    rows = db.execute(stmt).all()
    return [
        ModelMetrics(
            model_name=row.model_name,
            requests=_as_int(row.requests),
            total_cost_usd=_as_float(row.total_cost_usd),
            avg_latency_ms=_as_float(row.avg_latency_ms),
        )
        for row in rows
    ]


def fetch_top_users(db: Session, limit: int) -> list[TopUserMetrics]:
    """Return the highest-spending users ranked by total cost."""
    total_tokens_expr = FactApiRequest.input_tokens + FactApiRequest.output_tokens
    stmt = (
        select(
            FactApiRequest.user_email.label("user_email"),
            func.coalesce(func.sum(FactApiRequest.cost_usd), 0).label("total_cost_usd"),
            func.coalesce(func.sum(total_tokens_expr), 0).label("total_tokens"),
        )
        .group_by(FactApiRequest.user_email)
        .order_by(func.coalesce(func.sum(FactApiRequest.cost_usd), 0).desc())
        .limit(limit)
    )
    rows = db.execute(stmt).all()
    return [
        TopUserMetrics(
            user_email=row.user_email,
            total_cost_usd=_as_float(row.total_cost_usd),
            total_tokens=_as_int(row.total_tokens),
        )
        for row in rows
    ]


def fetch_practice_metrics(db: Session) -> list[PracticeMetrics]:
    """Return cost and usage rollups grouped by engineering practice."""
    stmt = (
        select(
            func.coalesce(DimUser.practice, "Unknown").label("practice"),
            func.count(FactApiRequest.request_sk).label("requests"),
            func.coalesce(func.sum(FactApiRequest.cost_usd), 0).label("total_cost_usd"),
            func.count(func.distinct(FactApiRequest.user_email)).label("unique_users"),
        )
        .join(DimUser, DimUser.email == FactApiRequest.user_email, isouter=True)
        .group_by(func.coalesce(DimUser.practice, "Unknown"))
        .order_by(func.coalesce(func.sum(FactApiRequest.cost_usd), 0).desc())
    )
    rows = db.execute(stmt).all()
    return [
        PracticeMetrics(
            practice=row.practice,
            requests=_as_int(row.requests),
            total_cost_usd=_as_float(row.total_cost_usd),
            unique_users=_as_int(row.unique_users),
        )
        for row in rows
    ]


def fetch_level_metrics(db: Session) -> list[LevelMetrics]:
    """Return cost and usage rollups grouped by employee level."""
    stmt = (
        select(
            func.coalesce(DimUser.level, "Unknown").label("level"),
            func.count(FactApiRequest.request_sk).label("requests"),
            func.coalesce(func.sum(FactApiRequest.cost_usd), 0).label("total_cost_usd"),
            func.count(func.distinct(FactApiRequest.user_email)).label("unique_users"),
        )
        .join(DimUser, DimUser.email == FactApiRequest.user_email, isouter=True)
        .group_by(func.coalesce(DimUser.level, "Unknown"))
        .order_by(func.coalesce(func.sum(FactApiRequest.cost_usd), 0).desc())
    )
    rows = db.execute(stmt).all()
    return [
        LevelMetrics(
            level=row.level,
            requests=_as_int(row.requests),
            total_cost_usd=_as_float(row.total_cost_usd),
            unique_users=_as_int(row.unique_users),
        )
        for row in rows
    ]


def fetch_daily_trends(db: Session) -> list[TrendMetrics]:
    """Return daily request volume and cost ordered chronologically."""
    day_bucket = func.date_trunc("day", FactApiRequest.event_ts).label("event_date")
    stmt = (
        select(
            day_bucket,
            func.count(FactApiRequest.request_sk).label("requests"),
            func.coalesce(func.sum(FactApiRequest.cost_usd), 0).label("total_cost_usd"),
        )
        .group_by(day_bucket)
        .order_by(day_bucket.asc())
    )
    rows = db.execute(stmt).all()
    return [
        TrendMetrics(
            event_date=row.event_date.date(),
            requests=_as_int(row.requests),
            total_cost_usd=_as_float(row.total_cost_usd),
        )
        for row in rows
    ]
