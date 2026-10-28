"""Net worth = cash + investments - outstanding liabilities.

Ties together three previously-independent subsystems (the transaction ledger,
the stock portfolio, and the loan tracker) into one number -- the kind of
cross-cutting aggregation that's a natural fit for a "Net Worth" dashboard.
"""
from datetime import date

from sqlalchemy import select

from app.models.networth_snapshot import NetWorthSnapshot
from app.models.transaction import Transaction
from app.services import loan_service, portfolio_service


def cash_balance(db, owner_id: int) -> float:
    """Running balance = all credits ever recorded - all debits ever recorded.

    This is a proxy for "cash on hand" built entirely from the imported transaction
    ledger -- there's no separate linked bank-balance feed, so it's necessarily an
    approximation anchored to whatever history has been imported.
    """
    txns = list(db.scalars(select(Transaction).where(Transaction.owner_id == owner_id)))
    credits = sum(t.amount for t in txns if t.txn_type == "credit")
    debits = sum(t.amount for t in txns if t.txn_type == "debit")
    return round(credits - debits, 2)


def net_worth_summary(db, owner_id: int) -> dict:
    cash = cash_balance(db, owner_id)
    portfolio = portfolio_service.portfolio_summary(db, owner_id)
    investments = portfolio["total_current_value"]
    liabilities = [loan_service.liability_with_schedule(l)
                   for l in loan_service.list_liabilities(db, owner_id)]
    total_liabilities = round(sum(l["outstanding_balance"] for l in liabilities), 2)
    total_assets = round(cash + investments, 2)
    return {
        "cash_balance": cash,
        "investments_value": investments,
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "net_worth": round(total_assets - total_liabilities, 2),
        "liabilities": liabilities,
    }


def snapshot_now(db, owner_id: int) -> NetWorthSnapshot:
    """Persist today's net worth (upsert-by-day). Called by the nightly scheduler
    job and also exposed as a manual POST /networth/snapshot for demoing it live."""
    s = net_worth_summary(db, owner_id)
    # Calendar day, not an instant -- one snapshot row per civil day is the whole
    # point of the unique (owner_id, date) constraint on the table.
    today = date.today().isoformat()  # noqa: DTZ011
    existing = db.scalar(select(NetWorthSnapshot).where(
        NetWorthSnapshot.owner_id == owner_id, NetWorthSnapshot.date == today))
    if existing:
        existing.total_assets = s["total_assets"]
        existing.total_liabilities = s["total_liabilities"]
        existing.net_worth = s["net_worth"]
        db.commit(); db.refresh(existing)
        return existing

    snap = NetWorthSnapshot(owner_id=owner_id, date=today,
                             total_assets=s["total_assets"],
                             total_liabilities=s["total_liabilities"],
                             net_worth=s["net_worth"])
    db.add(snap); db.commit(); db.refresh(snap)
    return snap


def history(db, owner_id: int, limit: int = 90) -> list[NetWorthSnapshot]:
    stmt = (select(NetWorthSnapshot)
            .where(NetWorthSnapshot.owner_id == owner_id)
            .order_by(NetWorthSnapshot.date.desc())
            .limit(limit))
    rows = list(db.scalars(stmt))
    rows.reverse()
    return rows
