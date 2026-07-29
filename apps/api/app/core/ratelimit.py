"""Per-client rate limiting on the standard library.

Sliding window rather than fixed: a fixed window lets a caller send twice the limit
across a boundary. Budgets are per-endpoint because the costs differ wildly. See
the rate-limiting section of the README.
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send


@dataclass(frozen=True)
class Rule:
    limit: int
    window_s: float


# Longest matching prefix wins; unlisted paths aren't limited.
DEFAULT_RULES: tuple[tuple[str, Rule], ...] = (
    ("/auth/login", Rule(limit=5, window_s=60)),
    ("/auth/signup", Rule(limit=10, window_s=3600)),
    ("/auth/forgot-password", Rule(limit=3, window_s=3600)),
    ("/auth/reset-password", Rule(limit=5, window_s=3600)),
    ("/documents", Rule(limit=3, window_s=60)),
    ("/chat", Rule(limit=20, window_s=60)),
)

EXEMPT_PATHS = frozenset({"/health"})  # monitoring polls it

_MAX_TRACKED_KEYS = 10_000


class SlidingWindowLimiter:
    """Request timestamps per key. No lock: all mutation happens on the event loop."""

    def __init__(
        self,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = _MAX_TRACKED_KEYS,
    ) -> None:
        self._clock = clock
        self._max_keys = max_keys
        self._hits: dict[str, deque[float]] = {}

    def check(self, key: str, rule: Rule) -> float | None:
        """Record a request. None if allowed, else the seconds left to wait."""
        now = self._clock()
        cutoff = now - rule.window_s
        hits = self._hits.get(key)
        if hits is None:
            if len(self._hits) >= self._max_keys:
                self._evict(now)
            hits = self._hits.setdefault(key, deque())
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= rule.limit:
            return max(0.0, round(hits[0] + rule.window_s - now, 3))
        hits.append(now)
        return None

    def _evict(self, now: float) -> None:
        """Keep the table bounded against a caller rotating addresses."""
        longest = max(rule.window_s for _, rule in DEFAULT_RULES)
        stale = [k for k, hits in self._hits.items() if not hits or hits[-1] <= now - longest]
        for key in stale:
            del self._hits[key]
        while len(self._hits) >= self._max_keys:  # every key still live; drop oldest first
            self._hits.pop(next(iter(self._hits)))


def match_rule(path: str, rules: tuple[tuple[str, Rule], ...]) -> tuple[str, Rule] | None:
    if path in EXEMPT_PATHS:
        return None
    best: tuple[str, Rule] | None = None
    for prefix, rule in rules:
        if path.startswith(prefix) and (best is None or len(prefix) > len(best[0])):
            best = (prefix, rule)
    return best


class RateLimitMiddleware:
    """429 + Retry-After once a caller is over budget.

    Pure ASGI, not BaseHTTPMiddleware: that class rewraps receive/send, which breaks
    streaming and ``request.is_disconnected()``, and /chat needs both. Register it
    before CORS so CORS stays outermost. A 429 the browser can't read shows up in
    the UI as a generic network error.
    """

    def __init__(
        self,
        app: ASGIApp,
        rules: tuple[tuple[str, Rule], ...] = DEFAULT_RULES,
        trust_proxy_headers: bool = False,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.app = app
        self._rules = rules
        self._trust_proxy_headers = trust_proxy_headers
        self._limiter = SlidingWindowLimiter(clock=clock)

    def _client_key(self, request: Request) -> str:
        # X-Forwarded-For is client-supplied, so trusting it by default would let
        # anyone reset their own budget by varying it.
        if self._trust_proxy_headers:
            forwarded = request.headers.get("x-forwarded-for", "")
            if forwarded:
                return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        matched = match_rule(request.url.path, self._rules)
        if matched is None:
            await self.app(scope, receive, send)
            return

        prefix, rule = matched
        retry_after = self._limiter.check(f"{prefix}|{self._client_key(request)}", rule)
        if retry_after is None:
            await self.app(scope, receive, send)
            return

        await JSONResponse(
            status_code=429,
            content={
                "detail": (
                    f"Too many requests. Limit is {rule.limit} per "
                    f"{int(rule.window_s)}s for this endpoint. "
                    f"Retry in {retry_after:.0f}s."
                )
            },
            headers={"Retry-After": str(max(1, int(retry_after) + 1))},
        )(scope, receive, send)
