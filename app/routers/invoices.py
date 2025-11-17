from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models_extended import InvoiceSale, InvoicePurchase
from pydantic import BaseModel
from datetime import date

router = APIRouter(prefix="/invoices", tags=["Invoices"])

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://qazwsxres.github.io",
    "Access-Control-Allow-Credentials": "true",
}


class InvoiceIn(BaseModel):
    number: str
    issue_date: date
    due_date: date
    amount: float
    vat: float | None = 0
    status: str = "draft"


# -------------- SALES -----------------

@router.post("/sales")
def create_sale(inv: InvoiceIn):
    with SessionLocal() as db:
        obj = InvoiceSale(**inv.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)

        return JSONResponse(
            content={
                "id": obj.id,
                "number": obj.number,
                "issue_date": str(obj.issue_date),
                "due_date": str(obj.due_date),
                "amount": obj.amount,
                "vat": obj.vat,
                "status": obj.status,
            },
            headers=CORS_HEADERS
        )


@router.get("/sales")
def list_sales():
    with SessionLocal() as db:
        items = db.query(InvoiceSale).all()

        data = [
            {
                "id": i.id,
                "number": i.number,
                "issue_date": str(i.issue_date),
                "due_date": str(i.due_date),
                "amount": i.amount,
                "vat": i.vat,
                "status": i.status,
            }
            for i in items
        ]

        return JSONResponse(content=data, headers=CORS_HEADERS)


# -------------- PURCHASES -----------------

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
                "amount": obj.amount,
                "vat": obj.vat,
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
                "amount": i.amount,
                "vat": i.vat,
                "status": i.status,
            }
            for i in items
        ]

        return JSONResponse(content=data, headers=CORS_HEADERS)
