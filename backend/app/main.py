"""FinTrack Pro FastAPI app — adds /ml router on top of base."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.background.scheduler import shutdown_scheduler, start_scheduler
from app.config import settings
from app.database.session import init_db
from app.routes import (
    auth, budgets, dashboard, exports, imports, loans, ml, networth, portfolio, transactions,
)
from app.utils.logging import configure_logging, get_logger
from app.utils.security_middleware import LoginRateLimitMiddleware, SecurityHeadersMiddleware

logger = get_logger(__name__)
PREFIX = "/api/v1"

@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    logger.info("Starting %s (%s)", settings.app_name, settings.environment)
    init_db()
    logger.info("Database ready")
    start_scheduler()
    yield
    shutdown_scheduler()

app = FastAPI(title=settings.app_name, version="1.0.0-pro", lifespan=lifespan,
              description="FinTrack Pro — ML-powered categorisation, anomaly detection, forecasts, "
                          "live stock portfolio, and net worth tracking.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins_list,
                    allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
# Week 4 hardening. Order matters: middleware is applied bottom-up, so the rate
# limiter added last runs FIRST and can reject a flood before anything else does
# work on it -- which is the entire point of a rate limit.
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoginRateLimitMiddleware)

app.include_router(auth.router,         prefix=PREFIX)
app.include_router(imports.router,      prefix=PREFIX)
app.include_router(transactions.router, prefix=PREFIX)
app.include_router(budgets.router,      prefix=PREFIX)
app.include_router(dashboard.router,    prefix=PREFIX)
app.include_router(ml.router,           prefix=PREFIX)  # ← NEW in Pro (Week 1)
app.include_router(portfolio.router,    prefix=PREFIX)  # ← NEW in Pro (Week 2)
app.include_router(loans.router,        prefix=PREFIX)  # ← NEW in Pro (Week 3)
app.include_router(networth.router,     prefix=PREFIX)  # ← NEW in Pro (Week 3)
app.include_router(exports.router,      prefix=PREFIX)  # ← NEW in Pro (Week 4)

@app.get("/health", tags=["health"])
async def health(): return {"status": "ok", "app": settings.app_name, "version": "pro"}

@app.get("/", tags=["root"])
async def root():
    return {"message": f"{settings.app_name} running", "docs": "/docs", "ml": "/api/v1/ml/model-info"}
