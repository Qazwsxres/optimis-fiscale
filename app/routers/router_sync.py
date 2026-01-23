"""
Synchronization Router - Bankin/Finary/Bridge Integration
Handles external banking API synchronization
"""

import os
import httpx
from datetime import datetime, date
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional

from ..database import SessionLocal
from ..models_banking import BankAccount, BankTransactionEnhanced, SyncLog

router = APIRouter(prefix="/api/sync", tags=["Synchronization"])

# Get CORS origin
FRONTEND_URL = os.getenv("ALLOWED_ORIGIN", "https://qazwsxres.github.io").split(",")[0]

def get_cors_headers():
    return {
        "Access-Control-Allow-Origin": FRONTEND_URL,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "*"
    }

# ============================================
# REQUEST MODELS
# ============================================

class SyncRequest(BaseModel):
    provider: str  # bankin, finary, bridge
    access_token: str
    account_ids: Optional[List[str]] = None

class ManualTransactionImport(BaseModel):
    account_id: int
    date: date
    label: str
    amount: float
    balance: Optional[float] = None
    category: Optional[str] = None

# ============================================
# BANKIN SYNC
# ============================================

@router.post("/bankin")
async def sync_from_bankin(request: SyncRequest):
    """
    Synchronize with Bankin API
    
    Requires: Bankin access token from OAuth2 flow
    
    Process:
    1. Fetch all accounts from Bankin
    2. For each account, fetch transactions
    3. Save to database with deduplication
    4. Log sync results
    """
    
    sync_log = None
    
    try:
        with SessionLocal() as db:
            # Create sync log
            sync_log = SyncLog(
                provider="bankin",
                status="running",
                started_at=datetime.now()
            )
            db.add(sync_log)
            db.commit()
            db.refresh(sync_log)
        
        total_accounts = 0
        total_transactions = 0
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Fetch accounts
            headers = {
                "Authorization": f"Bearer {request.access_token}",
                "Bankin-Version": "2023-12-01"
            }
            
            accounts_response = await client.get(
                "https://sync.bankin.com/v2/accounts",
                headers=headers
            )
            
            if accounts_response.status_code != 200:
                raise HTTPException(500, f"Bankin API error: {accounts_response.text}")
            
            accounts = accounts_response.json().get("resources", [])
            total_accounts = len(accounts)
            
            # 2. Process each account
            with SessionLocal() as db:
                for bankin_account in accounts:
                    account_id = bankin_account["id"]
                    
                    # Find or create account in DB
                    db_account = db.query(BankAccount)\
                        .filter(BankAccount.external_id == account_id)\
                        .first()
                    
                    if not db_account:
                        db_account = BankAccount(
                            external_id=account_id,
                            name=bankin_account.get("name", "Unknown"),
                            bank_name=bankin_account.get("bank_name"),
                            iban=bankin_account.get("iban"),
                            account_type=bankin_account.get("type", "checking"),
                            balance=bankin_account.get("balance", 0),
                            provider="bankin",
                            metadata=bankin_account
                        )
                        db.add(db_account)
                        db.commit()
                        db.refresh(db_account)
                    else:
                        # Update balance
                        db_account.balance = bankin_account.get("balance", db_account.balance)
                        db_account.last_sync = datetime.now()
                        db.commit()
                    
                    # 3. Fetch transactions for this account
                    trans_response = await client.get(
                        f"https://sync.bankin.com/v2/accounts/{account_id}/transactions",
                        headers=headers,
                        params={"limit": 500}  # Fetch last 500 transactions
                    )
                    
                    if trans_response.status_code == 200:
                        transactions = trans_response.json().get("resources", [])
                        
                        for bankin_trans in transactions:
                            # Check if already exists
                            existing = db.query(BankTransactionEnhanced)\
                                .filter(BankTransactionEnhanced.external_id == bankin_trans["id"])\
                                .first()
                            
                            if not existing:
                                # Parse date
                                trans_date = datetime.fromisoformat(bankin_trans["date"].replace("Z", "+00:00")).date()
                                
                                db_trans = BankTransactionEnhanced(
                                    account_id=db_account.id,
                                    external_id=bankin_trans["id"],
                                    date=trans_date,
                                    label=bankin_trans.get("description"),
                                    raw_label=bankin_trans.get("raw_description"),
                                    amount=bankin_trans.get("amount", 0),
                                    balance=bankin_trans.get("balance"),
                                    metadata=bankin_trans
                                )
                                db.add(db_trans)
                                total_transactions += 1
                        
                        db.commit()
                
                # Update sync log
                sync_log = db.query(SyncLog).filter(SyncLog.id == sync_log.id).first()
                sync_log.status = "success"
                sync_log.completed_at = datetime.now()
                sync_log.transactions_created = total_transactions
                db.commit()
        
        return JSONResponse(
            content={
                "success": True,
                "provider": "bankin",
                "accounts_synced": total_accounts,
                "transactions_created": total_transactions,
                "sync_log_id": sync_log.id
            },
            headers=get_cors_headers()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        # Update sync log with error
        if sync_log:
            with SessionLocal() as db:
                sync_log = db.query(SyncLog).filter(SyncLog.id == sync_log.id).first()
                sync_log.status = "failed"
                sync_log.completed_at = datetime.now()
                sync_log.error_message = str(e)
                db.commit()
        
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


# ============================================
# FINARY SYNC
# ============================================

@router.post("/finary")
async def sync_from_finary(request: SyncRequest):
    """
    Synchronize with Finary API
    
    Requires: Finary API key
    """
    
    sync_log = None
    
    try:
        with SessionLocal() as db:
            sync_log = SyncLog(
                provider="finary",
                status="running",
                started_at=datetime.now()
            )
            db.add(sync_log)
            db.commit()
            db.refresh(sync_log)
        
        total_accounts = 0
        total_transactions = 0
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {
                "Authorization": f"Bearer {request.access_token}"
            }
            
            # Fetch checking accounts from Finary
            response = await client.get(
                "https://api.finary.com/users/me/checking_accounts",
                headers=headers
            )
            
            if response.status_code != 200:
                raise HTTPException(500, f"Finary API error: {response.text}")
            
            accounts = response.json().get("result", [])
            total_accounts = len(accounts)
            
            with SessionLocal() as db:
                for finary_account in accounts:
                    account_id = str(finary_account["id"])
                    
                    # Find or create account
                    db_account = db.query(BankAccount)\
                        .filter(BankAccount.external_id == account_id)\
                        .first()
                    
                    if not db_account:
                        db_account = BankAccount(
                            external_id=account_id,
                            name=finary_account.get("name", "Unknown"),
                            bank_name=finary_account.get("bank_name"),
                            balance=finary_account.get("balance", 0),
                            provider="finary",
                            metadata=finary_account
                        )
                        db.add(db_account)
                        db.commit()
                        db.refresh(db_account)
                    else:
                        db_account.balance = finary_account.get("balance", db_account.balance)
                        db_account.last_sync = datetime.now()
                        db.commit()
                    
                    # Note: Finary transaction fetching would go here
                    # API endpoint may vary
                
                sync_log = db.query(SyncLog).filter(SyncLog.id == sync_log.id).first()
                sync_log.status = "success"
                sync_log.completed_at = datetime.now()
                sync_log.transactions_created = total_transactions
                db.commit()
        
        return JSONResponse(
            content={
                "success": True,
                "provider": "finary",
                "accounts_synced": total_accounts,
                "transactions_created": total_transactions,
                "sync_log_id": sync_log.id
            },
            headers=get_cors_headers()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        if sync_log:
            with SessionLocal() as db:
                sync_log = db.query(SyncLog).filter(SyncLog.id == sync_log.id).first()
                sync_log.status = "failed"
                sync_log.completed_at = datetime.now()
                sync_log.error_message = str(e)
                db.commit()
        
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


# ============================================
# MANUAL IMPORT
# ============================================

@router.post("/manual")
def manual_import(transactions: List[ManualTransactionImport]):
    """
    Manually import transactions
    
    Useful for:
    - Importing historical data
    - Adding cash transactions
    - Correcting data
    """
    try:
        created_count = 0
        
        with SessionLocal() as db:
            for trans in transactions:
                # Verify account exists
                account = db.query(BankAccount).filter(BankAccount.id == trans.account_id).first()
                if not account:
                    continue
                
                db_trans = BankTransactionEnhanced(
                    account_id=trans.account_id,
                    date=trans.date,
                    label=trans.label,
                    amount=trans.amount,
                    balance=trans.balance,
                    sub_category=trans.category
                )
                db.add(db_trans)
                created_count += 1
            
            db.commit()
        
        return JSONResponse(
            content={
                "success": True,
                "transactions_created": created_count
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
# SYNC STATUS
# ============================================

@router.get("/status")
def get_sync_status():
    """Get status of recent synchronizations"""
    try:
        with SessionLocal() as db:
            logs = db.query(SyncLog)\
                .order_by(SyncLog.started_at.desc())\
                .limit(20)\
                .all()
            
            return JSONResponse(
                content=[{
                    "id": log.id,
                    "provider": log.provider,
                    "status": log.status,
                    "started_at": log.started_at.isoformat() if log.started_at else None,
                    "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                    "transactions_created": log.transactions_created,
                    "error_message": log.error_message
                } for log in logs],
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


# ============================================
# SYNC LOGS
# ============================================

@router.get("/logs")
def get_sync_logs(provider: Optional[str] = None, limit: int = 50):
    """Get synchronization logs with optional filtering"""
    try:
        with SessionLocal() as db:
            query = db.query(SyncLog)
            
            if provider:
                query = query.filter(SyncLog.provider == provider)
            
            logs = query.order_by(SyncLog.started_at.desc()).limit(limit).all()
            
            return JSONResponse(
                content=[{
                    "id": log.id,
                    "provider": log.provider,
                    "status": log.status,
                    "started_at": log.started_at.isoformat() if log.started_at else None,
                    "completed_at": log.completed_at.isoformat() if log.completed_at else None,
                    "duration_seconds": log.duration_seconds,
                    "transactions_fetched": log.transactions_fetched,
                    "transactions_created": log.transactions_created,
                    "transactions_updated": log.transactions_updated,
                    "transactions_skipped": log.transactions_skipped,
                    "error_message": log.error_message
                } for log in logs],
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )
