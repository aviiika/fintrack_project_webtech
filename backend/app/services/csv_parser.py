"""Multi-bank CSV parser (unchanged from base — same registry)."""
import io
from datetime import datetime
import chardet
import pandas as pd

BANK_FORMATS = {
    "hdfc":  {"name":"HDFC Bank",            "date_col":"Date",             "date_format":"%d/%m/%y",       "desc_col":"Narration",            "debit_col":"Withdrawal Amt.","credit_col":"Deposit Amt.","balance_col":"Closing Balance","amount_col":None},
    "sbi":   {"name":"State Bank of India",  "date_col":"Txn Date",         "date_format":"%d %b %Y",       "desc_col":"Description",          "debit_col":"Debit","credit_col":"Credit","balance_col":"Balance","amount_col":None},
    "icici": {"name":"ICICI Bank",           "date_col":"Transaction Date", "date_format":"%d/%m/%Y",       "desc_col":"Transaction Remarks",  "debit_col":"Withdrawal Amount (INR )","credit_col":"Deposit Amount (INR )","balance_col":"Balance (INR )","amount_col":None},
    "axis":  {"name":"Axis Bank",            "date_col":"Tran Date",        "date_format":"%d-%m-%Y",       "desc_col":"PARTICULARS",          "debit_col":"DR","credit_col":"CR","balance_col":"BAL","amount_col":None},
    "kotak": {"name":"Kotak Mahindra Bank",  "date_col":"Transaction Date", "date_format":"%d-%m-%Y",       "desc_col":"Description",          "debit_col":None,"credit_col":None,"balance_col":"Balance","amount_col":"Amount"},
    "paytm": {"name":"Paytm Payments Bank",  "date_col":"Date",             "date_format":"%Y-%m-%d %H:%M:%S","desc_col":"Comments",           "debit_col":None,"credit_col":None,"balance_col":"Closing Balance","amount_col":"Amount"},
}

def _clean_amount(v):
    if pd.isna(v) or str(v).strip() in ("","-"): return 0.0
    s = str(v).replace(",","").replace(" ","").replace("₹","").strip()
    try: return abs(float(s))
    except ValueError: return 0.0

def _parse_date(v, fmt):
    for f in (fmt, "%d/%m/%Y","%d/%m/%y","%d-%m-%Y","%d %b %Y"):
        try: return datetime.strptime(str(v).strip(), f).strftime("%Y-%m-%d")
        except ValueError: continue
    return None

def parse_csv_bytes(content: bytes, bank_key: str, filename: str) -> list[dict]:
    if bank_key not in BANK_FORMATS:
        raise ValueError(f"Unknown bank key '{bank_key}'. Supported: {', '.join(BANK_FORMATS)}")
    fmt = BANK_FORMATS[bank_key]
    enc = chardet.detect(content).get("encoding") or "utf-8"
    try:
        df = pd.read_csv(io.BytesIO(content), encoding=enc, dtype=str, on_bad_lines="skip")
    except Exception as e:
        raise ValueError(f"Could not parse CSV: {e}") from e
    df.columns = df.columns.str.strip()
    df = df.dropna(how="all")
    records = []
    for _, row in df.iterrows():
        iso = _parse_date(row.get(fmt["date_col"],""), fmt["date_format"] or "%d/%m/%Y")
        if not iso: continue
        desc = str(row.get(fmt["desc_col"],"")).strip() or "Unknown"
        if fmt["amount_col"]:
            raw = str(row.get(fmt["amount_col"],"0")).replace(",","").strip()
            try: signed = float(raw)
            except ValueError: signed = 0.0
            amount, ttype = abs(signed), ("debit" if signed < 0 else "credit")
        else:
            d, c = _clean_amount(row.get(fmt["debit_col"],0)), _clean_amount(row.get(fmt["credit_col"],0))
            if d > 0: amount, ttype = d, "debit"
            elif c > 0: amount, ttype = c, "credit"
            else: continue
        bal = _clean_amount(row.get(fmt["balance_col"], None)) if fmt["balance_col"] else None
        records.append({"date": iso, "description": desc, "amount": round(amount,2),
                        "txn_type": ttype, "balance": round(bal,2) if bal else None,
                        "bank": bank_key, "source_file": filename})
    return records

def list_banks() -> dict:
    return {k: v["name"] for k, v in BANK_FORMATS.items()}
