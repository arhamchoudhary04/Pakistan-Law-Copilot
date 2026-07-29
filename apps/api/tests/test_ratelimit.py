"""Rate limiting: the counter, rule matching, and the 429 over HTTP.

The two properties worth having: it refuses a caller past the budget, and spoofing
``X-Forwarded-For`` doesn't buy a fresh one.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.ratelimit import (
    DEFAULT_RULES,
    RateLimitMiddleware,
    Rule,
    SlidingWindowLimiter,
    match_rule,
)
from tests.conftest import signup


class FakeClock:
    """Driven by hand, so no test sleeps."""

    def __init__(self, now: float = 0.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


# ---- the counter ----


def test_requests_are_allowed_up_to_the_limit_then_refused():
    limiter = SlidingWindowLimiter(clock=FakeClock())
    rule = Rule(limit=3, window_s=60)

    assert [limiter.check("k", rule) for _ in range(3)] == [None, None, None]
    refused = limiter.check("k", rule)
    assert refused is not None and refused > 0


def test_the_window_frees_up_as_time_passes():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(clock=clock)
    rule = Rule(limit=2, window_s=10)

    limiter.check("k", rule)
    limiter.check("k", rule)
    assert limiter.check("k", rule) is not None  # at the limit

    clock.now = 10.1  # both hits have aged out
    assert limiter.check("k", rule) is None


def test_the_window_slides_rather_than_resetting_in_blocks():
    """A fixed window would let a caller send 2x the limit across a boundary."""
    clock = FakeClock()
    limiter = SlidingWindowLimiter(clock=clock)
    rule = Rule(limit=2, window_s=10)

    clock.now = 8.0
    assert limiter.check("k", rule) is None
    clock.now = 9.0
    assert limiter.check("k", rule) is None

    clock.now = 10.0  # a fixed window would reset here; both hits are still recent
    assert limiter.check("k", rule) is not None

    clock.now = 18.1  # only now has the t=8 hit left the window
    assert limiter.check("k", rule) is None


def test_retry_after_counts_down_to_when_the_oldest_hit_expires():
    clock = FakeClock()
    limiter = SlidingWindowLimiter(clock=clock)
    rule = Rule(limit=1, window_s=60)

    limiter.check("k", rule)
    clock.now = 20.0
    assert limiter.check("k", rule) == 40.0  # 60s window, 20s elapsed


def test_separate_keys_have_separate_budgets():
    limiter = SlidingWindowLimiter(clock=FakeClock())
    rule = Rule(limit=1, window_s=60)

    assert limiter.check("alice", rule) is None
    assert limiter.check("bob", rule) is None  # unaffected by alice
    assert limiter.check("alice", rule) is not None


def test_tracked_keys_are_bounded_so_rotating_ips_cannot_exhaust_memory():
    limiter = SlidingWindowLimiter(clock=FakeClock(), max_keys=4)
    rule = Rule(limit=10, window_s=60)

    for i in range(50):
        limiter.check(f"ip-{i}", rule)

    assert len(limiter._hits) <= 4


# ---- rule matching ----


def test_each_endpoint_gets_its_own_rule():
    login = match_rule("/auth/login", DEFAULT_RULES)
    chat = match_rule("/chat", DEFAULT_RULES)
    assert login is not None and chat is not None
    assert login[1] != chat[1]
    # Login is the tightest budget: PBKDF2 makes each attempt expensive.
    assert login[1].limit < chat[1].limit


def test_health_is_never_limited_so_monitoring_keeps_working():
    assert match_rule("/health", DEFAULT_RULES) is None


def test_unlisted_paths_are_not_limited():
    assert match_rule("/docs", DEFAULT_RULES) is None
    assert match_rule("/conversations", DEFAULT_RULES) is None


def test_the_longest_matching_prefix_wins():
    rules = (("/a", Rule(1, 60)), ("/a/specific", Rule(99, 60)))
    matched = match_rule("/a/specific", rules)
    assert matched is not None
    assert matched[1].limit == 99


# ---- over HTTP ----


def test_login_starts_refusing_after_the_budget_is_spent(client: TestClient):
    """Unlimited login is both a guessing oracle and a CPU sink."""
    signup(client, "target@example.com")
    limit = dict(DEFAULT_RULES)["/auth/login"].limit
    body = {"email": "target@example.com", "password": "wrong-guess"}

    codes = [client.post("/auth/login", json=body).status_code for _ in range(limit + 1)]
    assert codes[:limit] == [401] * limit
    assert codes[-1] == 429


def test_a_429_tells_the_client_when_to_retry(client: TestClient):
    limit = dict(DEFAULT_RULES)["/auth/login"].limit
    body = {"email": "nobody@example.com", "password": "x"}
    for _ in range(limit):
        client.post("/auth/login", json=body)

    resp = client.post("/auth/login", json=body)
    assert resp.status_code == 429
    assert int(resp.headers["Retry-After"]) > 0
    assert "too many requests" in resp.json()["detail"].lower()


def test_spending_the_login_budget_does_not_block_chat(client: TestClient):
    """One abused route shouldn't take the others down with it."""
    body = {"email": "nobody@example.com", "password": "x"}
    for _ in range(dict(DEFAULT_RULES)["/auth/login"].limit + 1):
        client.post("/auth/login", json=body)

    # /chat has its own budget; 503 here means "no index", i.e. it was not refused.
    assert client.post("/chat", json={"message": "hello"}).status_code == 503


