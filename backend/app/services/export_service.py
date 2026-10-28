"""CSV and Excel export of transaction data.

Both exports stream from an in-memory buffer rather than writing a temp file:
these are small (a few thousand rows at most), and not touching the filesystem
means no temp-file cleanup to get wrong and no path-traversal surface.
"""
import io
from collections import defaultdict

from app.services.transaction_service import list_transactions


def transactions_to_csv(db, owner_id: int, month: str | None = None) -> bytes:
    """Flat CSV of transactions -- the format every spreadsheet tool opens."""
    import csv

    rows, _ = list_transactions(db, owner_id, month=month, limit=100_000)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Date", "Description", "Category", "Type", "Amount",
                     "Bank", "Balance", "Category Source", "Confidence", "User Corrected"])
    for t in rows:
        writer.writerow([
            t.date, t.description, t.category or "Uncategorized", t.txn_type,
            f"{t.amount:.2f}", t.bank,
            f"{t.balance:.2f}" if t.balance is not None else "",
            t.category_source or "",
            f"{t.category_confidence:.3f}" if t.category_confidence is not None else "",
            "yes" if t.user_corrected else "no",
        ])
    return buf.getvalue().encode("utf-8")


def transactions_to_xlsx(db, owner_id: int, month: str | None = None) -> bytes:
    """Multi-sheet workbook: all transactions, a category pivot, and a monthly summary.

    Mirrors what the original finance_tracker.py CLI produced as matplotlib PNGs,
    but as a workbook the user can actually pivot and filter themselves.
    """
    import pandas as pd

    rows, _ = list_transactions(db, owner_id, month=month, limit=100_000)

    records = [{
        "Date": t.date, "Description": t.description,
        "Category": t.category or "Uncategorized", "Type": t.txn_type,
        "Amount": t.amount, "Bank": t.bank, "Balance": t.balance,
    } for t in rows]

    df = pd.DataFrame(records) if records else pd.DataFrame(
        columns=["Date", "Description", "Category", "Type", "Amount", "Bank", "Balance"])

    # Category pivot (debits only -- summing spend alongside income is meaningless)
    debits = df[df["Type"] == "debit"] if not df.empty else df
    if not debits.empty:
        by_cat = (debits.groupby("Category")["Amount"]
                  .agg(["sum", "count", "mean"])
                  .rename(columns={"sum": "Total", "count": "Transactions", "mean": "Average"})
                  .sort_values("Total", ascending=False)
                  .round(2)
                  .reset_index())
    else:
        by_cat = pd.DataFrame(columns=["Category", "Total", "Transactions", "Average"])

    # Monthly income vs spending
    monthly = defaultdict(lambda: {"Income": 0.0, "Spending": 0.0})
    for t in rows:
        key = t.date[:7]
        if t.txn_type == "credit":
            monthly[key]["Income"] += t.amount
        else:
            monthly[key]["Spending"] += t.amount
    summary = pd.DataFrame([
        {"Month": k, "Income": round(v["Income"], 2), "Spending": round(v["Spending"], 2),
         "Savings": round(v["Income"] - v["Spending"], 2)}
        for k, v in sorted(monthly.items())
    ]) if monthly else pd.DataFrame(columns=["Month", "Income", "Spending", "Savings"])

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xl:
        df.to_excel(xl, sheet_name="Transactions", index=False)
        by_cat.to_excel(xl, sheet_name="By Category", index=False)
        summary.to_excel(xl, sheet_name="Monthly Summary", index=False)

        # Widen columns so nothing shows as ####
        for sheet_name, frame in [("Transactions", df), ("By Category", by_cat),
                                   ("Monthly Summary", summary)]:
            ws = xl.sheets[sheet_name]
            for i, col in enumerate(frame.columns, start=1):
                longest = max([len(str(col))] + [len(str(v)) for v in frame[col].head(200)]) \
                    if not frame.empty else len(str(col))
                ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = min(longest + 3, 50)

    return buf.getvalue()
