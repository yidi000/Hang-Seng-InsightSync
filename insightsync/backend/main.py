from __future__ import annotations

import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware

from insightsync.backend.api import companies, copilot, dashboard, insights, metadata, prospects, rag, signals, timeline
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
    app.include_router(prospects.router)
    app.include_router(signals.router)
    app.include_router(timeline.router)
    app.include_router(dashboard.router)
    app.include_router(metadata.router)
    app.include_router(rag.router)
    app.include_router(insights.router)
    app.include_router(copilot.router)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_: object, exc: StarletteHTTPException) -> JSONResponse:
        """Return frontend error shape for endpoints that opt into it."""

        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: object, exc: RequestValidationError) -> JSONResponse:
        """Return a stable validation error while preserving 422 semantics."""

        return JSONResponse(
            status_code=422,
            content={"error": {"code": "VALIDATION_ERROR", "message": "Request validation failed", "details": exc.errors()}},
        )

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
