"""Security hardening: response headers + a login rate limiter.

Both are deliberately hand-rolled rather than pulled from a library, because at
this size the implementations are short enough to read in full -- and being able
to explain exactly what a defence does is worth more than a dependency.

Covers four items from the OWASP Top 10:
  A01 Broken Access Control    -- every route already scopes queries by owner_id;
                                   headers here stop the browser-side leaks
                                   (framing, referrer) that access control misses.
  A02 Cryptographic Failures   -- HSTS tells browsers never to downgrade to HTTP.
  A05 Security Misconfiguration-- CSP, nosniff, and frame-deny are the headers a
                                   default FastAPI app does NOT send.
  A07 Auth Failures            -- the rate limiter below makes password brute
                                   force impractical.
"""
import logging
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


SECURITY_HEADERS = {
    # Stop the page being embedded in an attacker's iframe (clickjacking).
    "X-Frame-Options": "DENY",
    # Stop browsers guessing a response is HTML when we said it wasn't.
    "X-Content-Type-Options": "nosniff",
    # Don't leak the full URL (which can carry IDs) to third-party sites.
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # This API serves JSON only, so the strictest possible CSP applies: nothing
    # may be loaded or executed. The React frontend is served separately by Vite
    # (dev) or a static host (prod) and has its own policy.
    "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
    # Deny access to device APIs outright -- an API has no use for them.
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    # Force HTTPS for a year once the app is served over TLS. Harmless on
    # localhost, where browsers ignore HSTS.
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
}


# The interactive API docs (Swagger UI at /docs, ReDoc at /redoc) are the one place
# this server returns HTML. They load their JS/CSS from cdn.jsdelivr.net and run an
# inline bootstrap script, so the blanket `default-src 'none'` policy renders them
# as a blank page. These paths get a narrower-but-working policy instead; every
# other route, including the JSON API itself, keeps the strict one above.
DOCS_PATHS = ("/docs", "/redoc", "/docs/oauth2-redirect")
DOCS_CSP = (
    "default-src 'none'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com data:; "
    "img-src 'self' data: https://fastapi.tiangolo.com https://cdn.redoc.ly; "
    "worker-src blob:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'"
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        headers = dict(SECURITY_HEADERS)
        if request.url.path in DOCS_PATHS:
            headers["Content-Security-Policy"] = DOCS_CSP
        for header, value in headers.items():
            response.headers.setdefault(header, value)
        return response


class RateLimiter:
    """Sliding-window rate limiter, keyed by client IP.

    Why a sliding window and not a simple per-minute counter: a fixed window lets
    an attacker send `limit` requests at 11:59:59 and `limit` more at 12:00:00 --
    double the intended rate across the boundary. Keeping the actual timestamps
    and expiring them individually closes that gap.

    In-memory, so the window resets on restart and isn't shared between workers.
    That's an honest limitation of single-process deployment, and the fix is the
    same shape as the cache: move the deque into Redis.
    """

    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> tuple[bool, int]:
        """Returns (allowed, seconds_until_retry)."""
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] > self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False, int(self.window - (now - hits[0])) + 1
            hits.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


# 10 attempts per 5 minutes per IP. Generous enough that a user fat-fingering
# their password never notices; far too slow for a dictionary attack.
login_limiter = RateLimiter(limit=10, window_seconds=300)

# Paths where a brute-force attempt is actually worth something.
PROTECTED_PATHS = ("/api/v1/auth/login", "/api/v1/auth/token", "/api/v1/auth/register")


class LoginRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "POST" and request.url.path in PROTECTED_PATHS:
            client_ip = request.client.host if request.client else "unknown"
            allowed, retry_after = login_limiter.check(f"{client_ip}:{request.url.path}")
            if not allowed:
                logger.warning("Rate limit hit for %s on %s", client_ip, request.url.path)
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Too many attempts. Please try again later."},
                    headers={"Retry-After": str(retry_after)},
                )
        return await call_next(request)
