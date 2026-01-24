"""
Budgets Router - Budget Management and Tracking
"""

import os
from datetime import date, timedelta
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from ..database import SessionLocal
from ..models_banking import Budget, Category, BankTransactionEnhanced

router = APIRouter(prefix="/api/budgets", tags=["Budgets"])

FRONTEND_URL = os.getenv("ALLOWED_ORIGIN", "https://qazwsxres.github.io").split(",")[0]

def get_cors_headers():
    return {
        "Access-Control-Allow-Origin": FRONTEND_URL,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "*"
    }

# ============================================
# MODELS
# ============================================

class BudgetCreate(BaseModel):
    name: str
    category_id: Optional[int] = None
    amount: float
    period_type: str = "monthly"  # monthly, quarterly, yearly
    start_date: date
    end_date: Optional[date] = None
    alert_threshold: float = 0.80  # Alert at 80%

class BudgetUpdate(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    alert_threshold: Optional[float] = None
    is_active: Optional[bool] = None

# ============================================
# CREATE BUDGET
# ============================================

@router.post("/", status_code=201)
def create_budget(budget: BudgetCreate):
    """Create a new budget"""
    try:
        with SessionLocal() as db:
            # Verify category exists if specified
            if budget.category_id:
                category = db.query(Category).filter(Category.id == budget.category_id).first()
                if not category:
                    raise HTTPException(404, "Category not found")
            
            # Calculate end_date if not provided
            end_date = budget.end_date
            if not end_date:
                if budget.period_type == "monthly":
                    end_date = budget.start_date + timedelta(days=30)
                elif budget.period_type == "quarterly":
                    end_date = budget.start_date + timedelta(days=90)
                elif budget.period_type == "yearly":
                    end_date = budget.start_date + timedelta(days=365)
            
            bud = Budget(
                name=budget.name,
                category_id=budget.category_id,
                amount=budget.amount,
                period_type=budget.period_type,
                start_date=budget.start_date,
                end_date=end_date,
                alert_threshold=budget.alert_threshold,
                is_active=True
            )
            
            db.add(bud)
            db.commit()
            db.refresh(bud)
            
            return JSONResponse(
                content={
                    "id": bud.id,
                    "name": bud.name,
                    "amount": float(bud.amount),
                    "period_type": bud.period_type,
                    "start_date": bud.start_date.isoformat(),
                    "end_date": bud.end_date.isoformat() if bud.end_date else None
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
# LIST BUDGETS
# ============================================

@router.get("/")
def list_budgets(active_only: bool = True):
    """List all budgets"""
    try:
        with SessionLocal() as db:
            query = db.query(Budget)
            
            if active_only:
                query = query.filter(Budget.is_active == True)
            
            budgets = query.order_by(Budget.start_date.desc()).all()
            
            return JSONResponse(
                content=[{
                    "id": b.id,
                    "name": b.name,
                    "category_id": b.category_id,
                    "amount": float(b.amount),
                    "period_type": b.period_type,
                    "start_date": b.start_date.isoformat(),
                    "end_date": b.end_date.isoformat() if b.end_date else None,
                    "alert_threshold": float(b.alert_threshold),
                    "is_active": b.is_active
                } for b in budgets],
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )

# ============================================
# GET BUDGET PROGRESS
# ============================================

@router.get("/{budget_id}/progress")
def get_budget_progress(budget_id: int):
    """Get current progress for a budget"""
    try:
        with SessionLocal() as db:
            budget = db.query(Budget).filter(Budget.id == budget_id).first()
            
            if not budget:
                raise HTTPException(404, "Budget not found")
            
            # Get transactions in budget period
            query = db.query(BankTransactionEnhanced)\
                .filter(
                    BankTransactionEnhanced.date >= budget.start_date,
                    BankTransactionEnhanced.date <= budget.end_date
                )
            
            # Filter by category if specified
            if budget.category_id:
                query = query.filter(BankTransactionEnhanced.category_id == budget.category_id)
            
            transactions = query.all()
            
            # Calculate spent (absolute value of negative transactions)
            spent = sum(abs(float(t.amount)) for t in transactions if t.amount < 0)
            remaining = float(budget.amount) - spent
            percentage = (spent / float(budget.amount) * 100) if budget.amount > 0 else 0
            
            # Check if alert threshold exceeded
            alert = percentage >= (float(budget.alert_threshold) * 100)
            
            return JSONResponse(
                content={
                    "budget_id": budget_id,
                    "budget_name": budget.name,
                    "budget_amount": float(budget.amount),
                    "spent": round(spent, 2),
                    "remaining": round(remaining, 2),
                    "percentage": round(percentage, 2),
                    "alert_threshold": float(budget.alert_threshold) * 100,
                    "alert": alert,
                    "transaction_count": len(transactions),
                    "start_date": budget.start_date.isoformat(),
                    "end_date": budget.end_date.isoformat() if budget.end_date else None
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
# GET BUDGET ALERTS
# ============================================

@router.get("/alerts")
def get_budget_alerts():
    """Get all budgets that have exceeded their alert threshold"""
    try:
        with SessionLocal() as db:
            today = date.today()
            
            # Get active budgets that include today
            budgets = db.query(Budget)\
                .filter(
                    Budget.is_active == True,
                    Budget.start_date <= today,
                    Budget.end_date >= today
                )\
                .all()
            
            alerts = []
            
            for budget in budgets:
                # Get transactions
                query = db.query(BankTransactionEnhanced)\
                    .filter(
                        BankTransactionEnhanced.date >= budget.start_date,
                        BankTransactionEnhanced.date <= budget.end_date
                    )
                
                if budget.category_id:
                    query = query.filter(BankTransactionEnhanced.category_id == budget.category_id)
                
                transactions = query.all()
                spent = sum(abs(float(t.amount)) for t in transactions if t.amount < 0)
                percentage = (spent / float(budget.amount) * 100) if budget.amount > 0 else 0
                
                if percentage >= (float(budget.alert_threshold) * 100):
                    alerts.append({
                        "budget_id": budget.id,
                        "budget_name": budget.name,
                        "budget_amount": float(budget.amount),
                        "spent": round(spent, 2),
                        "percentage": round(percentage, 2),
                        "alert_threshold": float(budget.alert_threshold) * 100,
                        "severity": "high" if percentage >= 100 else "medium"
                    })
            
            return JSONResponse(
                content={
                    "alert_count": len(alerts),
                    "alerts": alerts
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
# UPDATE BUDGET
# ============================================

@router.put("/{budget_id}")
def update_budget(budget_id: int, budget: BudgetUpdate):
    """Update a budget"""
    try:
        with SessionLocal() as db:
            bud = db.query(Budget).filter(Budget.id == budget_id).first()
            
            if not bud:
                raise HTTPException(404, "Budget not found")
            
            if budget.name is not None:
                bud.name = budget.name
            if budget.amount is not None:
                bud.amount = budget.amount
            if budget.alert_threshold is not None:
                bud.alert_threshold = budget.alert_threshold
            if budget.is_active is not None:
                bud.is_active = budget.is_active
            
            db.commit()
            db.refresh(bud)
            
            return JSONResponse(
                content={
                    "id": bud.id,
                    "message": "Budget updated"
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
# DELETE BUDGET
# ============================================

@router.delete("/{budget_id}")
def delete_budget(budget_id: int):
    """Delete a budget"""
    try:
        with SessionLocal() as db:
            budget = db.query(Budget).filter(Budget.id == budget_id).first()
            
            if not budget:
                raise HTTPException(404, "Budget not found")
            
            db.delete(budget)
            db.commit()
            
            return JSONResponse(
                content={"message": "Budget deleted"},
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
# GET BUDGET OVERVIEW
# ============================================

@router.get("/overview")
def get_budgets_overview():
    """Get overview of all active budgets"""
    try:
        with SessionLocal() as db:
            today = date.today()
            
            budgets = db.query(Budget)\
                .filter(
                    Budget.is_active == True,
                    Budget.start_date <= today,
                    Budget.end_date >= today
                )\
                .all()
            
            total_budget = sum(float(b.amount) for b in budgets)
            total_spent = 0
            alerts_count = 0
            
            budget_details = []
            
            for budget in budgets:
                query = db.query(BankTransactionEnhanced)\
                    .filter(
                        BankTransactionEnhanced.date >= budget.start_date,
                        BankTransactionEnhanced.date <= budget.end_date
                    )
                
                if budget.category_id:
                    query = query.filter(BankTransactionEnhanced.category_id == budget.category_id)
                
                transactions = query.all()
                spent = sum(abs(float(t.amount)) for t in transactions if t.amount < 0)
                total_spent += spent
                
                percentage = (spent / float(budget.amount) * 100) if budget.amount > 0 else 0
                if percentage >= (float(budget.alert_threshold) * 100):
                    alerts_count += 1
                
                budget_details.append({
                    "id": budget.id,
                    "name": budget.name,
                    "amount": float(budget.amount),
                    "spent": round(spent, 2),
                    "percentage": round(percentage, 2)
                })
            
            return JSONResponse(
                content={
                    "active_budgets": len(budgets),
                    "total_budget": round(total_budget, 2),
                    "total_spent": round(total_spent, 2),
                    "total_remaining": round(total_budget - total_spent, 2),
                    "overall_percentage": round((total_spent / total_budget * 100) if total_budget > 0 else 0, 2),
                    "alerts_count": alerts_count,
                    "budgets": budget_details
                },
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )
