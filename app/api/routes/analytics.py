"""Analytics query endpoints backed by SQLAlchemy aggregations."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.schemas.analytics import (
    AnalyticsOverviewResponse,
    LevelAnalyticsItem,
    ModelAnalyticsItem,
    PracticeAnalyticsItem,
    TopUserAnalyticsItem,
    TrendAnalyticsItem,
)
from app.db.session import get_db
from app.services import analytics as analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverviewResponse)
def get_analytics_overview(
    db: Session = Depends(get_db),
) -> AnalyticsOverviewResponse:
    """Return platform-wide totals for requests, cost, tokens, latency, and users."""
    metrics = analytics_service.fetch_overview_metrics(db)
    return AnalyticsOverviewResponse(
        total_requests=metrics.total_requests,
        total_cost_usd=metrics.total_cost_usd,
        total_input_tokens=metrics.total_input_tokens,
        total_output_tokens=metrics.total_output_tokens,
        avg_latency_ms=metrics.avg_latency_ms,
        unique_users=metrics.unique_users,
    )


@router.get("/models", response_model=list[ModelAnalyticsItem])
def get_analytics_by_model(
    db: Session = Depends(get_db),
) -> list[ModelAnalyticsItem]:
    """Return per-model request counts, cost, and average latency."""
    return [
        ModelAnalyticsItem(
            model_name=item.model_name,
            requests=item.requests,
            total_cost_usd=item.total_cost_usd,
            avg_latency_ms=item.avg_latency_ms,
        )
        for item in analytics_service.fetch_model_metrics(db)
    ]


@router.get("/top-users", response_model=list[TopUserAnalyticsItem])
def get_top_users_by_cost(
    limit: int = Query(default=5, ge=1, le=100, description="Maximum users to return."),
    db: Session = Depends(get_db),
) -> list[TopUserAnalyticsItem]:
    """Return the highest-spending users ranked by total cost."""
    return [
        TopUserAnalyticsItem(
            user_email=item.user_email,
            total_cost_usd=item.total_cost_usd,
            total_tokens=item.total_tokens,
        )
        for item in analytics_service.fetch_top_users(db, limit)
    ]


@router.get("/practices", response_model=list[PracticeAnalyticsItem])
def get_analytics_by_practice(
    db: Session = Depends(get_db),
) -> list[PracticeAnalyticsItem]:
    """Return cost and usage rollups grouped by engineering practice."""
    return [
        PracticeAnalyticsItem(
            practice=item.practice,
            requests=item.requests,
            total_cost_usd=item.total_cost_usd,
            unique_users=item.unique_users,
        )
        for item in analytics_service.fetch_practice_metrics(db)
    ]


@router.get("/levels", response_model=list[LevelAnalyticsItem])
def get_analytics_by_level(
    db: Session = Depends(get_db),
) -> list[LevelAnalyticsItem]:
    """Return cost and usage rollups grouped by employee level."""
    return [
        LevelAnalyticsItem(
            level=item.level,
            requests=item.requests,
            total_cost_usd=item.total_cost_usd,
            unique_users=item.unique_users,
        )
        for item in analytics_service.fetch_level_metrics(db)
    ]


@router.get("/trends", response_model=list[TrendAnalyticsItem])
def get_daily_trends(
    db: Session = Depends(get_db),
) -> list[TrendAnalyticsItem]:
    """Return daily request volume and cost trends."""
    return [
        TrendAnalyticsItem(
            event_date=item.event_date,
            requests=item.requests,
            total_cost_usd=item.total_cost_usd,
        )
        for item in analytics_service.fetch_daily_trends(db)
    ]
