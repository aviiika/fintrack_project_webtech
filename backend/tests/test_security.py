"""Week 4 hardening: security headers and login rate limiting."""
import pytest

from app.utils.security_middleware import RateLimiter, login_limiter


@pytest.fixture(autouse=True)
def _clear_limiter():
    """The limiter is a process-wide singleton, so one test's attempts would
    otherwise leak into the next and cause order-dependent failures."""
    login_limiter.reset()
    yield
    login_limiter.reset()


def test_security_headers_present_on_every_response(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.headers["X-Frame-Options"] == "DENY"
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert "frame-ancestors 'none'" in r.headers["Content-Security-Policy"]
    assert "max-age=" in r.headers["Strict-Transport-Security"]
    # The JSON API keeps the strictest policy: nothing may load or run.
    assert r.headers["Content-Security-Policy"].startswith("default-src 'none'")
    assert "script-src" not in r.headers["Content-Security-Policy"]


def test_api_docs_csp_allows_swagger_ui_to_load(client):
    """Regression: `default-src 'none'` on /docs blocked Swagger UI's CDN script
    and inline bootstrap, so the page rendered blank in a real browser even though
    the server returned 200 -- which is why an HTTP-status check never caught it."""
    for path in ("/docs", "/redoc"):
        r = client.get(path)
        assert r.status_code == 200
        csp = r.headers["Content-Security-Policy"]
        assert "https://cdn.jsdelivr.net" in csp
        assert "script-src" in csp
        # Still not framable, even on the permissive docs policy.
        assert "frame-ancestors 'none'" in csp


def test_login_rate_limit_blocks_brute_force(client):
    payload = {"email": "nobody@fintrack.app", "password": "wrong-password"}
    # The limit is 10 per window; the first 10 should be processed (and rejected
    # on credentials, i.e. 401), the 11th blocked by the limiter itself (429).
    codes = [client.post("/api/v1/auth/login", json=payload).status_code for _ in range(11)]
    assert codes[:10] == [401] * 10
    assert codes[10] == 429


def test_rate_limited_response_carries_retry_after(client):
    payload = {"email": "nobody@fintrack.app", "password": "wrong-password"}
    for _ in range(11):
        r = client.post("/api/v1/auth/login", json=payload)
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) > 0


def test_rate_limit_does_not_block_normal_reads(client, auth_headers):
    # Only the auth endpoints are limited -- ordinary API traffic must be untouched.
    for _ in range(20):
        r = client.get("/api/v1/transactions", headers=auth_headers)
    assert r.status_code == 200


def test_sliding_window_expires_old_hits():
    """A fixed-window counter would let 2x the limit through across a boundary;
    the sliding window must expire individual timestamps instead."""
    limiter = RateLimiter(limit=2, window_seconds=0.2)
    assert limiter.check("ip")[0] is True
    assert limiter.check("ip")[0] is True
    assert limiter.check("ip")[0] is False  # limit reached

    import time
    time.sleep(0.25)  # window passes
    assert limiter.check("ip")[0] is True  # old hits expired


def test_limiter_keys_are_independent():
    limiter = RateLimiter(limit=1, window_seconds=60)
    assert limiter.check("ip-a")[0] is True
    assert limiter.check("ip-a")[0] is False
    assert limiter.check("ip-b")[0] is True  # a different client is unaffected
