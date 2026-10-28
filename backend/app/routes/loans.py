from fastapi import APIRouter, HTTPException

from app.schemas.all import LiabilityCreate, LiabilityRead, LiabilityWithSchedule
from app.services import loan_service
from app.utils.deps import CurrentUser, DbSession

router = APIRouter(prefix="/loans", tags=["loans"])


@router.get("", response_model=list[LiabilityWithSchedule])
async def list_(db: DbSession, cu: CurrentUser):
    return [loan_service.liability_with_schedule(l) for l in loan_service.list_liabilities(db, cu.id)]


@router.post("", response_model=LiabilityRead, status_code=201)
async def create(payload: LiabilityCreate, db: DbSession, cu: CurrentUser):
    return loan_service.create_liability(db, cu.id, payload)


@router.delete("/{lid}", status_code=204)
async def delete(lid: int, db: DbSession, cu: CurrentUser):
    l = loan_service.get_liability(db, lid, cu.id)
    if not l:
        raise HTTPException(404, "Loan not found")
    loan_service.delete_liability(db, l)
