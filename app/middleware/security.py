import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.services.config_manager import get_rate_limit_settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory sliding window rate limiter."""

    def __init__(self, app, max_requests: int = 120, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        max_requests, window_seconds = get_rate_limit_settings()
        if max_requests != self.max_requests or window_seconds != self.window_seconds:
            self.max_requests = max_requests
            self.window_seconds = window_seconds

        client_ip = request.client.host if request.client else "anonymous"
        now = time.time()
        window_start = now - self.window_seconds

        events = self._requests[client_ip]
        while events and events[0] < window_start:
            events.popleft()

        if len(events) >= self.max_requests:
            retry_after = int(events[0] + self.window_seconds - now) + 1
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests, please slow down.",
                    "retry_after": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        events.append(now)
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add common security headers to API responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        response.headers.setdefault("Cache-Control", "no-store")
        return response
