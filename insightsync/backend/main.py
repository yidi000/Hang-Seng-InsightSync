from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from insightsync.backend.api import companies, dashboard, insights, rag, signals, timeline
from insightsync.backend.core.config import get_settings
from insightsync.backend.core.security import ApiKeyAuthMiddleware, RateLimitMiddleware
from insightsync.backend.schemas.common import HealthResponse


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(title="InsightSync Backend", version="0.1.0")
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware, settings=settings)
    app.add_middleware(ApiKeyAuthMiddleware, settings=settings)
    app.include_router(companies.router)
    app.include_router(signals.router)
    app.include_router(timeline.router)
    app.include_router(dashboard.router)
    app.include_router(rag.router)
    app.include_router(insights.router)

    @app.get("/healthz", response_model=HealthResponse)
    def healthz() -> HealthResponse:
        """Return service health status."""

        return HealthResponse(status="ok", app_env=settings.app_env)

    return app


app = create_app()


def main() -> None:
    """Run the API server for local development."""

    settings = get_settings()
    uvicorn.run("insightsync.backend.main:app", host="0.0.0.0", port=settings.port, reload=settings.app_env == "local")


if __name__ == "__main__":
    main()
