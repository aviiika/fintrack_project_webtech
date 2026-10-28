from sqlalchemy import and_, select
from sqlalchemy.orm import Session
from app.models.budget import Budget
from app.models.transaction import Transaction
from app.schemas.all import BudgetCreate, BudgetUpdate

def list_budgets(db, owner_id, month=None):
    stmt = select(Budget).where(Budget.owner_id == owner_id)
    if month:
        stmt = stmt.where((Budget.month == month) | (Budget.month.is_(None)))
    budgets = list(db.scalars(stmt))
    out = []
    for b in budgets:
        q = select(Transaction).where(and_(
            Transaction.owner_id == owner_id,
            Transaction.category == b.category,
            Transaction.txn_type == "debit"))
        if month: q = q.where(Transaction.date.like(f"{month}%"))
        spent = round(sum(t.amount for t in db.scalars(q)), 2)
        pct = round((spent / b.monthly_limit * 100) if b.monthly_limit else 0, 1)
        out.append({"id": b.id, "category": b.category, "month": b.month,
                    "monthly_limit": b.monthly_limit, "spent": spent,
                    "remaining": round(b.monthly_limit - spent, 2),
                    "percent_used": min(pct, 100), "over_budget": spent > b.monthly_limit,
                    "status": "over" if spent > b.monthly_limit else ("warning" if pct >= 80 else "ok")})
    return sorted(out, key=lambda x: -x["spent"])

def get_budget(db, bid, owner_id):
    return db.scalar(select(Budget).where(Budget.id == bid, Budget.owner_id == owner_id))

def create_budget(db, owner_id, payload: BudgetCreate):
    b = Budget(**payload.model_dump(), owner_id=owner_id)
    db.add(b); db.commit(); db.refresh(b); return b

def update_budget(db, b, payload: BudgetUpdate):
    for k, v in payload.model_dump(exclude_unset=True).items(): setattr(b, k, v)
    db.commit(); db.refresh(b); return b

def delete_budget(db, b):
    db.delete(b); db.commit()
