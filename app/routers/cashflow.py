from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime, date
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
    Recompute daily balances from all bank transactions.
    """
    with SessionLocal() as db:
        # fetch all transactions
        tx = db.query(BankTransaction).order_by(BankTransaction.date.asc()).all()

        daily = {}
        for t in tx:
            if t.date not in daily:
                daily[t.date] = 0
            daily[t.date] += t.amount

        # compute running balance
        running = 0
        result = []
        for day in sorted(daily.keys()):
            running += daily[day]
            result.append({"date": str(day), "balance": running})

        # clear & repopulate table
        db.query(DailyCashflow).delete()
        for row in result:
            obj = DailyCashflow(date=row["date"], balance=row["balance"])
            db.add(obj)

        db.commit()

        return JSONResponse(
            content={"ok": True, "count": len(result)},
            headers=CORS_HEADERS
        )


@router.get("/daily")
def get_daily_cashflow():
    """
    Return daily cashflow from DB.
    """
    with SessionLocal() as db:
        items = db.query(DailyCashflow).order_by(DailyCashflow.date.asc()).all()
        data = [{"date": str(i.date), "balance": i.balance} for i in items]

        return JSONResponse(
            content=data,
            headers=CORS_HEADERS
        )
