"""Portfolio REST endpoints + a live price WebSocket.

The WebSocket is the "advanced web tech" centerpiece of Week 2: instead of the
frontend polling /portfolio/summary every few seconds, it opens one persistent
connection and the server pushes price ticks on an interval.
"""
import asyncio
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from app.config import settings
from app.database.session import SessionLocal
from app.schemas.all import PortfolioSummary, StockHoldingCreate, StockHoldingRead
from app.services import portfolio_service, user_service
from app.services.stock_service import get_prices
from app.utils.deps import CurrentUser, DbSession
from app.utils.security import decode_token

logger = logging.getLogger(__name__)
router = APIRouter(tags=["portfolio"])


@router.get("/portfolio/holdings", response_model=list[StockHoldingRead])
async def list_holdings(db: DbSession, cu: CurrentUser):
    return portfolio_service.list_holdings(db, cu.id)


@router.post("/portfolio/holdings", response_model=StockHoldingRead, status_code=201)
async def add_holding(payload: StockHoldingCreate, db: DbSession, cu: CurrentUser):
    return portfolio_service.create_holding(db, cu.id, payload)


@router.delete("/portfolio/holdings/{hid}", status_code=204)
async def remove_holding(hid: int, db: DbSession, cu: CurrentUser):
    h = portfolio_service.get_holding(db, hid, cu.id)
    if not h:
        raise HTTPException(404, "Holding not found")
    portfolio_service.delete_holding(db, h)


@router.get("/portfolio/summary", response_model=PortfolioSummary)
async def summary(db: DbSession, cu: CurrentUser):
    return portfolio_service.portfolio_summary(db, cu.id)


@router.websocket("/ws/prices")
async def ws_prices(ws: WebSocket, token: str = Query(...)):
    """Stream live prices for the connected user's own holdings.

    Auth note: a browser WebSocket handshake can't carry a custom Authorization
    header, so the JWT travels as a query parameter (?token=...) instead and is
    validated with the same decode_token() used by the REST auth dependency.
    """
    payload = decode_token(token)
    if not payload:
        await ws.close(code=4401)
        return

    await ws.accept()
    db = SessionLocal()
    try:
        user = user_service.get_user(db, int(payload["sub"]))
        if not user or not user.is_active:
            await ws.close(code=4401)
            return

        while True:
            holdings = portfolio_service.list_holdings(db, user.id)
            symbols = sorted({h.symbol for h in holdings})
            # get_prices() is blocking I/O (yfinance HTTP + a sync DB read). Calling it
            # directly here would stall the whole event loop for every connected client
            # -- and the stall is worst exactly when the upstream is slow or unreachable,
            # which is when you least want the server to freeze. Hand it to a thread.
            prices = await asyncio.to_thread(get_prices, symbols) if symbols else {}
            await ws.send_json({
                "type": "price_update",
                "prices": prices,
                "server_time": datetime.now(UTC).isoformat(),
            })
            await asyncio.sleep(settings.ws_push_interval_seconds)
    except WebSocketDisconnect:
        logger.info("Price WebSocket disconnected for user %s", payload.get("sub"))
    finally:
        db.close()
