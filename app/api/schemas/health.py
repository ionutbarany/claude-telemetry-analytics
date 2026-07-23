"""Pydantic response models for health check endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Liveness and readiness payload for orchestrators and load balancers."""

    status: str = Field(description="Overall API health status.")
    database: str = Field(description="Database connectivity status.")
    timestamp: str = Field(description="UTC timestamp when the check was performed (ISO 8601).")
