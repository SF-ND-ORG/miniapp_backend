import json
import re
import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict, Iterable

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


class SQLInjectionMiddleware(BaseHTTPMiddleware):
    """Detect simple SQL injection payloads in query and JSON bodies."""

    def __init__(self, app, patterns: list[str] | None = None, max_body_bytes: int = 131072):
        super().__init__(app)
        default_patterns = patterns or [
            r"union\s+select",
            r"or\s+1=1",
            r"--",
            r"/\*|\*/",
            r";\s*drop\s+table",
            r";\s*delete\s+from",
            r";\s*update\s+",
            r";\s*insert\s+into",
            r"sleep\s*\(\s*\d",
            r"information_schema",
            r"xp_",
        ]
        self._compiled = [re.compile(pat, re.IGNORECASE) for pat in default_patterns]
        self.max_body_bytes = max_body_bytes

    def _iter_strings(self, payload: Any) -> Iterable[str]:
        if isinstance(payload, str):
            yield payload
        elif isinstance(payload, dict):
            for value in payload.values():
                yield from self._iter_strings(value)
        elif isinstance(payload, (list, tuple, set)):
            for value in payload:
                yield from self._iter_strings(value)

    def _is_suspicious(self, value: str) -> bool:
        return any(pattern.search(value) for pattern in self._compiled)

    async def dispatch(self, request: Request, call_next):
        suspicious_keys: list[str] = []

        for key, value in request.query_params.multi_items():
            if value and self._is_suspicious(value):
                suspicious_keys.append(f"query:{key}")

        body_bytes = await request.body()
        if body_bytes:
            if len(body_bytes) > self.max_body_bytes:
                return JSONResponse(
                    status_code=413,
                    content={"detail": "Request body too large"},
                )

            content_type = request.headers.get("content-type", "").lower()
            if "application/json" in content_type:
                try:
                    payload = json.loads(body_bytes.decode("utf-8", errors="ignore"))
                    for value in self._iter_strings(payload):
                        if value and self._is_suspicious(value):
                            suspicious_keys.append("body")
                            break
                except json.JSONDecodeError:
                    pass

        if suspicious_keys:
            return JSONResponse(
                status_code=400,
                content={"detail": "Potential SQL injection detected", "fields": suspicious_keys},
            )

        if body_bytes:
            async def receive():
                return {"type": "http.request", "body": body_bytes, "more_body": False}

            request._receive = receive  # type: ignore[attr-defined]

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
