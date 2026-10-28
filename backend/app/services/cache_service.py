"""A tiny in-memory TTL cache that stands in for Redis.

Why not just use Redis directly? For a single-process college deployment, an extra
infra dependency (a Redis container, a connection string, a failure mode when it's
down) buys nothing -- a dict with expiry timestamps gives the same API shape at zero
operational cost. The point being demonstrated is the *caching pattern* (protect a
rate-limited upstream API, keep hot reads fast), not Redis itself.

Because callers only ever use get()/set()/clear(), swapping this for a real Redis
client later is a one-file change: give RedisCache the same three methods and change
one import in stock_service.py. Nothing else in the codebase needs to know.
"""
import time
from threading import Lock


class TTLCache:
    def __init__(self):
        self._store: dict[str, tuple[object, float]] = {}
        self._lock = Lock()

    def get(self, key: str):
        with self._lock:
            item = self._store.get(key)
            if item is None:
                return None
            value, expires_at = item
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value, ttl_seconds: float) -> None:
        with self._lock:
            self._store[key] = (value, time.monotonic() + ttl_seconds)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def stats(self) -> dict:
        with self._lock:
            return {"size": len(self._store), "keys": list(self._store.keys())}


# Process-wide singleton -- every caller shares the same cache, same as a real
# Redis instance would be shared across requests.
price_cache = TTLCache()
