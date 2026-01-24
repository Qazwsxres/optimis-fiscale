"""
Bank Accounts Router
Manage bank accounts and their balances
Compatible with Bankin/Finary integration
"""

import os
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime

from ..database import SessionLocal
from ..models_banking import BankAccount, BankTransactionEnhanced

router = APIRouter(prefix="/api/accounts", tags=["Bank Accounts"])

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


# ============================================
# REQUEST/RESPONSE MODELS
# ============================================
class AccountCreate(BaseModel):
    name: str
    bank_name: str
    iban: Optional[str] = None
    bic: Optional[str] = None
    account_type: str = "checking"
    provider: str = "manual"
    external_id: Optional[str] = None

class AccountUpdate(BaseModel):
    name: Optional[str] = None
    bank_name: Optional[str] = None
    is_active: Optional[bool] = None

class AccountResponse(BaseModel):
    id: int
    name: str
    bank_name: str
    iban: Optional[str]
    account_type: str
    balance: float
    currency: str
    is_active: bool
    provider: str
    last_sync: Optional[str]


# ============================================
# GET ALL ACCOUNTS
# ============================================
@router.get("/")
def list_accounts(include_inactive: bool = False):
    """
    Get all bank accounts
    
    Query params:
    - include_inactive: Include inactive accounts (default: false)
    """
    try:
        with SessionLocal() as db:
            query = db.query(BankAccount)
            
            if not include_inactive:
                query = query.filter(BankAccount.is_active == True)
            
            accounts = query.order_by(BankAccount.name).all()
            
            return JSONResponse(
                content=[{
                    "id": acc.id,
                    "name": acc.name,
                    "bank_name": acc.bank_name,
                    "iban": acc.iban,
                    "bic": acc.bic,
                    "account_type": acc.account_type,
                    "balance": float(acc.balance) if acc.balance else 0.0,
                    "currency": acc.currency,
                    "is_active": acc.is_active,
                    "provider": acc.provider,
                    "last_sync": acc.last_sync.isoformat() if acc.last_sync else None
                } for acc in accounts],
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


# ============================================
# GET SINGLE ACCOUNT
# ============================================
@router.get("/{account_id}")
def get_account(account_id: int):
    """Get details for a specific account"""
    try:
        with SessionLocal() as db:
            account = db.query(BankAccount).filter(BankAccount.id == account_id).first()
            
            if not account:
                raise HTTPException(404, "Account not found")
            
            # Get transaction count
            trans_count = db.query(BankTransactionEnhanced)\
                .filter(BankTransactionEnhanced.account_id == account_id)\
                .count()
            
            return JSONResponse(
                content={
                    "id": account.id,
                    "name": account.name,
                    "bank_name": account.bank_name,
                    "iban": account.iban,
                    "bic": account.bic,
                    "account_type": account.account_type,
                    "balance": float(account.balance) if account.balance else 0.0,
                    "currency": account.currency,
                    "is_active": account.is_active,
                    "provider": account.provider,
                    "external_id": account.external_id,
                    "last_sync": account.last_sync.isoformat() if account.last_sync else None,
                    "transaction_count": trans_count,
                    "created_at": account.created_at.isoformat() if account.created_at else None
                },
                headers=get_cors_headers()
            )
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


# ============================================
# CREATE ACCOUNT
# ============================================
@router.post("/")
def create_account(account: AccountCreate):
    """Create a new bank account"""
    try:
        with SessionLocal() as db:
            # Check if external_id already exists
            if account.external_id:
                existing = db.query(BankAccount)\
                    .filter(BankAccount.external_id == account.external_id)\
                    .first()
                if existing:
                    raise HTTPException(409, "Account with this external_id already exists")
            
            acc = BankAccount(
                name=account.name,
                bank_name=account.bank_name,
                iban=account.iban,
                bic=account.bic,
                account_type=account.account_type,
                provider=account.provider,
                external_id=account.external_id
            )
            db.add(acc)
            db.commit()
            db.refresh(acc)
            
            return JSONResponse(
                content={
                    "id": acc.id,
                    "name": acc.name,
                    "bank_name": acc.bank_name,
                    "message": "Account created successfully"
                },
                status_code=201,
                headers=get_cors_headers()
            )
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


# ============================================
# UPDATE ACCOUNT
# ============================================
@router.put("/{account_id}")
def update_account(account_id: int, account: AccountUpdate):
    """Update an existing account"""
    try:
        with SessionLocal() as db:
            acc = db.query(BankAccount).filter(BankAccount.id == account_id).first()
            
            if not acc:
                raise HTTPException(404, "Account not found")
            
            if account.name is not None:
                acc.name = account.name
            if account.bank_name is not None:
                acc.bank_name = account.bank_name
            if account.is_active is not None:
                acc.is_active = account.is_active
            
            db.commit()
            db.refresh(acc)
            
            return JSONResponse(
                content={
                    "id": acc.id,
                    "message": "Account updated successfully"
                },
                headers=get_cors_headers()
            )
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


# ============================================
# DELETE ACCOUNT (SOFT)
# ============================================
@router.delete("/{account_id}")
def delete_account(account_id: int):
    """
    Soft delete an account (sets is_active to False)
    """
    try:
        with SessionLocal() as db:
            acc = db.query(BankAccount).filter(BankAccount.id == account_id).first()
            
            if not acc:
                raise HTTPException(404, "Account not found")
            
            acc.is_active = False
            db.commit()
            
            return JSONResponse(
                content={"message": "Account deactivated successfully"},
                headers=get_cors_headers()
            )
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


# ============================================
# GET ACCOUNT BALANCE
# ============================================
@router.get("/{account_id}/balance")
def get_account_balance(account_id: int):
    """Get current balance for an account"""
    try:
        with SessionLocal() as db:
            account = db.query(BankAccount).filter(BankAccount.id == account_id).first()
            
            if not account:
                raise HTTPException(404, "Account not found")
            
            # Get latest transaction balance
            latest = db.query(BankTransactionEnhanced)\
                .filter(BankTransactionEnhanced.account_id == account_id)\
                .order_by(BankTransactionEnhanced.date.desc())\
                .first()
            
            # Use transaction balance if available, otherwise account balance
            balance = float(latest.balance) if latest and latest.balance else float(account.balance or 0)
            
            return JSONResponse(
                content={
                    "account_id": account_id,
                    "account_name": account.name,
                    "balance": balance,
                    "currency": account.currency,
                    "last_updated": latest.date.isoformat() if latest else None
                },
                headers=get_cors_headers()
            )
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


# ============================================
# GET ACCOUNT TRANSACTIONS
# ============================================
@router.get("/{account_id}/transactions")
def get_account_transactions(
    account_id: int,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Get transactions for a specific account
    
    Query params:
    - start_date: Filter from date (ISO format YYYY-MM-DD)
    - end_date: Filter to date (ISO format YYYY-MM-DD)
    - category: Filter by category name
    - limit: Max number of results (default: 100)
    - offset: Skip N results (for pagination)
    """
    try:
        with SessionLocal() as db:
            query = db.query(BankTransactionEnhanced)\
                .filter(BankTransactionEnhanced.account_id == account_id)\
                .order_by(BankTransactionEnhanced.date.desc())
            
            if start_date:
                query = query.filter(BankTransactionEnhanced.date >= start_date)
            if end_date:
                query = query.filter(BankTransactionEnhanced.date <= end_date)
            if category:
                query = query.filter(BankTransactionEnhanced.sub_category == category)
            
            total = query.count()
            transactions = query.limit(limit).offset(offset).all()
            
            return JSONResponse(
                content={
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                    "transactions": [{
                        "id": t.id,
                        "date": t.date.isoformat(),
                        "label": t.label,
                        "raw_label": t.raw_label,
                        "amount": float(t.amount),
                        "balance": float(t.balance) if t.balance else None,
                        "category": t.sub_category,
                        "is_recurring": t.is_recurring,
                        "is_reconciled": t.is_reconciled
                    } for t in transactions]
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
# GET ACCOUNT SUMMARY
# ============================================
@router.get("/{account_id}/summary")
def get_account_summary(account_id: int, days: int = 30):
    """
    Get account summary (income, expenses, balance evolution)
    
    Query params:
    - days: Number of days to analyze (default: 30)
    """
    try:
        with SessionLocal() as db:
            from datetime import timedelta
            from sqlalchemy import func
            
            account = db.query(BankAccount).filter(BankAccount.id == account_id).first()
            if not account:
                raise HTTPException(404, "Account not found")
            
            # Date range
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            # Get transactions in period
            transactions = db.query(BankTransactionEnhanced)\
                .filter(
                    BankTransactionEnhanced.account_id == account_id,
                    BankTransactionEnhanced.date >= start_date,
                    BankTransactionEnhanced.date <= end_date
                )\
                .all()
            
            # Calculate stats
            income = sum(float(t.amount) for t in transactions if t.amount > 0)
            expenses = sum(abs(float(t.amount)) for t in transactions if t.amount < 0)
            net = income - expenses
            
            return JSONResponse(
                content={
                    "account_id": account_id,
                    "account_name": account.name,
                    "period_days": days,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "current_balance": float(account.balance or 0),
                    "income": round(income, 2),
                    "expenses": round(expenses, 2),
                    "net": round(net, 2),
                    "transaction_count": len(transactions)
                },
                headers=get_cors_headers()
            )
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )
