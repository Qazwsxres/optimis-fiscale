"""
Webhooks Router - Handle callbacks from Bankin/Finary/Bridge
"""

import os
import hmac
import hashlib
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException, Header
from fastapi.responses import JSONResponse
from typing import Optional

from ..database import SessionLocal
from ..models_banking import WebhookEvent, BankAccount, BankTransactionEnhanced

router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])

FRONTEND_URL = os.getenv("ALLOWED_ORIGIN", "https://qazwsxres.github.io").split(",")[0]

# Webhook secrets from environment
BANKIN_WEBHOOK_SECRET = os.getenv("BANKIN_WEBHOOK_SECRET")
FINARY_WEBHOOK_SECRET = os.getenv("FINARY_WEBHOOK_SECRET")
BRIDGE_WEBHOOK_SECRET = os.getenv("BRIDGE_WEBHOOK_SECRET")

def get_cors_headers():
    return {
        "Access-Control-Allow-Origin": FRONTEND_URL,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "*"
    }

# ============================================
# SIGNATURE VERIFICATION
# ============================================

def verify_bankin_signature(payload: bytes, signature: str) -> bool:
    """Verify Bankin webhook signature"""
    if not BANKIN_WEBHOOK_SECRET:
        return False
    
    expected = hmac.new(
        BANKIN_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)

def verify_finary_signature(payload: bytes, signature: str) -> bool:
    """Verify Finary webhook signature"""
    if not FINARY_WEBHOOK_SECRET:
        return False
    
    expected = hmac.new(
        FINARY_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)

# ============================================
# BANKIN WEBHOOK
# ============================================

@router.post("/bankin")
async def bankin_webhook(
    request: Request,
    x_bankin_signature: Optional[str] = Header(None)
):
    """
    Handle webhooks from Bankin API
    
    Events:
    - transaction.created: New transaction
    - transaction.updated: Transaction updated
    - account.updated: Account balance updated
    - synchronization.completed: Sync finished
    """
    try:
        # Get raw body
        body = await request.body()
        
        # Verify signature
        if x_bankin_signature:
            if not verify_bankin_signature(body, x_bankin_signature):
                raise HTTPException(401, "Invalid signature")
        
        # Parse payload
        payload = await request.json()
        event_type = payload.get("type")
        event_data = payload.get("data", {})
        
        # Store webhook event
        with SessionLocal() as db:
            webhook = WebhookEvent(
                provider="bankin",
                event_type=event_type,
                payload=payload,
                headers=dict(request.headers),
                status="pending",
                external_event_id=payload.get("id")
            )
            db.add(webhook)
            db.commit()
            db.refresh(webhook)
            
            # Process event
            try:
                if event_type == "transaction.created":
                    # Create new transaction
                    account_id = event_data.get("account_id")
                    
                    # Find account in DB
                    account = db.query(BankAccount)\
                        .filter(BankAccount.external_id == account_id)\
                        .first()
                    
                    if account:
                        trans = BankTransactionEnhanced(
                            account_id=account.id,
                            external_id=event_data.get("id"),
                            date=datetime.fromisoformat(event_data.get("date")).date(),
                            label=event_data.get("description"),
                            raw_label=event_data.get("raw_description"),
                            amount=event_data.get("amount", 0),
                            balance=event_data.get("balance"),
                            metadata=event_data
                        )
                        db.add(trans)
                
                elif event_type == "account.updated":
                    # Update account balance
                    account_id = event_data.get("id")
                    
                    account = db.query(BankAccount)\
                        .filter(BankAccount.external_id == account_id)\
                        .first()
                    
                    if account:
                        account.balance = event_data.get("balance", account.balance)
                        account.last_sync = datetime.now()
                
                db.commit()
                
                # Mark webhook as processed
                webhook.status = "processed"
                webhook.processed_at = datetime.now()
                db.commit()
                
            except Exception as e:
                # Mark as failed
                webhook.status = "failed"
                webhook.error_message = str(e)
                webhook.processed_at = datetime.now()
                db.commit()
        
        return JSONResponse(
            content={"status": "ok"},
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
# FINARY WEBHOOK
# ============================================

@router.post("/finary")
async def finary_webhook(
    request: Request,
    x_finary_signature: Optional[str] = Header(None)
):
    """Handle webhooks from Finary API"""
    try:
        body = await request.body()
        
        # Verify signature
        if x_finary_signature:
            if not verify_finary_signature(body, x_finary_signature):
                raise HTTPException(401, "Invalid signature")
        
        payload = await request.json()
        event_type = payload.get("event")
        event_data = payload.get("data", {})
        
        # Store webhook event
        with SessionLocal() as db:
            webhook = WebhookEvent(
                provider="finary",
                event_type=event_type,
                payload=payload,
                headers=dict(request.headers),
                status="pending"
            )
            db.add(webhook)
            db.commit()
            
            # Process event (similar to Bankin)
            webhook.status = "processed"
            webhook.processed_at = datetime.now()
            db.commit()
        
        return JSONResponse(
            content={"status": "ok"},
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
# BRIDGE WEBHOOK
# ============================================

@router.post("/bridge")
async def bridge_webhook(request: Request):
    """Handle webhooks from Bridge API"""
    try:
        payload = await request.json()
        event_type = payload.get("event_type")
        
        with SessionLocal() as db:
            webhook = WebhookEvent(
                provider="bridge",
                event_type=event_type,
                payload=payload,
                headers=dict(request.headers),
                status="pending"
            )
            db.add(webhook)
            db.commit()
            
            webhook.status = "processed"
            webhook.processed_at = datetime.now()
            db.commit()
        
        return JSONResponse(
            content={"status": "ok"},
            headers=get_cors_headers()
        )
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )

# ============================================
# GET WEBHOOK EVENTS
# ============================================

@router.get("/events")
def get_webhook_events(
    provider: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50
):
    """Get webhook events history"""
    try:
        with SessionLocal() as db:
            query = db.query(WebhookEvent)
            
            if provider:
                query = query.filter(WebhookEvent.provider == provider)
            if status:
                query = query.filter(WebhookEvent.status == status)
            
            events = query.order_by(WebhookEvent.received_at.desc()).limit(limit).all()
            
            return JSONResponse(
                content=[{
                    "id": e.id,
                    "provider": e.provider,
                    "event_type": e.event_type,
                    "status": e.status,
                    "received_at": e.received_at.isoformat() if e.received_at else None,
                    "processed_at": e.processed_at.isoformat() if e.processed_at else None,
                    "error_message": e.error_message
                } for e in events],
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )

# ============================================
# VERIFY WEBHOOK SETUP
# ============================================

@router.get("/verify")
def verify_webhook_setup():
    """Verify webhook configuration"""
    return JSONResponse(
        content={
            "bankin": {
                "configured": bool(BANKIN_WEBHOOK_SECRET),
                "url": f"{os.getenv('API_URL', 'https://your-api.com')}/api/webhooks/bankin"
            },
            "finary": {
                "configured": bool(FINARY_WEBHOOK_SECRET),
                "url": f"{os.getenv('API_URL', 'https://your-api.com')}/api/webhooks/finary"
            },
            "bridge": {
                "configured": bool(BRIDGE_WEBHOOK_SECRET),
                "url": f"{os.getenv('API_URL', 'https://your-api.com')}/api/webhooks/bridge"
            }
        },
        headers=get_cors_headers()
    )
