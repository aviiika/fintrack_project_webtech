from datetime import date
from fastapi import APIRouter, Query
from app.services.transaction_service import get_dashboard_stats, get_annual_stats
from app.utils.deps import CurrentUser, DbSession

router = APIRouter(tags=["dashboard"])

@router.get("/dashboard")
async def dashboard(db: DbSession, cu: CurrentUser,
                     month: str = Query(None, pattern=r"^\d{4}-\d{2}$"),
                     bank: str = Query(None, max_length=20, pattern=r"^[A-Za-z0-9_ -]*$")):
    if not month: month = date.today().strftime("%Y-%m")
    return get_dashboard_stats(db, cu.id, month, bank)

@router.get("/reports/annual/{year}")
async def annual(year: int, db: DbSession, cu: CurrentUser):
    return get_annual_stats(db, cu.id, year)
