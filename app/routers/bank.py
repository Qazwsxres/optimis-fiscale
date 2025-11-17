# routes_finance.py
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import List
import csv
from io import TextIOWrapper

router = APIRouter()

# In-memory storage just for demo.
# Replace with your DB / ORM if you have one.
_bank_summary = {
    "balance": 0.0,
    "inflows": 0.0,
    "outflows": 0.0,
}

_sales_invoices: List[dict] = []
_purchase_invoices: List[dict] = []


# ---------- BANK ----------

@router.post("/bank/upload")
async def upload_bank_statement(file: UploadFile = File(...)):
    """
    Accepts a CSV: one row per transaction
    expected columns at least: date, label, amount
    This matches your front-end: uploadGeneric('bankFile','/bank/upload',...)
    """
    if file.content_type not in ("text/csv", "application/vnd.ms-excel"):
        raise HTTPException(status_code=400, detail="File must be CSV")

    try:
        # Parse CSV
        wrapper = TextIOWrapper(file.file, encoding="utf-8")
        reader = csv.DictReader(wrapper)
        inflows = 0.0
        outflows = 0.0
        for row in reader:
            # flexible column name for amount
            raw_amount = (
                row.get("amount")
                or row.get("montant")
                or row.get("Amount")
                or row.get("Montant")
            )
            if raw_amount is None:
                continue
            try:
                amount = float(str(raw_amount).replace(",", "."))
            except ValueError:
                continue

            if amount >= 0:
                inflows += amount
            else:
                outflows += amount

        balance = inflows + outflows
        _bank_summary["balance"] = balance
        _bank_summary["inflows"] = inflows
        _bank_summary["outflows"] = outflows

        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing bank file: {e}")


@router.get("/bank/summary")
async def bank_summary():
    """
    Used by your front-end: fetch(apiBase+'/bank/summary')
    """
    return _bank_summary
