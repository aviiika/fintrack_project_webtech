from fastapi import APIRouter, HTTPException, Query
from app.schemas.all import TransactionListResponse, TransactionRead, TransactionUpdate
from app.services import transaction_service
from app.services.categoriser import ALL_CATEGORIES
from app.utils.deps import CurrentUser, DbSession

router = APIRouter(prefix="/transactions", tags=["transactions"])

@router.get("/categories")
async def cats(): return {"categories": ALL_CATEGORIES}

# NOTE: this must stay declared BEFORE the "/{tid}" route below. FastAPI matches
# in declaration order, so a static path registered after a parameterised one
# would be swallowed by it ("months" parsed as an int tid -> 422).
@router.get("/months")
async def months(db: DbSession, cu: CurrentUser):
    """Distinct months that actually contain transactions, newest first.

    The UI uses this to land on a month with data instead of today's month --
    otherwise a user whose statements are a few months old opens the app to an
    empty dashboard and assumes the import failed.
    """
    return {"months": transaction_service.list_months(db, cu.id)}

@router.get("", response_model=TransactionListResponse)
async def list_(db: DbSession, cu: CurrentUser,
                 month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$"),
                 bank: str | None = None, category: str | None = None,
                 txn_type: str | None = Query(None, pattern=r"^(debit|credit)$"),
                 search: str | None = None, skip: int = 0, limit: int = 100):
    rows, total = transaction_service.list_transactions(
        db, cu.id, month=month, bank=bank, category=category,
        txn_type=txn_type, search=search, skip=skip, limit=limit)
    return TransactionListResponse(total=total,
                                    items=[TransactionRead.model_validate(r) for r in rows])

@router.get("/{tid}", response_model=TransactionRead)
async def get_(tid: int, db: DbSession, cu: CurrentUser):
    t = transaction_service.get_transaction(db, tid, cu.id)
    if not t: raise HTTPException(404, "Transaction not found")
    return TransactionRead.model_validate(t)

@router.patch("/{tid}", response_model=TransactionRead)
async def upd(tid: int, payload: TransactionUpdate, db: DbSession, cu: CurrentUser):
    t = transaction_service.get_transaction(db, tid, cu.id)
    if not t: raise HTTPException(404, "Transaction not found")
    return TransactionRead.model_validate(transaction_service.update_transaction(db, t, payload))

@router.delete("/{tid}", status_code=204)
async def del_(tid: int, db: DbSession, cu: CurrentUser):
    t = transaction_service.get_transaction(db, tid, cu.id)
    if not t: raise HTTPException(404, "Transaction not found")
    transaction_service.delete_transaction(db, t)
