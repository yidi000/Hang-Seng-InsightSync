from __future__ import annotations

import time
from collections import deque
from threading import Lock
from typing import Awaitable, Callable

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from insightsync.backend.core.config import Settings

_API_KEY_HEADER = "X-API-Key"
_PUBLIC_PATHS = {"/healthz", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    """Require X-API-Key header when API_KEYS is configured."""

    def __init__(self, app, settings: Settings) -> None:
        super().__init__(app)
        self._settings = settings

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        keys = self._settings.api_keys
        if not keys or request.url.path in _PUBLIC_PATHS:
            return await call_next(request)
        provided = request.headers.get(_API_KEY_HEADER)
        if not provided or provided not in keys:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid API key"},
            )
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-client fixed-window rate limit. Disabled when rate_limit_per_minute<=0."""

    def __init__(self, app, settings: Settings) -> None:
        super().__init__(app)
        self._settings = settings
        self._hits: dict[str, deque[float]] = {}
        self._lock = Lock()

    def _client_key(self, request: Request) -> str:
        api_key = request.headers.get(_API_KEY_HEADER)
        if api_key:
            return f"key:{api_key}"
        client = request.client
        return f"ip:{client.host}" if client else "ip:unknown"

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        limit = self._settings.rate_limit_per_minute
        if limit <= 0 or request.url.path in _PUBLIC_PATHS:
            return await call_next(request)
        now = time.monotonic()
        window = 60.0
        key = self._client_key(request)
        with self._lock:
            bucket = self._hits.setdefault(key, deque())
            while bucket and now - bucket[0] > window:
                bucket.popleft()
            if len(bucket) >= limit:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "Rate limit exceeded"},
                )
            bucket.append(now)
        return await call_next(request)
