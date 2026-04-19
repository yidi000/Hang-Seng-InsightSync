from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "ok"
    app_env: str


class PageParams(BaseModel):
    """Validated pagination parameters."""

    limit: int = Field(default=20, ge=1, le=200)
    offset: int = Field(default=0, ge=0)

    model_config = ConfigDict(extra="forbid")
