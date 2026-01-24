"""
Invoices Router - COMPLET AVEC GET ENDPOINT
Remplacer app/routers/invoices.py par ce fichier
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import date
from typing import Optional
import pandas as pd
import io
import os

router = APIRouter(prefix="/api/invoices", tags=["Invoices"])

from ..database import SessionLocal
from ..models_extended import InvoiceSale, InvoicePurchase, Client, Supplier

FRONTEND_URL = os.getenv("ALLOWED_ORIGIN", "https://qazwsxres.github.io").split(",")[0]

def get_cors_headers():
    return {
        "Access-Control-Allow-Origin": FRONTEND_URL,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "*"
    }

# ============================================
# PYDANTIC MODELS
# ============================================
class InvoiceCreate(BaseModel):
    number: str
    client_name: str
    client_email: Optional[str] = None
    issue_date: date
    due_date: date
    amount_ht: float
    vat_rate: float
    amount_ttc: float
    status: str = "pending"

# ============================================
# 🆕 GET INVOICES (NOUVEAU)
# ============================================
@router.get("/")
def get_invoices(type: Optional[str] = None):
    """
    Liste des factures (ventes et/ou achats)
    
    Query Parameters:
    - type: 'sales' ou 'purchases' (optionnel, défaut = les deux)
    """
    try:
        with SessionLocal() as db:
            invoices = []
            
            # Factures ventes
            if not type or type == "sales":
                sales = db.query(InvoiceSale).order_by(InvoiceSale.issue_date.desc()).all()
                for inv in sales:
                    invoices.append({
                        "id": inv.id,
                        "type": "sale",
                        "number": inv.number,
                        "client": inv.client_name,
                        "email": inv.client_email or "",
                        "amount_ht": float(inv.amount_ht or 0),
                        "vat_rate": float(inv.vat_rate or 0),
                        "amount_ttc": float(inv.amount_ttc or 0),
                        "issue_date": inv.issue_date.isoformat() if inv.issue_date else None,
                        "due_date": inv.due_date.isoformat() if inv.due_date else None,
                        "status": inv.status or "pending"
                    })
            
            # Factures achats
            if not type or type == "purchases":
                purchases = db.query(InvoicePurchase).order_by(InvoicePurchase.issue_date.desc()).all()
                for inv in purchases:
                    invoices.append({
                        "id": inv.id,
                        "type": "purchase",
                        "number": inv.number,
                        "supplier": inv.supplier.name if inv.supplier else "",
                        "amount": float(inv.amount or 0),
                        "vat": float(inv.vat or 0),
                        "issue_date": inv.issue_date.isoformat() if inv.issue_date else None,
                        "due_date": inv.due_date.isoformat() if inv.due_date else None,
                        "status": inv.status or "pending"
                    })
            
            return JSONResponse(
                content=invoices,
                headers=get_cors_headers()
            )
    except Exception as e:
        print(f"❌ Error in get_invoices: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


# ============================================
# GET SALES INVOICES
# ============================================
@router.get("/sales")
def get_sales_invoices():
    """Liste des factures de vente"""
    try:
        with SessionLocal() as db:
            invoices = db.query(InvoiceSale).order_by(InvoiceSale.issue_date.desc()).all()
            
            return JSONResponse(
                content=[{
                    "id": inv.id,
                    "number": inv.number,
                    "client_name": inv.client_name,
                    "client_email": inv.client_email,
                    "issue_date": inv.issue_date.isoformat() if inv.issue_date else None,
                    "due_date": inv.due_date.isoformat() if inv.due_date else None,
                    "amount_ht": float(inv.amount_ht or 0),
                    "vat_rate": float(inv.vat_rate or 0),
                    "amount_ttc": float(inv.amount_ttc or 0),
                    "status": inv.status
                } for inv in invoices],
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


# ============================================
# GET PURCHASE INVOICES
# ============================================
@router.get("/purchases")
def get_purchase_invoices():
    """Liste des factures d'achat"""
    try:
        with SessionLocal() as db:
            invoices = db.query(InvoicePurchase).order_by(InvoicePurchase.issue_date.desc()).all()
            
            return JSONResponse(
                content=[{
                    "id": inv.id,
                    "number": inv.number,
                    "supplier_id": inv.supplier_id,
                    "supplier_name": inv.supplier.name if inv.supplier else "",
                    "issue_date": inv.issue_date.isoformat() if inv.issue_date else None,
                    "due_date": inv.due_date.isoformat() if inv.due_date else None,
                    "amount": float(inv.amount or 0),
                    "vat": float(inv.vat or 0),
                    "status": inv.status
                } for inv in invoices],
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


# ============================================
# POST - UPLOAD SALES INVOICES CSV
# ============================================
@router.post("/sales")
async def upload_sales_invoices(file: UploadFile = File(...)):
    """Upload factures ventes (CSV)"""
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        with SessionLocal() as db:
            count = 0
            for _, row in df.iterrows():
                # Get or create client
                client = db.query(Client).filter(Client.name == row['client_name']).first()
                if not client:
                    client = Client(
                        name=row['client_name'],
                        email=row.get('client_email')
                    )
                    db.add(client)
                    db.flush()
                
                # Create invoice
                invoice = InvoiceSale(
                    number=row['number'],
                    client_id=client.id,
                    client_name=row['client_name'],
                    client_email=row.get('client_email'),
                    issue_date=pd.to_datetime(row['issue_date']).date(),
                    due_date=pd.to_datetime(row['due_date']).date(),
                    amount_ht=float(row['amount_ht']),
                    vat_rate=float(row.get('vat_rate', 20)),
                    amount_ttc=float(row['amount_ttc']),
                    status=row.get('status', 'pending')
                )
                db.add(invoice)
                count += 1
            
            db.commit()
            
            return JSONResponse(
                content={
                    "message": f"{count} factures ventes importées",
                    "count": count
                },
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


# ============================================
# POST - UPLOAD PURCHASE INVOICES CSV
# ============================================
@router.post("/purchases")
async def upload_purchase_invoices(file: UploadFile = File(...)):
    """Upload factures achats (CSV)"""
    try:
        contents = await file.read()
        df = pd.read_csv(io.BytesIO(contents))
        
        with SessionLocal() as db:
            count = 0
            for _, row in df.iterrows():
                # Get or create supplier
                supplier = db.query(Supplier).filter(Supplier.name == row['supplier_name']).first()
                if not supplier:
                    supplier = Supplier(name=row['supplier_name'])
                    db.add(supplier)
                    db.flush()
                
                # Create invoice
                invoice = InvoicePurchase(
                    number=row['number'],
                    supplier_id=supplier.id,
                    issue_date=pd.to_datetime(row['issue_date']).date(),
                    due_date=pd.to_datetime(row['due_date']).date(),
                    amount=float(row['amount']),
                    vat=float(row.get('vat', 0)),
                    status=row.get('status', 'pending')
                )
                db.add(invoice)
                count += 1
            
            db.commit()
            
            return JSONResponse(
                content={
                    "message": f"{count} factures achats importées",
                    "count": count
                },
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


# ============================================
# POST - CREATE SINGLE INVOICE
# ============================================
@router.post("/sales/create")
def create_invoice(invoice: InvoiceCreate):
    """Créer une facture de vente"""
    try:
        with SessionLocal() as db:
            # Get or create client
            client = db.query(Client).filter(Client.name == invoice.client_name).first()
            if not client:
                client = Client(
                    name=invoice.client_name,
                    email=invoice.client_email
                )
                db.add(client)
                db.flush()
            
            # Create invoice
            new_invoice = InvoiceSale(
                number=invoice.number,
                client_id=client.id,
                client_name=invoice.client_name,
                client_email=invoice.client_email,
                issue_date=invoice.issue_date,
                due_date=invoice.due_date,
                amount_ht=invoice.amount_ht,
                vat_rate=invoice.vat_rate,
                amount_ttc=invoice.amount_ttc,
                status=invoice.status
            )
            db.add(new_invoice)
            db.commit()
            db.refresh(new_invoice)
            
            return JSONResponse(
                content={
                    "id": new_invoice.id,
                    "number": new_invoice.number,
                    "message": "Facture créée"
                },
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


print("✅ Invoices router loaded with GET endpoint")
