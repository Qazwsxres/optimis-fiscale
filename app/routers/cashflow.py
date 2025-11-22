from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from ..database import SessionLocal
from ..models_extended import (
    BankTransaction,
    DailyCashflow,
    InvoiceSale,
    InvoicePurchase
)

router = APIRouter(prefix="/cashflow", tags=["Cashflow"])

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://qazwsxres.github.io",
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Methods": "*",
    "Access-Control-Allow-Headers": "*",
}


# =========================================================
#   POST /cashflow/compute
# =========================================================
@router.post("/compute")
def compute_daily_cashflow():
    """Recompute daily balances from bank transactions."""
    with SessionLocal() as db:
        tx = db.query(BankTransaction).order_by(BankTransaction.date.asc()).all()

        daily = {}
        for t in tx:
            daily.setdefault(t.date, 0)
            daily[t.date] += float(t.amount)

        running = 0
        result = []
        for day in sorted(daily.keys()):
            running += daily[day]
            result.append({"date": str(day), "balance": running})

        # Reset table
        db.query(DailyCashflow).delete()

        for row in result:
            db.add(DailyCashflow(
                date=datetime.fromisoformat(row["date"]).date(),
                balance=row["balance"]
            ))

        db.commit()

        return JSONResponse(
            content={"ok": True, "count": len(result)},
            headers=CORS_HEADERS
        )


# =========================================================
#   GET /cashflow/daily
# =========================================================
@router.get("/daily")
def get_daily_cashflow():
    """Return daily cumulative cashflow."""
    with SessionLocal() as db:
        items = db.query(DailyCashflow).order_by(DailyCashflow.date.asc()).all()
        data = [{"date": str(row.date), "balance": float(row.balance)} for row in items]

        return JSONResponse(content=data, headers=CORS_HEADERS)


# =========================================================
#   GET /cashflow/forecast  (30-day)
# =========================================================
@router.get("/forecast")
def get_forecast():
    """Return 30-day cashflow prediction using invoice due dates."""
    with SessionLocal() as db:

        # Load last known daily balance
        daily = db.query(DailyCashflow).order_by(DailyCashflow.date.asc()).all()
        if not daily:
            return JSONResponse(
                {"error": "No cashflow data"},
                status_code=400,
                headers=CORS_HEADERS
            )

        last_balance = float(daily[-1].balance)
        start_date = daily[-1].date

        # Load unpaid invoices
        sales = db.query(InvoiceSale).filter(InvoiceSale.status != "paid").all()
        purchases = db.query(InvoicePurchase).filter(InvoicePurchase.status != "paid").all()

        forecast = []
        balance = last_balance

        for i in range(1, 31):
            day = start_date + timedelta(days=i)

            # incoming invoices
            for inv in sales:
                if inv.due_date and inv.due_date == day:
                    balance += float(inv.amount)

            # outgoing invoices
            for inv in purchases:
                if inv.due_date and inv.due_date == day:
                    balance -= float(inv.amount)

            forecast.append({"date": str(day), "balance": balance})

        return JSONResponse(forecast, headers=CORS_HEADERS)


# =========================================================
#   OPTIONS (CORS preflight)
# =========================================================
@router.options("/{path:path}")
def opts(path: str):
    return JSONResponse({"ok": True}, headers=CORS_HEADERS)
