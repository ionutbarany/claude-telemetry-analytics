"""Pydantic response models for analytics API endpoints."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class AnalyticsOverviewResponse(BaseModel):
    """Platform-wide aggregate metrics across all API request facts."""

    total_requests: int = Field(description="Total number of API requests recorded.")
    total_cost_usd: float = Field(description="Sum of estimated request cost in USD.")
    total_input_tokens: int = Field(description="Sum of input tokens consumed.")
    total_output_tokens: int = Field(description="Sum of output tokens produced.")
    avg_latency_ms: float = Field(description="Mean request duration in milliseconds.")
    unique_users: int = Field(description="Count of distinct user emails with requests.")


class ModelAnalyticsItem(BaseModel):
    """Per-model usage and cost rollup."""

    model_name: str = Field(description="Model identifier from telemetry events.")
    requests: int = Field(description="Number of requests for this model.")
    total_cost_usd: float = Field(description="Sum of estimated cost in USD for this model.")
    avg_latency_ms: float = Field(description="Mean request duration in milliseconds.")


class TopUserAnalyticsItem(BaseModel):
    """Per-user cost and token usage rollup."""

    user_email: str = Field(description="User email from telemetry events.")
    total_cost_usd: float = Field(description="Sum of estimated cost in USD for this user.")
    total_tokens: int = Field(
        description="Sum of input and output tokens consumed by this user."
    )


class PracticeAnalyticsItem(BaseModel):
    """Per-practice cost and usage rollup."""

    practice: str = Field(description="Engineering practice from employee enrichment.")
    requests: int = Field(description="Number of API requests attributed to the practice.")
    total_cost_usd: float = Field(description="Sum of estimated cost in USD for the practice.")
    unique_users: int = Field(description="Distinct users in the practice with requests.")


class LevelAnalyticsItem(BaseModel):
    """Per-level cost and usage rollup."""

    level: str = Field(description="Employee seniority level from employee enrichment.")
    requests: int = Field(description="Number of API requests attributed to the level.")
    total_cost_usd: float = Field(description="Sum of estimated cost in USD for the level.")
    unique_users: int = Field(description="Distinct users at the level with requests.")


class TrendAnalyticsItem(BaseModel):
    """Daily request volume and cost trend point."""

    event_date: date = Field(description="UTC calendar date for the aggregated bucket.")
    requests: int = Field(description="Number of API requests on the date.")
    total_cost_usd: float = Field(description="Sum of estimated cost in USD on the date.")
