from datetime import date

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models_extended import InvoiceSale, InvoicePurchase

router = APIRouter(prefix="/invoices", tags=["Invoices"])

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://qazwsxres.github.io",
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Methods": "*",
    "Access-Control-Allow-Headers": "*",
}


# ---------- COMMON INPUT MODEL (CSV IMPORT) ----------

class InvoiceIn(BaseModel):
    number: str
    issue_date: date
    due_date: date
    amount: float
    vat: float | None = 0
    status: str = "draft"


# ---------- FULL SALES INVOICE CREATION (UI / API) ----------

class InvoiceCreate(BaseModel):
    client_name: str
    client_email: str | None = None
    number: str
    issue_date: date
    due_date: date
    amount_ht: float
    vat_rate: float = 0.20
    description: str | None = None


@router.post("/sales/create")
def create_sale_invoice(inv: InvoiceCreate):
    """Create a detailed sales invoice (for your future UI form)."""
    with SessionLocal() as db:
        ttc = round(inv.amount_ht * (1 + inv.vat_rate), 2)

        obj = InvoiceSale(
            client_name=inv.client_name,
            client_email=inv.client_email,
            number=inv.number,
            issue_date=inv.issue_date,
            due_date=inv.due_date,
            amount_ht=inv.amount_ht,
            vat_rate=inv.vat_rate,
            amount_ttc=ttc,
            description=inv.description,
            status="unpaid",
        )

        db.add(obj)
        db.commit()
        db.refresh(obj)

        return JSONResponse(
            content={
                "id": obj.id,
                "number": obj.number,
                "client_name": obj.client_name,
                "amount_ttc": float(obj.amount_ttc or 0),
                "status": obj.status,
            },
            headers=CORS_HEADERS,
        )


# ---------- SALES IMPORT (CSV) ----------

@router.post("/sales")
def create_sale(inv: InvoiceIn):
    """
    Import a sales invoice from CSV.

    We map the simple CSV model (amount, vat) to the new InvoiceSale schema
    and store amount as TTC. This keeps the DB consistent AND preserves
    the old frontend contract (loadDashboard still reads `.amount`).
    """
    with SessionLocal() as db:
        obj = InvoiceSale(
            client_name="Import CSV",
            client_email=None,
            number=inv.number,
            issue_date=inv.issue_date,
            due_date=inv.due_date,
            amount_ht=None,          # unknown from CSV
            vat_rate=None,           # unknown from CSV
            amount_ttc=inv.amount,   # store TTC
            description=None,
            status=inv.status or "unpaid",
        )

        db.add(obj)
        db.commit()
        db.refresh(obj)

        return JSONResponse(
            content={
                "id": obj.id,
                "number": obj.number,
                "issue_date": str(obj.issue_date),
                "due_date": str(obj.due_date),
                # FRONTEND EXPECTS `amount` → we send TTC here
                "amount": float(obj.amount_ttc or 0),
                "vat": float(inv.vat or 0),
                "status": obj.status,
            },
            headers=CORS_HEADERS,
        )


@router.get("/sales")
def list_sales():
    """
    List all sales invoices.

    We keep the `amount` field name for backward compatibility with index.html,
    and fill it with amount_ttc.
    """
    with SessionLocal() as db:
        items = db.query(InvoiceSale).order_by(InvoiceSale.issue_date.desc()).all()

        data = [
            {
                "id": i.id,
                "number": i.number,
                "issue_date": str(i.issue_date),
                "due_date": str(i.due_date),
                "client_name": i.client_name,
                "amount": float(i.amount_ttc or 0),  # <= important
                "vat": float(i.vat_rate or 0) if hasattr(i, "vat_rate") else 0.0,
                "status": i.status,
            }
            for i in items
        ]

        return JSONResponse(content=data, headers=CORS_HEADERS)


# ---------- PURCHASES CREATE ----------

@router.post("/purchases")
def create_purchase(inv: InvoiceIn):
    with SessionLocal() as db:
        obj = InvoicePurchase(
            number=inv.number,
            issue_date=inv.issue_date,
            due_date=inv.due_date,
            amount=inv.amount,
            vat=inv.vat or 0,
            status=inv.status,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)

        return JSONResponse(
            content={
                "id": obj.id,
                "number": obj.number,
                "issue_date": str(obj.issue_date),
                "due_date": str(obj.due_date),
                "amount": float(obj.amount),
                "vat": float(obj.vat or 0),
                "status": obj.status,
            },
            headers=CORS_HEADERS,
        )


# ---------- PURCHASES LIST ----------

@router.get("/purchases")
def list_purchases():
    with SessionLocal() as db:
        items = db.query(InvoicePurchase).order_by(InvoicePurchase.issue_date.desc()).all()

        data = [
            {
                "id": i.id,
                "number": i.number,
                "issue_date": str(i.issue_date),
                "due_date": str(i.due_date),
                "amount": float(i.amount or 0),
                "vat": float(i.vat or 0),
                "status": i.status,
            }
            for i in items
        ]

        return JSONResponse(content=data, headers=CORS_HEADERS)


# ---------- CORS PREFLIGHT ----------

@router.options("/{path:path}")
def invoice_preflight(path: str):
    return JSONResponse(content={"ok": True}, headers=CORS_HEADERS)
