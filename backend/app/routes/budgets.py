from fastapi import APIRouter, HTTPException, Query
from app.schemas.all import BudgetCreate, BudgetRead, BudgetUpdate, BudgetWithSpending
from app.services import budget_service
from app.utils.deps import CurrentUser, DbSession

router = APIRouter(prefix="/budgets", tags=["budgets"])

@router.get("", response_model=list[BudgetWithSpending])
async def list_(db: DbSession, cu: CurrentUser,
                 month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$")):
    return budget_service.list_budgets(db, cu.id, month)

@router.post("", response_model=BudgetRead, status_code=201)
async def create(payload: BudgetCreate, db: DbSession, cu: CurrentUser):
    return budget_service.create_budget(db, cu.id, payload)

@router.patch("/{bid}", response_model=BudgetRead)
async def upd(bid: int, payload: BudgetUpdate, db: DbSession, cu: CurrentUser):
    b = budget_service.get_budget(db, bid, cu.id)
    if not b: raise HTTPException(404, "Budget not found")
    return budget_service.update_budget(db, b, payload)

@router.delete("/{bid}", status_code=204)
async def del_(bid: int, db: DbSession, cu: CurrentUser):
    b = budget_service.get_budget(db, bid, cu.id)
    if not b: raise HTTPException(404, "Budget not found")
    budget_service.delete_budget(db, b)
