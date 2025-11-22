from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import date
from ..database import SessionLocal
from ..models_extended import BankTransaction, DailyCashflow

router = APIRouter(prefix="/cashflow", tags=["Cashflow"])

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://qazwsxres.github.io",
    "Access-Control-Allow-Credentials": "true",
}


@router.post("/compute")
def compute_daily_cashflow():
    """
    Recompute daily balances from BankTransaction table.
    """
    with SessionLocal() as db:
        tx = db.query(BankTransaction).order_by(BankTransaction.date.asc()).all()

        daily = {}
        for t in tx:
            daily.setdefault(t.date, 0)
            daily[t.date] += t.amount

        running = 0
        result = []
        for day in sorted(daily.keys()):
            running += daily[day]
            result.append({"date": str(day), "balance": running})

        db.query(DailyCashflow).delete()
        for row in result:
            db.add(DailyCashflow(
                date=row["date"],
                balance=row["balance"]
            ))
        db.commit()

        return JSONResponse(
            content={"ok": True, "count": len(result)},
            headers=CORS_HEADERS
        )


@router.get("/daily")
def get_daily_cashflow():
    """
    Return prepared daily cashflow table.
    """
    with SessionLocal() as db:
        items = db.query(DailyCashflow).order_by(DailyCashflow.date.asc()).all()
        data = [{"date": str(row.date), "balance": row.balance} for row in items]

        return JSONResponse(content=data, headers=CORS_HEADERS)

@router.get("/forecast")
def get_forecast():
    """
    30-day cashflow forecast:
      - Starts from last daily cashflow balance
      - Adds incoming invoice payments on due_date
      - Subtracts purchase invoices on due_date
    """
    with SessionLocal() as db:

        # 1. Load last known daily cashflow
        daily = db.query(DailyCashflow).order_by(DailyCashflow.date.asc()).all()
        if not daily:
            return JSONResponse({"error": "No cashflow data"}, status_code=400)

        last_balance = float(daily[-1].balance)
        start_date = daily[-1].date

        # 2. Load invoices
        sales = db.query(InvoiceSale).filter(InvoiceSale.status != "paid").all()
        purchases = db.query(InvoicePurchase).filter(InvoicePurchase.status != "paid").all()

        # 3. Construct 30-day future window
        from datetime import timedelta

        forecast = []
        balance = last_balance

        for i in range(1, 31):
            day = start_date + timedelta(days=i)

            # incoming payments
            for inv in sales:
                if inv.due_date == day:
                    balance += float(inv.amount)

            # outgoing payments
            for inv in purchases:
                if inv.due_date == day:
                    balance -= float(inv.amount)

            forecast.append({"date": str(day), "balance": balance})

        return JSONResponse(forecast, headers=CORS_HEADERS)
