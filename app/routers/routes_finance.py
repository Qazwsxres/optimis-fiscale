from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from typing import List
import csv
from io import TextIOWrapper

router = APIRouter()

# Simple in-memory storage
_bank_summary = {"balance": 0.0, "inflows": 0.0, "outflows": 0.0}
_sales_invoices: List[dict] = []
_purchase_invoices: List[dict] = []

# ---------------- BANK ---------------- #

@router.post("/bank/upload")
async def upload_bank_statement(file: UploadFile = File(...)):
    if file.content_type not in ("text/csv", "application/vnd.ms-excel"):
        raise HTTPException(400, "File must be CSV")

    try:
        wrapper = TextIOWrapper(file.file, encoding="utf-8")
        reader = csv.DictReader(wrapper)

        inflows = 0.0
        outflows = 0.0

        for row in reader:
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
        raise HTTPException(500, f"Error parsing bank file: {e}")


@router.get("/bank/summary")
async def bank_summary():
    return _bank_summary


# ---------------- SALES INVOICES ---------------- #

@router.post("/invoices/sales")
async def upload_sales_invoices(file: UploadFile = File(...)):
    global _sales_invoices
    _sales_invoices = []

    if file.content_type not in ("text/csv", "application/vnd.ms-excel"):
        raise HTTPException(400, "File must be CSV")

    try:
        wrapper = TextIOWrapper(file.file, encoding="utf-8")
        reader = csv.DictReader(wrapper)

        for row in reader:
            inv = {
                "number": row.get("number") or row.get("invoice_number") or "",
                "issue_date": row.get("issue_date") or row.get("date") or "",
                "due_date": row.get("due_date") or "",
                "amount": float(str(row.get("amount") or row.get("total") or "0").replace(",", ".")),
                "status": row.get("status") or "open",
            }
            _sales_invoices.append(inv)

        return {"ok": True, "count": len(_sales_invoices)}

    except Exception as e:
        raise HTTPException(500, f"Error parsing sales file: {e}")


@router.get("/invoices/sales")
async def get_sales_invoices():
    return _sales_invoices


# ---------------- PURCHASE INVOICES ---------------- #

@router.post("/invoices/purchases")
async def upload_purchase_invoices(file: UploadFile = File(...)):
    global _purchase_invoices
    _purchase_invoices = []

    if file.content_type not in ("text/csv", "application/vnd.ms-excel"):
        raise HTTPException(400, "File must be CSV")

    try:
        wrapper = TextIOWrapper(file.file, encoding="utf-8")
        reader = csv.DictReader(wrapper)

        for row in reader:
            inv = {
                "number": row.get("number") or row.get("invoice_number") or "",
                "issue_date": row.get("issue_date") or row.get("date") or "",
                "due_date": row.get("due_date") or "",
                "amount": float(str(row.get("amount") or row.get("total") or "0").replace(",", ".")),
                "status": row.get("status") or "open",
            }
            _purchase_invoices.append(inv)

        return {"ok": True, "count": len(_purchase_invoices)}

    except Exception as e:
        raise HTTPException(500, f"Error parsing purchase file: {e}")


@router.get("/invoices/purchases")
async def get_purchase_invoices():
    return _purchase_invoices
