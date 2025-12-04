from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import date
from pydantic import BaseModel

from ..database import SessionLocal
from ..models_extended import InvoiceSale, InvoicePurchase

router = APIRouter(prefix="/invoices", tags=["Invoices"])

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://qazwsxres.github.io",
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Methods": "*",
    "Access-Control-Allow-Headers": "*",
}

# ============================================================
#     NEW INVOICE SALES MODEL (HT + TVA + TTC)
# ============================================================

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
    with SessionLocal() as db:

        amount_ttc = round(inv.amount_ht * (1 + inv.vat_rate), 2)

        obj = InvoiceSale(
            client_name=inv.client_name,
            client_email=inv.client_email,
            number=inv.number,
            issue_date=inv.issue_date,
            due_date=inv.due_date,
            amount_ht=inv.amount_ht,
            vat_rate=inv.vat_rate,
            amount_ttc=amount_ttc,
            description=inv.description,
            status="unpaid"
        )

        db.add(obj)
        db.commit()
        db.refresh(obj)

        return JSONResponse(
            content={
                "id": obj.id,
                "client_name": obj.client_name,
                "number": obj.number,
                "amount_ttc": float(obj.amount_ttc),
                "status": obj.status,
            },
            headers=CORS_HEADERS
        )


# ============================================================
#     SALES LIST — RETURN **NEW FIELDS**
# ============================================================

@router.get("/sales")
def list_sales():
    with SessionLocal() as db:
        items = db.query(InvoiceSale).order_by(InvoiceSale.issue_date.desc()).all()

        data = [
            {
                "id": i.id,
                "client_name": i.client_name,
                "number": i.number,
                "issue_date": str(i.issue_date),
                "due_date": str(i.due_date),
                "amount_ht": float(i.amount_ht),
                "vat_rate": float(i.vat_rate),
                "amount_ttc": float(i.amount_ttc),
                "description": i.description,
                "status": i.status,
            }
            for i in items
        ]

        return JSONResponse(content=data, headers=CORS_HEADERS)


# ============================================================
#   MARK INVOICE AS PAID
# ============================================================

@router.put("/sales/{invoice_id}/pay")
def mark_invoice_paid(invoice_id: int):
    with SessionLocal() as db:
        inv = db.query(InvoiceSale).filter(InvoiceSale.id == invoice_id).first()
        if not inv:
            raise HTTPException(404, "Facture introuvable")

        inv.status = "paid"
        db.commit()

        return JSONResponse(
            content={"ok": True, "status": "paid"},
            headers=CORS_HEADERS
        )


# ============================================================
#     PURCHASES — (OLD MODEL LEFT AS IS)
# ============================================================

class InvoiceIn(BaseModel):
    number: str
    issue_date: date
    due_date: date
    amount: float
    vat: float | None = 0
    status: str = "draft"


@router.post("/purchases")
def create_purchase(inv: InvoiceIn):
    with SessionLocal() as db:
        obj = InvoicePurchase(**inv.model_dump())
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
                "vat": float(obj.vat),
                "status": obj.status,
            },
            headers=CORS_HEADERS
        )


@router.get("/purchases")
def list_purchases():
    with SessionLocal() as db:
        items = db.query(InvoicePurchase).all()

        data = [
            {
                "id": i.id,
                "number": i.number,
                "issue_date": str(i.issue_date),
                "due_date": str(i.due_date),
                "amount": float(i.amount),
                "vat": float(i.vat),
                "status": i.status,
            }
            for i in items
        ]

        return JSONResponse(content=data, headers=CORS_HEADERS)


# ============================================================
#     CORS PREFLIGHT
# ============================================================

@router.options("/{path:path}")
def invoice_preflight(path: str):
    return JSONResponse(content={"ok": True}, headers=CORS_HEADERS)
