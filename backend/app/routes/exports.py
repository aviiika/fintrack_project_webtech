"""Download endpoints for CSV / Excel exports."""
from datetime import date

from fastapi import APIRouter, Query
from fastapi.responses import Response

from app.services.export_service import transactions_to_csv, transactions_to_xlsx
from app.utils.deps import CurrentUser, DbSession

router = APIRouter(prefix="/export", tags=["export"])

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/transactions.csv")
async def export_csv(db: DbSession, cu: CurrentUser,
                      month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$")):
    data = transactions_to_csv(db, cu.id, month=month)
    label = month or "all"
    return Response(
        content=data, media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="fintrack_{label}.csv"'},
    )


@router.get("/report.xlsx")
async def export_xlsx(db: DbSession, cu: CurrentUser,
                       month: str | None = Query(None, pattern=r"^\d{4}-\d{2}$")):
    data = transactions_to_xlsx(db, cu.id, month=month)
    # Calendar year for the filename, not an instant -- see loan_service for the
    # same reasoning about naive dates.
    label = month or date.today().strftime("%Y")  # noqa: DTZ011
    return Response(
        content=data, media_type=XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="fintrack_report_{label}.xlsx"'},
    )
