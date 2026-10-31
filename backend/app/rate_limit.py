"""Per-IP rate limiting for the AI endpoints (NFR-08).

A fixed-window counter held in process memory. That is honest about what it is:
on Vercel each function instance keeps its own counter, so the effective limit
is per instance, not global. It protects API credits against a loop or a stuck
client, which is what the requirement asks for; it is not a security control
and would not stop a distributed attacker.

A durable limiter would need a shared store. That is a deliberate non-goal here
- it would put a database round trip in front of every request to solve a
problem this project does not yet have.
"""

import time
from collections import defaultdict, deque

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.config import Settings

#: Only the endpoints that can spend money on model calls.
RATE_LIMITED_SUFFIXES: tuple[str, ...] = ("/analyse", "/variation-order", "/contracts/draft")


def is_rate_limited_path(path: str) -> bool:
    """True for the endpoints that may call the model."""
    return path.startswith("/api/") and path.endswith(RATE_LIMITED_SUFFIXES)


class FixedWindowLimiter:
    """Counts requests per key inside a rolling window."""

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str, now: float | None = None) -> tuple[bool, int, float]:
        """Record a hit. Returns (allowed, remaining, retry_after_seconds)."""
        now = time.monotonic() if now is None else now
        hits = self._hits[key]
        cutoff = now - self.window_seconds
        while hits and hits[0] <= cutoff:
            hits.popleft()

        if len(hits) >= self.limit:
            retry_after = max(0.0, hits[0] + self.window_seconds - now)
            return False, 0, retry_after

        hits.append(now)
        return True, self.limit - len(hits), 0.0

    def reset(self) -> None:
        self._hits.clear()


#: Process-wide limiter. Held at module level rather than on the middleware
#: instance so tests (and a future admin endpoint) can reset it without
#: reaching into FastAPI's middleware stack.
_limiter: FixedWindowLimiter | None = None


def get_limiter(settings: Settings) -> FixedWindowLimiter:
    """Return the process-wide limiter, building it on first use."""
    global _limiter
    if _limiter is None:
        _limiter = FixedWindowLimiter(
            settings.ai_rate_limit_requests, settings.ai_rate_limit_window_seconds
        )
    return _limiter


def reset_rate_limiter() -> None:
    """Forget every recorded hit. Used between tests."""
    global _limiter
    if _limiter is not None:
        _limiter.reset()
    _limiter = None


class AIRateLimitMiddleware(BaseHTTPMiddleware):
    """Applies the limiter to the AI endpoints only."""

    def __init__(self, app: ASGIApp, settings: Settings) -> None:
        super().__init__(app)
        self._settings = settings

    @staticmethod
    def client_key(request: Request) -> str:
        """Identify the caller.

        Behind Vercel the peer address is a proxy, so the leftmost
        X-Forwarded-For entry is used when present. That header is client
        controlled and trivially spoofed - acceptable for credit protection,
        not for anything security-bearing.
        """
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> JSONResponse:
        if not self._settings.rate_limit_enabled or not is_rate_limited_path(request.url.path):
            return await call_next(request)

        limiter = get_limiter(self._settings)
        allowed, remaining, retry_after = limiter.check(self.client_key(request))
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers={"Retry-After": str(int(retry_after) + 1)},
                content={
                    "detail": {
                        "code": "RATE_LIMITED",
                        "message": (
                            f"Too many AI requests. The limit is "
                            f"{self._settings.ai_rate_limit_requests} per "
                            f"{self._settings.ai_rate_limit_window_seconds}s."
                        ),
                    }
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self._settings.ai_rate_limit_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
