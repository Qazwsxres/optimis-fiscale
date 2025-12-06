import os
from datetime import date, timedelta
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..database import SessionLocal
from ..models_extended import (
    BankTransaction,
    DailyCashflow,
    InvoiceSale,
    InvoicePurchase,
)

router = APIRouter(prefix="/cashflow", tags=["Cashflow"])

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


@router.post("/compute")
def compute_daily_cashflow():
    """
    Recompute daily balances from BankTransaction table and persist them
    into `cashflow_daily`.
    """
    try:
        with SessionLocal() as db:
            tx = (
                db.query(BankTransaction)
                .order_by(BankTransaction.date.asc())
                .all()
            )

            # aggregate by date
            daily_totals: dict[date, float] = {}
            for t in tx:
                daily_totals.setdefault(t.date, 0.0)
                daily_totals[t.date] += float(t.amount)

            running = 0.0
            result = []
            for d in sorted(daily_totals.keys()):
                running += daily_totals[d]
                result.append({"date": d, "balance": running})

            # reset table
            db.query(DailyCashflow).delete()
            for row in result:
                db.add(
                    DailyCashflow(
                        date=row["date"],
                        balance=row["balance"],
                    )
                )
            db.commit()

            return JSONResponse(
                content={"ok": True, "count": len(result)},
                headers=get_cors_headers(),
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


@router.get("/daily")
def get_daily_cashflow():
    """Return prepared daily cashflow table."""
    try:
        with SessionLocal() as db:
            items = (
                db.query(DailyCashflow)
                .order_by(DailyCashflow.date.asc())
                .all()
            )
            data = [
                {"date": str(row.date), "balance": float(row.balance or 0)}
                for row in items
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


@router.get("/forecast")
def get_forecast():
    """
    30-day cashflow forecast:
      - Starts from last DailyCashflow balance
      - Adds incoming sales invoices on due_date
      - Subtracts purchase invoices on due_date
    """
    try:
        with SessionLocal() as db:
            daily = (
                db.query(DailyCashflow)
                .order_by(DailyCashflow.date.asc())
                .all()
            )
            if not daily:
                return JSONResponse(
                    content={"error": "No cashflow data"},
                    status_code=400,
                    headers=get_cors_headers(),
                )

            last_balance = float(daily[-1].balance or 0)
            start_date = daily[-1].date

            sales = (
                db.query(InvoiceSale)
                .filter(InvoiceSale.status != "paid")
                .all()
            )
            purchases = (
                db.query(InvoicePurchase)
                .filter(InvoicePurchase.status != "paid")
                .all()
            )

            forecast = []
            balance = last_balance
            for i in range(1, 31):
                day = start_date + timedelta(days=i)

                for inv in sales:
                    if inv.due_date == day:
                        balance += float(inv.amount_ttc or 0)

                for inv in purchases:
                    if inv.due_date == day:
                        balance -= float(inv.amount or 0)

                forecast.append({"date": str(day), "balance": balance})

            return JSONResponse(
                content=forecast,
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )
