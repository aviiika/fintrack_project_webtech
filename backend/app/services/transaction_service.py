"""Transaction CRUD, ML-aware import pipeline, and the correction feedback loop."""
import logging
from collections import defaultdict

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.ml.inference.categoriser_service import predict_batch
from app.models.correction_counter import CorrectionCounter
from app.models.import_log import ImportLog
from app.models.transaction import Transaction
from app.schemas.all import TransactionUpdate

logger = logging.getLogger(__name__)


# ─── Import pipeline (now ML-powered) ────────────────────────────────────────

def import_transactions(
    db: Session,
    owner_id: int,
    records: list[dict],
    filename: str,
    bank: str,
) -> dict:
    """Persist parsed records with ML-powered categorisation.

    Dedup logic unchanged from base: (date, description, amount, bank) is the key.
    Categorisation now goes through predict_batch(), which internally chooses
    ML or rules based on confidence.
    """
    # Dedup first — collect only the records we actually need to categorise
    new_records = []
    for r in records:
        exists = db.scalar(
            select(Transaction.id).where(
                and_(
                    Transaction.owner_id == owner_id,
                    Transaction.date == r["date"],
                    Transaction.description == r["description"],
                    Transaction.amount == r["amount"],
                    Transaction.bank == r["bank"],
                )
            )
        )
        if not exists:
            new_records.append(r)

    if not new_records:
        _log_import(db, owner_id, filename, bank, parsed=len(records), added=0)
        return {"parsed": len(records), "added": 0}

    # Batch-predict categories (ML with rule fallback for low-confidence rows)
    predictions = predict_batch(
        [(r["description"], r["txn_type"]) for r in new_records]
    )

    for r, pred in zip(new_records, predictions):
        db.add(Transaction(
            date=r["date"],
            description=r["description"],
            amount=r["amount"],
            txn_type=r["txn_type"],
            category=pred["category"],
            category_source=pred["source"],
            category_confidence=pred["confidence"],
            user_corrected=False,
            bank=r["bank"],
            source_file=r.get("source_file"),
            balance=r.get("balance"),
            owner_id=owner_id,
        ))

    _log_import(db, owner_id, filename, bank, parsed=len(records), added=len(new_records))
    db.commit()
    return {"parsed": len(records), "added": len(new_records)}


def _log_import(db: Session, owner_id: int, filename: str, bank: str,
                parsed: int, added: int) -> None:
    db.add(ImportLog(filename=filename, bank=bank, rows_parsed=parsed,
                     rows_added=added, owner_id=owner_id))


# ─── CRUD ────────────────────────────────────────────────────────────────────

def get_transaction(db: Session, txn_id: int, owner_id: int):
    return db.scalar(select(Transaction).where(
        Transaction.id == txn_id, Transaction.owner_id == owner_id))


def list_months(db, owner_id) -> list[str]:
    """Distinct YYYY-MM values present in this user's ledger, newest first.

    Dates are stored as ISO strings, so the month is a plain substring -- no
    date parsing needed, and SQLite can do the DISTINCT in one pass.
    """
    rows = db.scalars(
        select(func.substr(Transaction.date, 1, 7))
        .where(Transaction.owner_id == owner_id)
        .distinct()
    )
    return sorted((m for m in rows if m), reverse=True)


def list_transactions(db, owner_id, month=None, bank=None, category=None,
                      txn_type=None, search=None, skip=0, limit=200):
    stmt = select(Transaction).where(Transaction.owner_id == owner_id)
    if month:    stmt = stmt.where(Transaction.date.like(f"{month}%"))
    if bank:     stmt = stmt.where(Transaction.bank == bank)
    if category: stmt = stmt.where(Transaction.category == category)
    if txn_type: stmt = stmt.where(Transaction.txn_type == txn_type)
    if search:   stmt = stmt.where(Transaction.description.ilike(f"%{search}%"))

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = list(db.scalars(stmt.order_by(Transaction.date.desc())
                           .offset(skip).limit(limit)))
    return rows, total or 0


# ─── The feedback loop ───────────────────────────────────────────────────────

def update_transaction(db: Session, txn: Transaction, payload: TransactionUpdate) -> Transaction:
    """Apply an update. If the user is CHANGING THE CATEGORY, treat it as a
    correction: mark it, increment the counter, and trigger a retrain if needed.

    This is the heart of the human-in-the-loop ML system — every correction
    becomes a stronger training example (sample_weight=2 in train_categoriser).
    """
    data = payload.model_dump(exclude_unset=True)
    retrain_triggered = False

    old_category = txn.category
    for field, value in data.items():
        setattr(txn, field, value)

    # Did the category actually change?
    if "category" in data and data["category"] != old_category:
        txn.user_corrected = True
        txn.category_source = "manual"
        txn.category_confidence = 1.0  # user-set = certain
        retrain_triggered = _bump_correction_counter(db, txn.owner_id)

    db.commit()
    db.refresh(txn)

    if retrain_triggered:
        _trigger_retrain(txn.owner_id)

    return txn


def _bump_correction_counter(db: Session, owner_id: int) -> bool:
    """Increment the correction counter. Return True if retrain threshold hit."""
    counter = db.get(CorrectionCounter, owner_id)
    if counter is None:
        counter = CorrectionCounter(owner_id=owner_id, count=0, total_lifetime_corrections=0)
        db.add(counter)
    counter.count += 1
    counter.total_lifetime_corrections += 1
    db.flush()

    if counter.count >= settings.ml_retrain_every_n_corrections:
        counter.count = 0  # reset the cycle
        db.flush()
        return True
    return False


def _trigger_retrain(owner_id: int) -> None:
    """Fire-and-forget retrain. In production this would queue to Celery/RQ;
    here we run inline (acceptable for the data volumes a single user generates)."""
    try:
        from app.ml.training.train_categoriser import train
        result = train()
        logger.info("Auto-retrain triggered (owner=%s): %s", owner_id, result.get("message"))
    except Exception as e:
        logger.error("Auto-retrain failed: %s", e)


def get_correction_status(db: Session, owner_id: int) -> dict:
    """Return the correction counter state — used by the Model Insights page."""
    counter = db.get(CorrectionCounter, owner_id)
    cnt = counter.count if counter else 0
    total = counter.total_lifetime_corrections if counter else 0
    threshold = settings.ml_retrain_every_n_corrections
    return {
        "corrections_this_cycle": cnt,
        "threshold_for_retrain": threshold,
        "total_lifetime_corrections": total,
        "next_retrain_in": max(0, threshold - cnt),
    }


def delete_transaction(db, txn):
    db.delete(txn); db.commit()


# ─── Dashboard aggregations (unchanged) ──────────────────────────────────────

def get_dashboard_stats(db: Session, owner_id: int, month: str,
                        bank: str | None = None) -> dict:
    """Aggregates for one month. When `bank` is given every figure (totals, category
    split, trend, recent list) is computed for that bank only; `banks` always lists
    every bank that has data this month so the UI can offer exactly those filters."""
    base = select(Transaction).where(
        Transaction.owner_id == owner_id,
        Transaction.date.like(f"{month}%"),
    )
    month_txns = list(db.scalars(base))
    bank_counts = defaultdict(int)
    for t in month_txns:
        bank_counts[(t.bank or "").lower()] += 1
    wanted = (bank or "").strip().lower()
    txns = [t for t in month_txns if (t.bank or "").lower() == wanted] if wanted else month_txns
    credits = [t for t in txns if t.txn_type == "credit"]
    debits  = [t for t in txns if t.txn_type == "debit"]

    total_income = round(sum(t.amount for t in credits), 2)
    total_spent  = round(sum(t.amount for t in debits), 2)
    savings      = round(total_income - total_spent, 2)
    savings_rate = round((savings / total_income * 100) if total_income else 0, 1)

    cat_totals = defaultdict(float)
    for t in debits:
        cat_totals[t.category or "Uncategorized"] += t.amount

    daily = defaultdict(float)
    for t in debits:
        daily[t.date] += t.amount

    recent = sorted(txns, key=lambda t: t.date, reverse=True)[:5]
    return {
        "month": month,
        "bank": wanted or None,
        "banks": [{"bank": k, "count": v} for k, v in sorted(bank_counts.items()) if k],
        "total_income": total_income,
        "total_spent": total_spent,
        "savings": savings,
        "savings_rate": savings_rate,
        "transaction_count": len(txns),
        "credit_count": len(credits),
        "debit_count": len(debits),
        "spending_by_category": [{"category": k, "amount": round(v, 2)}
                                 for k, v in sorted(cat_totals.items(), key=lambda x: -x[1])],
        "daily_trend": [{"date": d, "amount": round(a, 2)}
                        for d, a in sorted(daily.items())],
        "recent_transactions": [
            {"id": t.id, "date": t.date, "description": t.description,
             "amount": t.amount, "txn_type": t.txn_type, "category": t.category,
             "bank": t.bank, "balance": t.balance,
             "category_source": t.category_source, "category_confidence": t.category_confidence}
            for t in recent
        ],
    }


def get_annual_stats(db: Session, owner_id: int, year: int) -> dict:
    rows = list(db.scalars(select(Transaction).where(
        Transaction.owner_id == owner_id,
        Transaction.date.like(f"{year}%"),
    )))
    monthly = {f"{year}-{m:02d}": {"income": 0.0, "spending": 0.0} for m in range(1, 13)}
    cat_totals = defaultdict(float)
    bank_totals = defaultdict(float)
    for t in rows:
        mk = t.date[:7]
        if mk in monthly:
            if t.txn_type == "credit":
                monthly[mk]["income"] += t.amount
            else:
                monthly[mk]["spending"] += t.amount
                cat_totals[t.category or "Uncategorized"] += t.amount
                bank_totals[t.bank] += t.amount
    return {
        "year": year,
        "monthly": [{"month": k, "income": round(v["income"], 2),
                     "spending": round(v["spending"], 2)}
                    for k, v in sorted(monthly.items())],
        "top_categories": [{"category": k, "amount": round(v, 2)}
                           for k, v in sorted(cat_totals.items(), key=lambda x: -x[1])[:10]],
        "spending_by_bank": [{"bank": k, "amount": round(v, 2)}
                             for k, v in sorted(bank_totals.items(), key=lambda x: -x[1])],
    }


def get_import_history(db: Session, owner_id: int) -> list:
    return list(db.scalars(select(ImportLog).where(ImportLog.owner_id == owner_id)
                           .order_by(ImportLog.imported_at.desc()).limit(10)))
