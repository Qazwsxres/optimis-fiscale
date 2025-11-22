from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import csv
from io import TextIOWrapper

router = APIRouter(prefix="/bank", tags=["Bank"])

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://qazwsxres.github.io",
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Methods": "*",
    "Access-Control-Allow-Headers": "*",
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
        raise HTTPException(400, "File must be CSV")

    try:
        wrapper = TextIOWrapper(file.file, encoding="utf-8")
        reader = csv.DictReader(wrapper)

        required = {"date", "label", "amount", "balance", "category", "transaction_type"}
        if not required.issubset({c.strip().lower() for c in reader.fieldnames}):
            raise HTTPException(
                400,
                f"Missing required columns. CSV must contain: {', '.join(required)}"
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
            headers=CORS_HEADERS
        )

    except Exception as e:
        raise HTTPException(500, f"Erreur lecture CSV: {e}")


@router.get("/summary")
def bank_summary():
    return JSONResponse(_bank_summary, headers=CORS_HEADERS)


@router.get("/transactions")
def bank_transactions():
    return JSONResponse(_bank_transactions, headers=CORS_HEADERS)


@router.get("/daily")
def bank_daily():
    return JSONResponse(_bank_daily, headers=CORS_HEADERS)


@router.options("/{path:path}")
def options_handler():
    return JSONResponse({"ok": True}, headers=CORS_HEADERS)
