"""
Anomaly detection — flags transactions that are statistically unusual relative
to the user's own history in a given category.

Uses z-score (standard deviations above the mean). Explainable, fast,
no training required. For a production system you might upgrade to
Isolation Forest or an autoencoder, but z-score has the virtue of being
fully interpretable: "this transaction is 3.2x your usual Zomato bill."
"""
import math
import statistics

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.transaction import Transaction

MIN_HISTORY = 5          # need at least 5 txns in a category to judge "unusual"
Z_THRESHOLD = 2.5        # flag anything > 2.5 standard deviations above mean


def flag_anomalies(db: Session, owner_id: int, month: str | None = None) -> list[dict]:
    """Return a list of statistically-unusual transactions.

    Groups by category, computes z-score for each debit, flags outliers above
    Z_THRESHOLD. Only looks at debits — large credits (bonuses, refunds) are
    generally good news, not anomalies worth alerting on.
    """
    stmt = select(Transaction).where(
        Transaction.owner_id == owner_id,
        Transaction.txn_type == "debit",
    )
    txns = list(db.scalars(stmt))

    # Group by category
    by_category: dict[str, list[Transaction]] = {}
    for t in txns:
        by_category.setdefault(t.category or "Uncategorized", []).append(t)

    anomalies: list[dict] = []

    for category, items in by_category.items():
        if len(items) < MIN_HISTORY:
            continue
        amounts = [t.amount for t in items]
        mean = statistics.mean(amounts)
        stdev = statistics.pstdev(amounts)
        if stdev == 0:
            continue

        for t in items:
            # Optional month filter — only report anomalies IN the given month
            if month and not t.date.startswith(month):
                continue

            z = (t.amount - mean) / stdev
            if z > Z_THRESHOLD:
                anomalies.append({
                    "id": t.id,
                    "description": t.description,
                    "amount": round(t.amount, 2),
                    "date": t.date,
                    "category": category,
                    "typical_amount": round(mean, 2),
                    "times_above_average": round(t.amount / mean, 1) if mean else 0,
                    "z_score": round(z, 2),
                })

    anomalies.sort(key=lambda a: -a["z_score"])
    return anomalies[:20]  # cap at top 20 most unusual
