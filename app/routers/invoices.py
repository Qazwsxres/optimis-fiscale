import os
import csv
from datetime import date, datetime
from io import StringIO, TextIOWrapper
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..database import SessionLocal
from ..models_extended import InvoiceSale, InvoicePurchase

router = APIRouter(prefix="/invoices", tags=["Invoices"])

# Get CORS origin from environment
FRONTEND_URL = os.getenv("ALLOWED_ORIGIN", "https://qazwsxres.github.io").split(",")[0]

def get_cors_headers():
    """Standard CORS headers for all responses"""
    return {
        "Access-Control-Allow-Origin": FRONTEND_URL,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "*"
    }


def parse_date(date_str: str) -> date:
    """Parse date from various formats"""
    if not date_str or not date_str.strip():
        return None
    
    date_str = date_str.strip().split(" ")[0]  # Remove time if present
    
    # Try ISO format first (YYYY-MM-DD)
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        pass
    
    # Try other formats
    for fmt in ["%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]:
        try:
            return datetime.strptime(date_str, fmt).date()
        except:
            continue
    
    return None


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
    try:
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
                headers=get_cors_headers(),
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


# ---------- SALES CSV IMPORT ----------

@router.post("/sales")
async def upload_sales_csv(file: UploadFile = File(...)):
    """
    Import sales invoices from CSV file.
    
    Expected columns: number, issue_date, due_date, amount, status
    """
    try:
        # Read file content
        content = await file.read()
        text = content.decode('utf-8')
        
        # Parse CSV
        csv_file = StringIO(text)
        reader = csv.DictReader(csv_file)
        
        created_count = 0
        errors = []
        
        with SessionLocal() as db:
            for idx, row in enumerate(reader, start=2):  # Start at 2 (header is line 1)
                try:
                    # Get invoice number
                    number = (row.get("number") or row.get("invoice_number") or "").strip()
                    if not number:
                        continue
                    
                    # Parse dates
                    issue_date = parse_date(row.get("issue_date") or row.get("date") or "")
                    due_date = parse_date(row.get("due_date") or "")
                    
                    if not issue_date or not due_date:
                        errors.append(f"Line {idx}: Invalid date format")
                        continue
                    
                    # Parse amount
                    amount_str = str(row.get("amount") or row.get("total") or "0")
                    amount_str = amount_str.replace(",", ".").strip()
                    
                    try:
                        amount = float(amount_str)
                    except:
                        errors.append(f"Line {idx}: Invalid amount '{amount_str}'")
                        continue
                    
                    # Get status
                    status = (row.get("status") or "unpaid").strip().lower()
                    
                    # Create invoice
                    obj = InvoiceSale(
                        client_name="Import CSV",
                        client_email=None,
                        number=number,
                        issue_date=issue_date,
                        due_date=due_date,
                        amount_ht=None,
                        vat_rate=None,
                        amount_ttc=amount,
                        description=None,
                        status=status,
                    )
                    
                    db.add(obj)
                    created_count += 1
                    
                except Exception as e:
                    errors.append(f"Line {idx}: {str(e)}")
                    continue
            
            db.commit()
        
        return JSONResponse(
            content={
                "ok": True,
                "count": created_count,
                "message": f"{created_count} invoices imported",
                "errors": errors if errors else None
            },
            headers=get_cors_headers()
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error parsing CSV: {str(e)}"},
            headers=get_cors_headers()
        )


@router.get("/sales")
def list_sales():
    """List all sales invoices."""
    try:
        with SessionLocal() as db:
            items = db.query(InvoiceSale).order_by(InvoiceSale.issue_date.desc()).all()

            data = [
                {
                    "id": i.id,
                    "number": i.number,
                    "issue_date": str(i.issue_date),
                    "due_date": str(i.due_date),
                    "client_name": i.client_name,
                    "amount": float(i.amount_ttc or 0),
                    "vat": float(i.vat_rate or 0) if hasattr(i, "vat_rate") else 0.0,
                    "status": i.status,
                }
                for i in items
            ]

            return JSONResponse(
                content=data,
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


# ---------- PURCHASES CSV IMPORT ----------

@router.post("/purchases")
async def upload_purchases_csv(file: UploadFile = File(...)):
    """Import purchase invoices from CSV file."""
    try:
        # Read file content
        content = await file.read()
        text = content.decode('utf-8')
        
        # Parse CSV
        csv_file = StringIO(text)
        reader = csv.DictReader(csv_file)
        
        created_count = 0
        errors = []
        
        with SessionLocal() as db:
            for idx, row in enumerate(reader, start=2):
                try:
                    number = (row.get("number") or row.get("invoice_number") or "").strip()
                    if not number:
                        continue
                    
                    # Parse dates
                    issue_date = parse_date(row.get("issue_date") or row.get("date") or "")
                    due_date = parse_date(row.get("due_date") or "")
                    
                    if not issue_date or not due_date:
                        errors.append(f"Line {idx}: Invalid date format")
                        continue
                    
                    # Parse amount
                    amount_str = str(row.get("amount") or row.get("total") or "0")
                    amount_str = amount_str.replace(",", ".").strip()
                    
                    try:
                        amount = float(amount_str)
                    except:
                        errors.append(f"Line {idx}: Invalid amount")
                        continue
                    
                    status = (row.get("status") or "pending").strip().lower()
                    
                    # Create invoice
                    obj = InvoicePurchase(
                        number=number,
                        issue_date=issue_date,
                        due_date=due_date,
                        amount=amount,
                        vat=0,
                        status=status,
                    )
                    
                    db.add(obj)
                    created_count += 1
                    
                except Exception as e:
                    errors.append(f"Line {idx}: {str(e)}")
                    continue
            
            db.commit()
        
        return JSONResponse(
            content={
                "ok": True,
                "count": created_count,
                "message": f"{created_count} purchase invoices imported",
                "errors": errors if errors else None
            },
            headers=get_cors_headers()
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Error parsing CSV: {str(e)}"},
            headers=get_cors_headers()
        )


# ---------- PURCHASES LIST ----------

@router.get("/purchases")
def list_purchases():
    try:
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

            return JSONResponse(
                content=data,
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )
