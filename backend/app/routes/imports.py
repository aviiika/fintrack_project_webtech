from fastapi import APIRouter, HTTPException, UploadFile, File, Form, status
from app.schemas.all import ImportLogRead
from app.services.csv_parser import parse_csv_bytes, list_banks, BANK_FORMATS
from app.services.transaction_service import import_transactions, get_import_history
from app.utils.deps import CurrentUser, DbSession

router = APIRouter(prefix="/import", tags=["import"])
MAX_SIZE_MB = 10

@router.get("/banks")
async def banks(): return {"banks": [{"key": k, "name": v} for k, v in list_banks().items()]}

@router.post("", status_code=status.HTTP_201_CREATED)
async def upload(db: DbSession, cu: CurrentUser,
                  bank: str = Form(...), file: UploadFile = File(...)):
    if bank not in BANK_FORMATS:
        raise HTTPException(400, f"Unknown bank '{bank}'")
    content = await file.read()
    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {MAX_SIZE_MB} MB limit")
    try:
        records = parse_csv_bytes(content, bank, file.filename or "upload.csv")
    except ValueError as e: raise HTTPException(422, str(e))
    if not records: raise HTTPException(422, "No valid transactions found")
    r = import_transactions(db, cu.id, records, file.filename or "upload.csv", bank)
    return {"filename": file.filename, "bank": bank,
            "parsed": r["parsed"], "added": r["added"],
            "skipped": r["parsed"] - r["added"],
            "message": f"Imported {r['added']} new transaction(s). "
                       f"{r['parsed'] - r['added']} duplicate(s) skipped."}

@router.get("/history", response_model=list[ImportLogRead])
async def history(db: DbSession, cu: CurrentUser):
    return get_import_history(db, cu.id)
