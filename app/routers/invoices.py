"""
COMPLETE invoices.py - COPY THIS ENTIRE FILE
Replace your app/routers/invoices.py with this
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

from app.database import get_db
from app.models_extended import InvoiceSale, InvoicePurchase

router = APIRouter(prefix="/api/invoices", tags=["invoices"])


# ============================================================
# PYDANTIC SCHEMAS
# ============================================================

class InvoiceResponse(BaseModel):
    id: int
    invoice_type: str
    client_name: Optional[str] = None
    number: str
    issue_date: str
    due_date: str
    amount_ht: Optional[float]
    amount_ttc: Optional[float]
    status: str

    class Config:
        from_attributes = True


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/", response_model=List[InvoiceResponse])
async def get_invoices(
    invoice_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    client: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all invoices with filtering"""
    try:
        all_invoices = []
        
        # Determine which types to query
        types_to_query = []
        if invoice_type == "sale":
            types_to_query = [("sale", InvoiceSale)]
        elif invoice_type == "purchase":
            types_to_query = [("purchase", InvoicePurchase)]
        else:
            types_to_query = [("sale", InvoiceSale), ("purchase", InvoicePurchase)]
        
        # Query each type
        for inv_type, Model in types_to_query:
            query = db.query(Model)
            
            if status and hasattr(Model, 'status'):
                query = query.filter(Model.status == status)
            
            if client and hasattr(Model, 'client_name'):
                query = query.filter(Model.client_name.ilike(f"%{client}%"))
            
            if date_from and hasattr(Model, 'issue_date'):
                query = query.filter(Model.issue_date >= date_from)
            
            if date_to and hasattr(Model, 'issue_date'):
                query = query.filter(Model.issue_date <= date_to)
            
            query = query.order_by(Model.issue_date.desc())
            invoices = query.all()
            
            for inv in invoices:
                all_invoices.append(
                    InvoiceResponse(
                        id=inv.id,
                        invoice_type=inv_type,
                        client_name=getattr(inv, 'client_name', None),
                        number=inv.number,
                        issue_date=inv.issue_date.isoformat(),
                        due_date=inv.due_date.isoformat() if inv.due_date else None,
                        amount_ht=float(inv.amount_ht) if inv.amount_ht else None,
                        amount_ttc=float(inv.amount_ttc) if inv.amount_ttc else None,
                        status=inv.status
                    )
                )
        
        # Sort by date
        all_invoices.sort(key=lambda x: x.issue_date, reverse=True)
        
        return all_invoices
        
    except Exception as e:
        print(f"❌ Error in get_invoices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: int,
    invoice_type: str = Query(..., description="sale or purchase"),
    db: Session = Depends(get_db)
):
    """Get a specific invoice"""
    try:
        Model = InvoiceSale if invoice_type == "sale" else InvoicePurchase
        invoice = db.query(Model).filter(Model.id == invoice_id).first()
        
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        return InvoiceResponse(
            id=invoice.id,
            invoice_type=invoice_type,
            client_name=getattr(invoice, 'client_name', None),
            number=invoice.number,
            issue_date=invoice.issue_date.isoformat(),
            due_date=invoice.due_date.isoformat() if invoice.due_date else None,
            amount_ht=float(invoice.amount_ht) if invoice.amount_ht else None,
            amount_ttc=float(invoice.amount_ttc) if invoice.amount_ttc else None,
            status=invoice.status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting invoice: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def invoices_health():
    """Health check"""
    return {
        "status": "ok",
        "router": "invoices",
        "message": "Invoices router with query parameter support"
    }


print("✅ Invoices router loaded with GET endpoint")
