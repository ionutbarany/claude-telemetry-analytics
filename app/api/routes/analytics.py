"""Analytics query endpoints backed by SQLAlchemy aggregations."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.schemas.analytics import (
    AnalyticsOverviewResponse,
    ModelAnalyticsItem,
    TopUserAnalyticsItem,
)
from app.db.models.api_request import FactApiRequest
from app.db.session import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _as_float(value: Decimal | float | int | None) -> float:
    """Convert a numeric aggregate to float, defaulting missing values to zero."""
    if value is None:
        return 0.0
    return float(value)


def _as_int(value: int | None) -> int:
    """Convert an integer aggregate to int, defaulting missing values to zero."""
    return 0 if value is None else int(value)


@router.get("/overview", response_model=AnalyticsOverviewResponse)
def get_analytics_overview(
    db: Session = Depends(get_db),
) -> AnalyticsOverviewResponse:
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

    return AnalyticsOverviewResponse(
        total_requests=_as_int(row.total_requests),
        total_cost_usd=_as_float(row.total_cost_usd),
        total_input_tokens=_as_int(row.total_input_tokens),
        total_output_tokens=_as_int(row.total_output_tokens),
        avg_latency_ms=_as_float(row.avg_latency_ms),
        unique_users=_as_int(row.unique_users),
    )


@router.get("/models", response_model=list[ModelAnalyticsItem])
def get_analytics_by_model(
    db: Session = Depends(get_db),
) -> list[ModelAnalyticsItem]:
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
        ModelAnalyticsItem(
            model_name=row.model_name,
            requests=_as_int(row.requests),
            total_cost_usd=_as_float(row.total_cost_usd),
            avg_latency_ms=_as_float(row.avg_latency_ms),
        )
        for row in rows
    ]


@router.get("/top-users", response_model=list[TopUserAnalyticsItem])
def get_top_users_by_cost(
    limit: int = Query(default=5, ge=1, le=100, description="Maximum users to return."),
    db: Session = Depends(get_db),
) -> list[TopUserAnalyticsItem]:
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
        TopUserAnalyticsItem(
            user_email=row.user_email,
            total_cost_usd=_as_float(row.total_cost_usd),
            total_tokens=_as_int(row.total_tokens),
        )
        for row in rows
    ]
