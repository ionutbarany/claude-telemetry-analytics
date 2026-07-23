"""FastAPI application entry point for Claude Telemetry Analytics."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.analytics import router as analytics_router

API_VERSION = "0.1.0"
SERVICE_NAME = "claude-telemetry-analytics-api"

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    """Configure root logging from the LOG_LEVEL environment variable."""
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Emit startup and shutdown log messages for the API process."""
    logger.info("Starting %s v%s", SERVICE_NAME, API_VERSION)
    yield
    logger.info("Shutting down %s", SERVICE_NAME)


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    configure_logging()

    application = FastAPI(
        title="Claude Telemetry Analytics API",
        version=API_VERSION,
        description=(
            "REST API for telemetry ingestion, health checks, and analytics queries."
        ),
        lifespan=lifespan,
    )

    @application.get("/")
    def root() -> dict[str, str]:
        """Return service identity and runtime status."""
        return {
            "service": SERVICE_NAME,
            "version": API_VERSION,
            "status": "running",
        }

    @application.get("/health")
    def health() -> dict[str, str]:
        """Return a simple liveness response for orchestrators."""
        return {"status": "ok"}

    application.include_router(analytics_router)

    return application


app = create_app()
