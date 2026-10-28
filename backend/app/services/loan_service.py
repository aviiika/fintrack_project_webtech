"""EMI math and amortization -- a closed-form financial formula, not a trained model.

Deliberately NOT machine learning: a loan ledger needs to be deterministic and
auditable (a user must be able to recompute their own outstanding balance by hand
and get the same number), so the standard reducing-balance formula used by Indian
banks is the correct tool here, same as z-scores were the correct tool for anomaly
detection rather than another model.
"""
from datetime import date, datetime

from sqlalchemy import select

from app.models.liability import Liability
from app.schemas.all import LiabilityCreate


def calculate_emi(principal: float, annual_rate: float, tenure_months: int) -> float:
    """Standard EMI formula: EMI = P * r * (1+r)^n / ((1+r)^n - 1), r = monthly rate."""
    if annual_rate == 0:
        return round(principal / tenure_months, 2)
    r = annual_rate / 12 / 100
    emi = principal * r * (1 + r) ** tenure_months / ((1 + r) ** tenure_months - 1)
    return round(emi, 2)


def _months_elapsed(start_date: str, as_of: date | None = None) -> int:
    """How many EMIs have fallen due since the loan started.

    Naive (timezone-free) dates on purpose: "which month is it" is a calendar
    question, not an instant in time. A bank doesn't debit your EMI at a UTC
    offset -- it debits it on a calendar day. Attaching a timezone here would add
    a false precision that could shift the month boundary by a few hours and
    change the EMI count at month ends.
    """
    as_of = as_of or date.today()  # noqa: DTZ011 -- calendar date, see docstring
    start = datetime.strptime(start_date, "%Y-%m-%d").date()  # noqa: DTZ007 -- date-only input
    return max(0, (as_of.year - start.year) * 12 + (as_of.month - start.month))


def _outstanding_balance(principal: float, annual_rate: float, tenure_months: int,
                          emi: float, elapsed_months: int) -> float:
    """Reducing balance: each month, interest accrues on what's left, the remainder
    of the EMI pays down principal."""
    elapsed = min(elapsed_months, tenure_months)
    if annual_rate == 0:
        return max(0.0, round(principal - emi * elapsed, 2))
    r = annual_rate / 12 / 100
    balance = principal
    for _ in range(elapsed):
        interest = balance * r
        balance -= (emi - interest)
    return max(0.0, round(balance, 2))


def list_liabilities(db, owner_id: int) -> list[Liability]:
    return list(db.scalars(select(Liability).where(Liability.owner_id == owner_id)))


def get_liability(db, lid: int, owner_id: int) -> Liability | None:
    return db.scalar(select(Liability).where(Liability.id == lid, Liability.owner_id == owner_id))


def create_liability(db, owner_id: int, payload: LiabilityCreate) -> Liability:
    emi = calculate_emi(payload.principal_amount, payload.interest_rate_annual, payload.tenure_months)
    l = Liability(**payload.model_dump(), owner_id=owner_id, emi_amount=emi)
    db.add(l); db.commit(); db.refresh(l)
    return l


def delete_liability(db, l: Liability) -> None:
    db.delete(l); db.commit()


def liability_with_schedule(l: Liability) -> dict:
    """Derive outstanding balance / progress on read -- see module docstring for why
    this is never persisted as a stored column."""
    elapsed = _months_elapsed(l.start_date)
    elapsed_capped = min(elapsed, l.tenure_months)
    remaining = max(0, l.tenure_months - elapsed_capped)
    outstanding = _outstanding_balance(l.principal_amount, l.interest_rate_annual,
                                        l.tenure_months, l.emi_amount, elapsed)
    total_paid = round(l.emi_amount * elapsed_capped, 2)
    total_payable = round(l.emi_amount * l.tenure_months, 2)
    total_interest = round(total_payable - l.principal_amount, 2)
    return {
        "id": l.id, "name": l.name, "liability_type": l.liability_type,
        "principal_amount": l.principal_amount, "interest_rate_annual": l.interest_rate_annual,
        "tenure_months": l.tenure_months, "emi_amount": l.emi_amount, "start_date": l.start_date,
        "months_elapsed": elapsed_capped, "months_remaining": remaining,
        "outstanding_balance": outstanding, "total_interest_payable": total_interest,
        "total_paid_so_far": total_paid,
    }
