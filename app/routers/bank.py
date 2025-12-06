import os
import csv
from io import TextIOWrapper
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/bank", tags=["Bank"])

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

# In-memory state
_bank_summary = {
    "balance": 0.0,
    "inflows": 0.0,
    "outflows": 0.0,
}

_bank_daily = []      # list of {date, balance}
_bank_transactions = []  # full parsed CSV


@router.post("/upload")
async def upload_bank_csv(file: UploadFile = File(...)):
    """
    Uploads a bank CSV with columns:
    date,label,amount,balance,category,transaction_type
    Computes:
      - inflows / outflows
      - final balance
      - daily cumulative balance
    """
    global _bank_summary, _bank_daily, _bank_transactions

    if file.content_type not in ("text/csv", "application/vnd.ms-excel"):
        return JSONResponse(
            status_code=400,
            content={"error": "File must be CSV"},
            headers=get_cors_headers()
        )

    try:
        wrapper = TextIOWrapper(file.file, encoding="utf-8")
        reader = csv.DictReader(wrapper)

        required = {"date", "label", "amount", "balance", "category", "transaction_type"}
        if not required.issubset({c.strip().lower() for c in reader.fieldnames}):
            return JSONResponse(
                status_code=400,
                content={
                    "error": f"Missing required columns. CSV must contain: {', '.join(required)}"
                },
                headers=get_cors_headers()
            )

        _bank_transactions = []
        per_day = {}
        inflows = 0.0
        outflows = 0.0

        for row in reader:
            date_str = row["date"].split(" ")[0]

            try:
                amount = float(row["amount"])
            except:
                continue

            # Save full transaction
            _bank_transactions.append({
                "date": date_str,
                "label": row["label"],
                "amount": amount,
                "balance": float(row["balance"]),
                "category": row["category"],
                "transaction_type": row["transaction_type"]
            })

            # Daily accumulation
            per_day.setdefault(date_str, 0.0)
            per_day[date_str] += amount

            if amount >= 0:
                inflows += amount
            else:
                outflows += amount

        # Compute cumulative daily balance
        running = 0
        _bank_daily = []
        for day in sorted(per_day.keys()):
            running += per_day[day]
            _bank_daily.append({"date": day, "balance": running})

        _bank_summary = {
            "balance": running,
            "inflows": inflows,
            "outflows": outflows
        }

        return JSONResponse(
            content={
                "ok": True,
                "summary": _bank_summary,
                "count": len(_bank_transactions)
            },
            headers=get_cors_headers()
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Erreur lecture CSV: {e}"},
            headers=get_cors_headers()
        )


@router.get("/summary")
def bank_summary():
    return JSONResponse(
        content=_bank_summary,
        headers=get_cors_headers()
    )


@router.get("/transactions")
def bank_transactions():
    return JSONResponse(
        content=_bank_transactions,
        headers=get_cors_headers()
    )


@router.get("/daily")
def bank_daily():
    return JSONResponse(
        content=_bank_daily,
        headers=get_cors_headers()
    )
