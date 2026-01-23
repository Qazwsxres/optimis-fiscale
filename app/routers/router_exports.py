"""
Exports Router - FEC, CSV, Excel, PDF exports
"""

import os
import csv
import io
from datetime import date, datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional

from ..database import SessionLocal
from ..models_banking import BankTransactionEnhanced, BankAccount, Category
from ..models_extended import InvoiceSale, InvoicePurchase

router = APIRouter(prefix="/api/exports", tags=["Exports"])

FRONTEND_URL = os.getenv("ALLOWED_ORIGIN", "https://qazwsxres.github.io").split(",")[0]

def get_cors_headers():
    return {
        "Access-Control-Allow-Origin": FRONTEND_URL,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "*"
    }

# ============================================
# EXPORT TRANSACTIONS CSV
# ============================================

@router.get("/transactions/csv")
def export_transactions_csv(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    account_id: Optional[int] = None
):
    """Export transactions to CSV"""
    try:
        with SessionLocal() as db:
            query = db.query(BankTransactionEnhanced)
            
            if start_date:
                query = query.filter(BankTransactionEnhanced.date >= start_date)
            if end_date:
                query = query.filter(BankTransactionEnhanced.date <= end_date)
            if account_id:
                query = query.filter(BankTransactionEnhanced.account_id == account_id)
            
            transactions = query.order_by(BankTransactionEnhanced.date.desc()).all()
            
            # Create CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Header
            writer.writerow([
                'Date', 'Account', 'Label', 'Amount', 'Balance', 
                'Category', 'Is Recurring', 'External ID'
            ])
            
            # Data
            for trans in transactions:
                account = db.query(BankAccount)\
                    .filter(BankAccount.id == trans.account_id)\
                    .first()
                
                category = db.query(Category)\
                    .filter(Category.id == trans.category_id)\
                    .first() if trans.category_id else None
                
                writer.writerow([
                    trans.date.isoformat(),
                    account.name if account else '',
                    trans.label or '',
                    float(trans.amount),
                    float(trans.balance) if trans.balance else '',
                    category.name if category else '',
                    'Yes' if trans.is_recurring else 'No',
                    trans.external_id or ''
                ])
            
            output.seek(0)
            
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode('utf-8')),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=transactions_{datetime.now().strftime('%Y%m%d')}.csv",
                    **get_cors_headers()
                }
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )

# ============================================
# EXPORT FEC (Fichier des Écritures Comptables)
# ============================================

@router.get("/fec")
def export_fec(year: int):
    """
    Export FEC format (required by French tax authorities)
    
    Format: Pipe-separated (|) with specific columns
    Required for French companies' accounting audits
    """
    try:
        with SessionLocal() as db:
            # Get transactions for the year
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)
            
            transactions = db.query(BankTransactionEnhanced)\
                .filter(
                    BankTransactionEnhanced.date >= start_date,
                    BankTransactionEnhanced.date <= end_date
                )\
                .order_by(BankTransactionEnhanced.date)\
                .all()
            
            # Create FEC file
            output = io.StringIO()
            
            # FEC Header (pipe-separated)
            header = [
                'JournalCode',      # Code journal
                'JournalLib',       # Libellé journal
                'EcritureNum',      # Numéro écriture
                'EcritureDate',     # Date écriture (YYYYMMDD)
                'CompteNum',        # Numéro compte
                'CompteLib',        # Libellé compte
                'CompAuxNum',       # Compte auxiliaire (optionnel)
                'CompAuxLib',       # Libellé compte auxiliaire
                'PieceRef',         # Référence pièce
                'PieceDate',        # Date pièce (YYYYMMDD)
                'EcritureLib',      # Libellé écriture
                'Debit',            # Montant débit
                'Credit',           # Montant crédit
                'EcritureLet',      # Lettrage (optionnel)
                'DateLet',          # Date lettrage
                'ValidDate',        # Date validation (YYYYMMDD)
                'Montantdevise',    # Montant devise
                'Idevise'           # Code devise
            ]
            output.write('|'.join(header) + '\n')
            
            # Data rows
            for idx, trans in enumerate(transactions, start=1):
                account = db.query(BankAccount)\
                    .filter(BankAccount.id == trans.account_id)\
                    .first()
                
                # Determine debit/credit
                debit = float(trans.amount) if trans.amount > 0 else 0
                credit = abs(float(trans.amount)) if trans.amount < 0 else 0
                
                row = [
                    'BQ',                                          # JournalCode (Banque)
                    'Journal Banque',                              # JournalLib
                    f'BQ{year}{idx:06d}',                         # EcritureNum
                    trans.date.strftime('%Y%m%d'),                 # EcritureDate
                    '512000',                                      # CompteNum (512 = Banque)
                    account.name if account else 'Banque',         # CompteLib
                    '',                                            # CompAuxNum
                    '',                                            # CompAuxLib
                    trans.external_id or f'REF{idx}',             # PieceRef
                    trans.date.strftime('%Y%m%d'),                 # PieceDate
                    (trans.label or 'Transaction')[:100],          # EcritureLib (max 100 chars)
                    f'{debit:.2f}',                                # Debit
                    f'{credit:.2f}',                               # Credit
                    '',                                            # EcritureLet
                    '',                                            # DateLet
                    trans.date.strftime('%Y%m%d'),                 # ValidDate
                    f'{abs(float(trans.amount)):.2f}',            # Montantdevise
                    'EUR'                                          # Idevise
                ]
                output.write('|'.join(row) + '\n')
            
            output.seek(0)
            
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode('utf-8')),
                media_type="text/plain",
                headers={
                    "Content-Disposition": f"attachment; filename=FEC_{year}_NUMMA.txt",
                    **get_cors_headers()
                }
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )

# ============================================
# EXPORT INVOICES CSV
# ============================================

@router.get("/invoices/csv")
def export_invoices_csv(invoice_type: str = "sales"):
    """Export invoices (sales or purchases) to CSV"""
    try:
        with SessionLocal() as db:
            if invoice_type == "sales":
                invoices = db.query(InvoiceSale).order_by(InvoiceSale.issue_date.desc()).all()
            else:
                invoices = db.query(InvoicePurchase).order_by(InvoicePurchase.issue_date.desc()).all()
            
            # Create CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            if invoice_type == "sales":
                writer.writerow([
                    'Number', 'Client', 'Email', 'Issue Date', 'Due Date',
                    'Amount HT', 'VAT Rate', 'Amount TTC', 'Status'
                ])
                
                for inv in invoices:
                    writer.writerow([
                        inv.number,
                        inv.client_name,
                        inv.client_email or '',
                        inv.issue_date.isoformat(),
                        inv.due_date.isoformat(),
                        float(inv.amount_ht or 0),
                        float(inv.vat_rate or 0),
                        float(inv.amount_ttc or 0),
                        inv.status
                    ])
            else:
                writer.writerow([
                    'Number', 'Supplier', 'Issue Date', 'Due Date',
                    'Amount', 'VAT', 'Status'
                ])
                
                for inv in invoices:
                    writer.writerow([
                        inv.number,
                        inv.supplier.name if inv.supplier else '',
                        inv.issue_date.isoformat(),
                        inv.due_date.isoformat(),
                        float(inv.amount or 0),
                        float(inv.vat or 0),
                        inv.status
                    ])
            
            output.seek(0)
            
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode('utf-8')),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename={invoice_type}_invoices_{datetime.now().strftime('%Y%m%d')}.csv",
                    **get_cors_headers()
                }
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )

# ============================================
# EXPORT BUDGET REPORT
# ============================================

@router.get("/budget/report")
def export_budget_report():
    """Export budget report"""
    try:
        from ..models_banking import Budget
        
        with SessionLocal() as db:
            budgets = db.query(Budget)\
                .filter(Budget.is_active == True)\
                .all()
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            writer.writerow([
                'Budget Name', 'Amount', 'Period', 'Start Date', 
                'End Date', 'Alert Threshold'
            ])
            
            for budget in budgets:
                writer.writerow([
                    budget.name,
                    float(budget.amount),
                    budget.period_type,
                    budget.start_date.isoformat(),
                    budget.end_date.isoformat() if budget.end_date else '',
                    float(budget.alert_threshold) * 100
                ])
            
            output.seek(0)
            
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode('utf-8')),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=budget_report_{datetime.now().strftime('%Y%m%d')}.csv",
                    **get_cors_headers()
                }
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )

# ============================================
# EXPORT CATEGORIES
# ============================================

@router.get("/categories/csv")
def export_categories():
    """Export categories with statistics"""
    try:
        with SessionLocal() as db:
            categories = db.query(Category).all()
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            writer.writerow([
                'ID', 'Name', 'Type', 'Parent ID', 'Icon', 
                'Color', 'Is Deductible', 'Deduction Rate'
            ])
            
            for cat in categories:
                writer.writerow([
                    cat.id,
                    cat.name,
                    cat.type,
                    cat.parent_id or '',
                    cat.icon or '',
                    cat.color or '',
                    'Yes' if cat.is_deductible else 'No',
                    float(cat.deduction_rate) if cat.deduction_rate else ''
                ])
            
            output.seek(0)
            
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode('utf-8')),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=categories_{datetime.now().strftime('%Y%m%d')}.csv",
                    **get_cors_headers()
                }
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )
