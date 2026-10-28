"""Live(ish) stock price lookups for NSE-listed symbols, via yfinance.

Production concerns handled here, deliberately:
  1. Rate-limit protection -- Yahoo Finance will throttle/block an IP that polls too
     often. Every lookup goes through `price_cache` (TTL = settings.stock_price_cache_ttl_seconds)
     so a WebSocket pushing updates every few seconds, plus several REST calls, all
     collapse onto one upstream fetch per symbol per TTL window.
  2. Graceful degradation -- a college demo (or a viva with no internet) can't depend
     on a third-party API being reachable. If the live fetch fails for any reason
     (network blocked, symbol delisted, Yahoo schema change), we fall back to a
     deterministic mock price instead of a 500. The response always says which mode
     served it (`is_live`), so the fallback is visible, not silently wrong.
"""
import logging
import random
from datetime import UTC, datetime

from app.config import settings
from app.services.cache_service import price_cache

logger = logging.getLogger(__name__)

NSE_SUFFIX = ".NS"  # yfinance convention for NSE-listed tickers

# Last-known reference levels for widely-held NSE tickers, used only when the
# live feed is unreachable. A purely random fallback "works" in the sense that
# nothing crashes, but it prices RELIANCE at 187 and shows the user a 68% loss,
# which is worse than useless -- a wrong number presented confidently. Anchoring
# the offline path to plausible levels keeps the degraded mode *honest* as well
# as functional; the is_live=false flag still tells the UI not to trust it.
REFERENCE_PRICES = {
    "RELIANCE": 2950.0, "TCS": 4100.0, "INFY": 1850.0, "HDFCBANK": 1700.0,
    "ICICIBANK": 1250.0, "SBIN": 820.0, "WIPRO": 540.0, "ITC": 470.0,
    "LT": 3600.0, "AXISBANK": 1150.0, "BHARTIARTL": 1580.0, "HCLTECH": 1780.0,
    "MARUTI": 12500.0, "TATAMOTORS": 980.0, "SUNPHARMA": 1820.0,
    "KOTAKBANK": 1760.0, "ASIANPAINT": 2900.0, "TITAN": 3400.0,
    "BAJFINANCE": 7200.0, "NESTLEIND": 2450.0, "ZOMATO": 270.0, "PAYTM": 950.0,
}


def _mock_price(symbol: str) -> float:
    """Deterministic fallback price when the live feed is unreachable.

    Anchored to a known reference level where we have one, with a small
    deterministic daily drift (+/-3%) seeded by symbol + date -- so the number is
    stable for the whole day (the UI doesn't flicker on every poll) but still
    moves day to day like a real quote would.

    Unknown tickers get a hash-derived price in a plausible mid-cap range rather
    than a wild one.
    """
    rng = random.Random(f"{symbol}:{datetime.now(UTC).toordinal()}")
    base = REFERENCE_PRICES.get(symbol)
    if base is None:
        base = 200 + (sum(ord(c) for c in symbol) * 37) % 2800
    return round(base * rng.uniform(0.97, 1.03), 2)


def _fetch_live_price(symbol: str) -> dict:
    import yfinance as yf  # imported lazily so a missing/broken install doesn't break startup

    ticker = yf.Ticker(f"{symbol}{NSE_SUFFIX}")
    fast = ticker.fast_info
    price = fast.get("lastPrice") if hasattr(fast, "get") else getattr(fast, "last_price", None)
    prev_close = fast.get("previousClose") if hasattr(fast, "get") else getattr(fast, "previous_close", None)
    if not price:
        raise ValueError(f"no live price returned for {symbol}")
    return {
        "symbol": symbol,
        "price": float(price),
        "previous_close": float(prev_close) if prev_close else float(price),
        "is_live": True,
    }


def get_price(symbol: str) -> dict:
    """Cached current price for one symbol (cache-aside pattern)."""
    symbol = symbol.upper().strip()
    cache_key = f"price:{symbol}"
    cached = price_cache.get(cache_key)
    if cached is not None:
        return cached

    try:
        data = _fetch_live_price(symbol)
    except Exception as exc:  # noqa: BLE001 -- any failure degrades to mock, never a 500
        logger.warning("Live price fetch failed for %s (%s) -- serving fallback price", symbol, exc)
        price = _mock_price(symbol)
        data = {"symbol": symbol, "price": price, "previous_close": price, "is_live": False}

    data["fetched_at"] = datetime.now(UTC).isoformat()
    price_cache.set(cache_key, data, settings.stock_price_cache_ttl_seconds)
    return data


def get_prices(symbols: list[str]) -> dict[str, dict]:
    """Batch lookup -- each symbol still goes through the same per-symbol cache entry."""
    return {s.upper().strip(): get_price(s) for s in symbols}
