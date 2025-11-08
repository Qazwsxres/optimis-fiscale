from fastapi import APIRouter, HTTPException
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models_extended import InvoiceSale, InvoicePurchase
from pydantic import BaseModel
from datetime import date

router = APIRouter(prefix="/invoices", tags=["Invoices"])

class InvoiceIn(BaseModel):
    number: str
    issue_date: date
    due_date: date
    amount: float
    vat: float | None = 0
    status: str = "draft"

@router.post("/sales")
def create_sale(inv: InvoiceIn):
    with SessionLocal() as db:
        obj = InvoiceSale(**inv.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
    return obj

@router.get("/sales")
def list_sales():
    with SessionLocal() as db:
        items = db.query(InvoiceSale).all()
        return items

@router.post("/purchases")
def create_purchase(inv: InvoiceIn):
    with SessionLocal() as db:
        obj = InvoicePurchase(**inv.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
    return obj

@router.get("/purchases")
def list_purchases():
    with SessionLocal() as db:
        items = db.query(InvoicePurchase).all()
        return items
