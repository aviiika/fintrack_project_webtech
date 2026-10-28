from fastapi import APIRouter

from app.schemas.all import NetWorthHistoryPoint, NetWorthSummary
from app.services import networth_service
from app.utils.deps import CurrentUser, DbSession

router = APIRouter(prefix="/networth", tags=["net worth"])


@router.get("", response_model=NetWorthSummary)
async def summary(db: DbSession, cu: CurrentUser):
    return networth_service.net_worth_summary(db, cu.id)


@router.get("/history", response_model=list[NetWorthHistoryPoint])
async def hist(db: DbSession, cu: CurrentUser):
    rows = networth_service.history(db, cu.id)
    return [{"date": r.date, "net_worth": r.net_worth,
             "total_assets": r.total_assets, "total_liabilities": r.total_liabilities} for r in rows]


@router.post("/snapshot", response_model=NetWorthHistoryPoint)
async def snapshot(db: DbSession, cu: CurrentUser):
    """Manually trigger today's snapshot -- the same action the nightly scheduler
    job performs, exposed here so it can be demoed without waiting for cron."""
    s = networth_service.snapshot_now(db, cu.id)
    return {"date": s.date, "net_worth": s.net_worth,
            "total_assets": s.total_assets, "total_liabilities": s.total_liabilities}
