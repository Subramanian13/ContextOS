from __future__ import annotations

import os
import threading
import time
from collections import defaultdict, deque
from hmac import compare_digest

from fastapi import Header, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


def require_demo_write(x_contextos_operator_key: str | None = Header(default=None)) -> None:
    environment = os.getenv("CONTEXTOS_ENV", "development").lower()
    enabled = os.getenv("DEMO_WRITE_ENABLED", "true" if environment == "development" else "false").lower() == "true"
    if not enabled:
        raise HTTPException(status_code=403, detail="This public demo is read-only.")
    expected = os.getenv("DEMO_OPERATOR_KEY", "").strip()
    if expected and (not x_contextos_operator_key or not compare_digest(expected, x_contextos_operator_key)):
        raise HTTPException(status_code=403, detail="A demo operator key is required for this action.")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Small single-process guard; use an edge/distributed limiter in production."""

    def __init__(self, app, window_seconds: int = 60) -> None:
        super().__init__(app)
        self.window = window_seconds
        self.events: dict[str, deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if "/recovery/analyze" in path or "/historical-context" in path:
            limit, bucket = int(os.getenv("AI_RATE_LIMIT_PER_MINUTE", "10")), "ai"
        elif request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            limit, bucket = int(os.getenv("WRITE_RATE_LIMIT_PER_MINUTE", "30")), "write"
        else:
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        key = f"{bucket}:{client}"
        now = time.monotonic()
        with self.lock:
            queue = self.events[key]
            while queue and queue[0] <= now - self.window:
                queue.popleft()
            if len(queue) >= limit:
                return JSONResponse({"detail": "Request rate limit exceeded. Try again later."}, status_code=429)
            queue.append(now)
        return await call_next(request)