def test_health_survives_a_flood(client: TestClient):
    assert all(client.get("/health").status_code == 200 for _ in range(40))


def test_two_clients_do_not_share_a_budget(test_env):
    from app.main import create_app

    app = create_app()
    body = {"email": "nobody@example.com", "password": "x"}
    limit = dict(DEFAULT_RULES)["/auth/login"].limit

    with TestClient(app, client=("10.0.0.1", 5000)) as first:
        with TestClient(app, client=("10.0.0.2", 5000)) as second:
            for _ in range(limit):
                first.post("/auth/login", json=body)
            assert first.post("/auth/login", json=body).status_code == 429
            # A different address still has its full budget.
            assert second.post("/auth/login", json=body).status_code == 401


def test_a_spoofed_forwarded_for_header_cannot_buy_a_fresh_budget(client: TestClient):
    """X-Forwarded-For is client-supplied, so it must be ignored unless trusted."""
    limit = dict(DEFAULT_RULES)["/auth/login"].limit
    body = {"email": "nobody@example.com", "password": "x"}
    for i in range(limit):
        client.post("/auth/login", json=body, headers={"X-Forwarded-For": f"9.9.9.{i}"})

    resp = client.post("/auth/login", json=body, headers={"X-Forwarded-For": "9.9.9.250"})
    assert resp.status_code == 429


def test_forwarded_for_is_honoured_when_explicitly_trusted(test_env, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_TRUST_PROXY", "true")
    from app.core.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()
    body = {"email": "nobody@example.com", "password": "x"}
    limit = dict(DEFAULT_RULES)["/auth/login"].limit

    with TestClient(create_app()) as proxied:
        for _ in range(limit):
            proxied.post("/auth/login", json=body, headers={"X-Forwarded-For": "203.0.113.7"})
        blocked = proxied.post(
            "/auth/login", json=body, headers={"X-Forwarded-For": "203.0.113.7"}
        )
        other = proxied.post("/auth/login", json=body, headers={"X-Forwarded-For": "203.0.113.8"})

    assert blocked.status_code == 429
    assert other.status_code == 401  # a genuinely different upstream client


def test_a_429_still_carries_cors_headers_so_the_browser_can_read_it(client: TestClient):
    """The reason the limiter is registered before CORS."""
    body = {"email": "nobody@example.com", "password": "x"}
    origin = {"Origin": "http://localhost:3000"}
    for _ in range(dict(DEFAULT_RULES)["/auth/login"].limit):
        client.post("/auth/login", json=body, headers=origin)

    resp = client.post("/auth/login", json=body, headers=origin)
    assert resp.status_code == 429
    assert resp.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_rate_limiting_can_be_switched_off(test_env, monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
    from app.core.config import get_settings
    from app.main import create_app

    get_settings.cache_clear()
    body = {"email": "nobody@example.com", "password": "x"}

    with TestClient(create_app()) as unlimited:
        codes = {unlimited.post("/auth/login", json=body).status_code for _ in range(8)}
    assert codes == {401}


def test_the_middleware_passes_non_http_scopes_straight_through():
    seen: list[str] = []

    async def app(scope, receive, send):
        seen.append(scope["type"])

    middleware = RateLimitMiddleware(app)

    import asyncio

    asyncio.run(middleware({"type": "lifespan"}, None, None))  # type: ignore[arg-type]
    assert seen == ["lifespan"]
