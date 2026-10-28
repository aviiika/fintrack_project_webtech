from sqlalchemy import select

from app.models.stock_holding import StockHolding
from app.schemas.all import StockHoldingCreate
from app.services.stock_service import get_prices


def list_holdings(db, owner_id: int) -> list[StockHolding]:
    return list(db.scalars(select(StockHolding).where(StockHolding.owner_id == owner_id)))


def get_holding(db, hid: int, owner_id: int) -> StockHolding | None:
    return db.scalar(select(StockHolding).where(StockHolding.id == hid, StockHolding.owner_id == owner_id))


def create_holding(db, owner_id: int, payload: StockHoldingCreate) -> StockHolding:
    h = StockHolding(**payload.model_dump(), owner_id=owner_id)
    db.add(h); db.commit(); db.refresh(h)
    return h


def delete_holding(db, h: StockHolding) -> None:
    db.delete(h); db.commit()


def portfolio_summary(db, owner_id: int) -> dict:
    """Mark every holding to its live (or cached/fallback) price and roll up gain/loss."""
    holdings = list_holdings(db, owner_id)
    if not holdings:
        return {"holdings": [], "total_invested": 0.0, "total_current_value": 0.0,
                "total_gain_loss": 0.0, "total_gain_loss_pct": 0.0}

    prices = get_prices([h.symbol for h in holdings])
    rows: list[dict] = []
    total_invested = total_current = 0.0

    for h in holdings:
        p = prices[h.symbol.upper().strip()]
        invested = h.quantity * h.avg_buy_price
        current = h.quantity * p["price"]
        gain = current - invested
        rows.append({
            "id": h.id, "symbol": h.symbol, "exchange": h.exchange,
            "quantity": h.quantity, "avg_buy_price": h.avg_buy_price,
            "current_price": p["price"], "is_live": p["is_live"],
            "invested_value": round(invested, 2), "current_value": round(current, 2),
            "gain_loss": round(gain, 2),
            "gain_loss_pct": round((gain / invested * 100) if invested else 0, 2),
        })
        total_invested += invested
        total_current += current

    total_gain = total_current - total_invested
    return {
        "holdings": sorted(rows, key=lambda r: -r["current_value"]),
        "total_invested": round(total_invested, 2),
        "total_current_value": round(total_current, 2),
        "total_gain_loss": round(total_gain, 2),
        "total_gain_loss_pct": round((total_gain / total_invested * 100) if total_invested else 0, 2),
    }
