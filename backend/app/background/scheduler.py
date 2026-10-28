"""Background jobs, run in-process by APScheduler.

Three jobs, each small and idempotent (safe to double-run, which matters because a
job can overlap itself the first time the process restarts mid-run):

  1. price_cache_warmup       -- every `stock_price_cache_ttl_seconds`, pre-fetch
                                  prices for every distinct symbol held across all
                                  users, so /ws/prices and /portfolio/summary never
                                  block on a cold cache entry.
  2. nightly_networth_snapshot -- once a day, persist a NetWorthSnapshot row per
                                  user, building the time series /networth/history
                                  charts.
  3. nightly_retrain_sweep     -- once a day, re-run the ML categoriser training
                                  pass. Belt-and-braces: the inline trigger in
                                  transaction_service already retrains the moment a
                                  user crosses the correction threshold, but this
                                  catches anyone whose server process restarted
                                  mid-cycle (an in-memory counter reset would
                                  otherwise be lost until the next correction).

Kept out of request/response paths entirely -- nothing here runs inside an HTTP
handler, so a slow upstream (Yahoo Finance, a big retrain) never adds latency to a
user-facing request.
"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.database.session import SessionLocal
from app.ml.training.train_categoriser import train
from app.models.stock_holding import StockHolding
from app.models.user import User
from app.services import networth_service
from app.services.stock_service import get_prices

logger = logging.getLogger(__name__)
# Pinned to UTC explicitly -- APScheduler otherwise asks tzlocal to resolve the
# host's system timezone, which blows up in containers whose TZ env var is a
# legacy alias (e.g. "Asia/Calcutta") that zoneinfo doesn't recognise. Cron hours
# below are UTC; settings.networth_snapshot_hour documents that.
scheduler = AsyncIOScheduler(timezone="UTC")


def price_cache_warmup() -> None:
    db = SessionLocal()
    try:
        symbols = sorted({row[0] for row in db.query(StockHolding.symbol).distinct()})
        if symbols:
            get_prices(symbols)
            logger.info("Price cache warmed for %d symbol(s)", len(symbols))
    finally:
        db.close()


def nightly_networth_snapshot() -> None:
    db = SessionLocal()
    try:
        users = list(db.query(User).all())
        for user in users:
            networth_service.snapshot_now(db, user.id)
        logger.info("Net worth snapshots taken for %d user(s)", len(users))
    finally:
        db.close()


def nightly_retrain_sweep() -> None:
    db = SessionLocal()
    try:
        result = train(db=db)
        logger.info("Nightly retrain sweep: %s", result.get("status"))
    finally:
        db.close()


def start_scheduler() -> None:
    if not settings.enable_background_jobs:
        logger.info("Background jobs disabled (settings.enable_background_jobs=False)")
        return
    if scheduler.running:
        return

    scheduler.add_job(price_cache_warmup, "interval",
                       seconds=settings.stock_price_cache_ttl_seconds,
                       id="price_cache_warmup", replace_existing=True)
    scheduler.add_job(nightly_networth_snapshot, "cron",
                       hour=settings.networth_snapshot_hour,
                       id="nightly_networth_snapshot", replace_existing=True)
    scheduler.add_job(nightly_retrain_sweep, "cron",
                       hour=settings.networth_snapshot_hour, minute=30,
                       id="nightly_retrain_sweep", replace_existing=True)
    scheduler.start()
    logger.info("Background scheduler started (%d jobs)", len(scheduler.get_jobs()))


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
