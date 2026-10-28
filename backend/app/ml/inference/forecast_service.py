"""
Spend forecast — linear-trend extrapolation of cumulative daily spending.

Given spending so far this month, project where the month will end at.
Uses numpy.polyfit (least-squares linear regression). Simple, defensible,
and the right choice given typically-sparse per-user data.

For a report viva: mention that a production version would use
Facebook Prophet or ARIMA to capture weekly seasonality (e.g. weekend
spending spikes, mid-month salary effects), but a linear model is
appropriate when per-user history is limited.
"""
import calendar
from datetime import date

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.budget import Budget
from app.models.transaction import Transaction


def project_month_end(db: Session, owner_id: int, as_of: date | None = None) -> dict:
    """Project this month's total spend based on partial-month data.

    Returns {days_elapsed, days_in_month, spent_so_far, daily_rate,
             projected_month_end, projected_overspend}.
    """
    today = as_of or date.today()
    month_str = today.strftime("%Y-%m")
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_elapsed = today.day

    # Load all debits so far this month
    stmt = select(Transaction).where(
        Transaction.owner_id == owner_id,
        Transaction.txn_type == "debit",
        Transaction.date.like(f"{month_str}%"),
    )
    txns = list(db.scalars(stmt))

    if days_elapsed < 3 or len(txns) < 3:
        return {
            "days_elapsed": days_elapsed,
            "days_in_month": days_in_month,
            "spent_so_far": round(sum(t.amount for t in txns), 2),
            "daily_rate": None,
            "projected_month_end": None,
            "projected_overspend": None,
        }

    # Build day-by-day cumulative array
    daily: dict[int, float] = {}
    for t in txns:
        day = int(t.date.split("-")[2])
        daily[day] = daily.get(day, 0.0) + t.amount
    cumulative = []
    running = 0.0
    for d in range(1, days_elapsed + 1):
        running += daily.get(d, 0.0)
        cumulative.append(running)

    # Linear fit: cumulative_spend = slope * day + intercept
    days = np.arange(1, days_elapsed + 1)
    slope, intercept = np.polyfit(days, cumulative, 1)
    projected = float(slope * days_in_month + intercept)

    # Compare against total budget (sum of all monthly limits for this month)
    total_budget = db.scalar(
        select(Budget).where(
            Budget.owner_id == owner_id,
            (Budget.month == month_str) | (Budget.month.is_(None)),
        )
    )
    # Sum ALL budget limits (above was just checking existence)
    from sqlalchemy import func
    budget_total = db.scalar(
        select(func.sum(Budget.monthly_limit)).where(
            Budget.owner_id == owner_id,
            (Budget.month == month_str) | (Budget.month.is_(None)),
        )
    ) or 0.0
    overspend = round(projected - budget_total, 2) if budget_total > 0 else None

    return {
        "days_elapsed": days_elapsed,
        "days_in_month": days_in_month,
        "spent_so_far": round(cumulative[-1], 2),
        "daily_rate": round(float(slope), 2),
        "projected_month_end": round(projected, 2),
        "projected_overspend": overspend,
    }
