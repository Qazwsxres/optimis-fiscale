"""
Analytics Router - KPIs, Statistics, and Financial Analysis
"""

import os
from datetime import date, timedelta
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from typing import Optional

from ..database import SessionLocal
from ..models_banking import BankAccount, BankTransactionEnhanced, Category
from sqlalchemy import func, extract

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

FRONTEND_URL = os.getenv("ALLOWED_ORIGIN", "https://qazwsxres.github.io").split(",")[0]

def get_cors_headers():
    return {
        "Access-Control-Allow-Origin": FRONTEND_URL,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "*"
    }

# ============================================
# OVERVIEW DASHBOARD
# ============================================

@router.get("/overview")
def get_overview(days: int = 30):
    """Get financial overview for dashboard"""
    try:
        from datetime import date, timedelta
        
        with SessionLocal() as db:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            # Get all transactions in period
            transactions = db.query(BankTransactionEnhanced)\
                .filter(
                    BankTransactionEnhanced.date >= start_date,
                    BankTransactionEnhanced.date <= end_date
                )\
                .all()
            
            # Calculate metrics
            income = sum(float(t.amount) for t in transactions if t.amount > 0)
            expenses = sum(abs(float(t.amount)) for t in transactions if t.amount < 0)
            net = income - expenses
            
            # Average per day
            avg_daily_income = income / days if days > 0 else 0
            avg_daily_expenses = expenses / days if days > 0 else 0
            
            # Current balance from all accounts
            accounts = db.query(BankAccount).filter(BankAccount.is_active == True).all()
            total_balance = sum(float(acc.balance or 0) for acc in accounts)
            
            # Transaction count
            trans_count = len(transactions)
            
            return JSONResponse(
                content={
                    "period_days": days,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "total_balance": round(total_balance, 2),
                    "income": round(income, 2),
                    "expenses": round(expenses, 2),
                    "net": round(net, 2),
                    "avg_daily_income": round(avg_daily_income, 2),
                    "avg_daily_expenses": round(avg_daily_expenses, 2),
                    "transaction_count": trans_count,
                    "accounts_count": len(accounts)
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
# SPENDING ANALYSIS
# ============================================

@router.get("/spending")
def get_spending_analysis(days: int = 30):
    """Analyze spending by category"""
    try:
        with SessionLocal() as db:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            # Get expense transactions grouped by category
            results = db.query(
                Category.name,
                Category.icon,
                Category.color,
                func.count(BankTransactionEnhanced.id).label('count'),
                func.sum(BankTransactionEnhanced.amount).label('total')
            )\
            .join(BankTransactionEnhanced, BankTransactionEnhanced.category_id == Category.id)\
            .filter(
                BankTransactionEnhanced.date >= start_date,
                BankTransactionEnhanced.date <= end_date,
                BankTransactionEnhanced.amount < 0  # Only expenses
            )\
            .group_by(Category.id, Category.name, Category.icon, Category.color)\
            .order_by(func.sum(BankTransactionEnhanced.amount).asc())\
            .all()
            
            total_expenses = sum(abs(float(r.total or 0)) for r in results)
            
            categories = []
            for r in results:
                amount = abs(float(r.total or 0))
                percentage = (amount / total_expenses * 100) if total_expenses > 0 else 0
                
                categories.append({
                    "category": r.name,
                    "icon": r.icon,
                    "color": r.color,
                    "transaction_count": r.count,
                    "amount": round(amount, 2),
                    "percentage": round(percentage, 2)
                })
            
            return JSONResponse(
                content={
                    "period_days": days,
                    "total_expenses": round(total_expenses, 2),
                    "categories": categories
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
# INCOME ANALYSIS
# ============================================

@router.get("/income")
def get_income_analysis(days: int = 30):
    """Analyze income sources"""
    try:
        with SessionLocal() as db:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            # Get income transactions
            results = db.query(
                Category.name,
                func.count(BankTransactionEnhanced.id).label('count'),
                func.sum(BankTransactionEnhanced.amount).label('total')
            )\
            .join(BankTransactionEnhanced, BankTransactionEnhanced.category_id == Category.id)\
            .filter(
                BankTransactionEnhanced.date >= start_date,
                BankTransactionEnhanced.date <= end_date,
                BankTransactionEnhanced.amount > 0  # Only income
            )\
            .group_by(Category.id, Category.name)\
            .order_by(func.sum(BankTransactionEnhanced.amount).desc())\
            .all()
            
            total_income = sum(float(r.total or 0) for r in results)
            
            sources = []
            for r in results:
                amount = float(r.total or 0)
                percentage = (amount / total_income * 100) if total_income > 0 else 0
                
                sources.append({
                    "source": r.name,
                    "transaction_count": r.count,
                    "amount": round(amount, 2),
                    "percentage": round(percentage, 2)
                })
            
            return JSONResponse(
                content={
                    "period_days": days,
                    "total_income": round(total_income, 2),
                    "sources": sources
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
# TRENDS ANALYSIS
# ============================================

@router.get("/trends")
def get_trends(months: int = 6):
    """Get monthly income/expense trends"""
    try:
        with SessionLocal() as db:
            end_date = date.today()
            start_date = end_date - timedelta(days=months * 30)
            
            # Get transactions grouped by month
            results = db.query(
                extract('year', BankTransactionEnhanced.date).label('year'),
                extract('month', BankTransactionEnhanced.date).label('month'),
                func.sum(
                    func.case(
                        (BankTransactionEnhanced.amount > 0, BankTransactionEnhanced.amount),
                        else_=0
                    )
                ).label('income'),
                func.sum(
                    func.case(
                        (BankTransactionEnhanced.amount < 0, BankTransactionEnhanced.amount),
                        else_=0
                    )
                ).label('expenses')
            )\
            .filter(BankTransactionEnhanced.date >= start_date)\
            .group_by('year', 'month')\
            .order_by('year', 'month')\
            .all()
            
            trends = []
            for r in results:
                income = float(r.income or 0)
                expenses = abs(float(r.expenses or 0))
                net = income - expenses
                
                trends.append({
                    "year": int(r.year),
                    "month": int(r.month),
                    "income": round(income, 2),
                    "expenses": round(expenses, 2),
                    "net": round(net, 2)
                })
            
            return JSONResponse(
                content={
                    "months": months,
                    "trends": trends
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
# RECURRING TRANSACTIONS
# ============================================

@router.get("/recurring")
def get_recurring_transactions():
    """Detect recurring transactions (subscriptions, bills)"""
    try:
        with SessionLocal() as db:
            # Get all transactions
            transactions = db.query(BankTransactionEnhanced)\
                .filter(BankTransactionEnhanced.is_recurring == True)\
                .order_by(BankTransactionEnhanced.date.desc())\
                .limit(100)\
                .all()
            
            # Group by label (simplified)
            recurring = {}
            for trans in transactions:
                label = trans.label or "Unknown"
                if label not in recurring:
                    recurring[label] = {
                        "label": label,
                        "count": 0,
                        "total": 0,
                        "avg_amount": 0,
                        "category": trans.sub_category
                    }
                recurring[label]["count"] += 1
                recurring[label]["total"] += abs(float(trans.amount))
            
            # Calculate averages
            for item in recurring.values():
                item["avg_amount"] = round(item["total"] / item["count"], 2) if item["count"] > 0 else 0
                item["total"] = round(item["total"], 2)
            
            return JSONResponse(
                content={
                    "recurring_count": len(recurring),
                    "recurring": list(recurring.values())
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
# FORECAST
# ============================================

@router.get("/forecast")
def get_forecast(days: int = 30):
    """
    Simple linear forecast based on historical trends
    
    Note: This is a basic implementation. 
    In production, use ML models like Prophet or LSTM.
    """
    try:
        with SessionLocal() as db:
            # Get last 90 days of data
            end_date = date.today()
            start_date = end_date - timedelta(days=90)
            
            transactions = db.query(BankTransactionEnhanced)\
                .filter(
                    BankTransactionEnhanced.date >= start_date,
                    BankTransactionEnhanced.date <= end_date
                )\
                .all()
            
            # Calculate daily averages
            income_sum = sum(float(t.amount) for t in transactions if t.amount > 0)
            expense_sum = sum(abs(float(t.amount)) for t in transactions if t.amount < 0)
            
            avg_daily_income = income_sum / 90
            avg_daily_expense = expense_sum / 90
            
            # Get current balance
            accounts = db.query(BankAccount).filter(BankAccount.is_active == True).all()
            current_balance = sum(float(acc.balance or 0) for acc in accounts)
            
            # Generate forecast
            forecast = []
            balance = current_balance
            
            for i in range(1, days + 1):
                forecast_date = end_date + timedelta(days=i)
                
                # Add expected income and subtract expected expenses
                balance += avg_daily_income - avg_daily_expense
                
                forecast.append({
                    "date": forecast_date.isoformat(),
                    "predicted_balance": round(balance, 2),
                    "expected_income": round(avg_daily_income, 2),
                    "expected_expenses": round(avg_daily_expense, 2)
                })
            
            return JSONResponse(
                content={
                    "current_balance": round(current_balance, 2),
                    "forecast_days": days,
                    "avg_daily_income": round(avg_daily_income, 2),
                    "avg_daily_expense": round(avg_daily_expense, 2),
                    "forecast": forecast
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
# TOP MERCHANTS
# ============================================

@router.get("/top-merchants")
def get_top_merchants(days: int = 30, limit: int = 10):
    """Get top merchants by spending"""
    try:
        with SessionLocal() as db:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            
            # Group by label and sum expenses
            results = db.query(
                BankTransactionEnhanced.label,
                func.count(BankTransactionEnhanced.id).label('count'),
                func.sum(BankTransactionEnhanced.amount).label('total')
            )\
            .filter(
                BankTransactionEnhanced.date >= start_date,
                BankTransactionEnhanced.date <= end_date,
                BankTransactionEnhanced.amount < 0  # Only expenses
            )\
            .group_by(BankTransactionEnhanced.label)\
            .order_by(func.sum(BankTransactionEnhanced.amount).asc())\
            .limit(limit)\
            .all()
            
            merchants = []
            for r in results:
                merchants.append({
                    "merchant": r.label,
                    "transaction_count": r.count,
                    "total_spent": round(abs(float(r.total or 0)), 2)
                })
            
            return JSONResponse(
                content={
                    "period_days": days,
                    "merchants": merchants
                },
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )
