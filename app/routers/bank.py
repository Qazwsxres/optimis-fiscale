from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
import csv
from io import TextIOWrapper

router = APIRouter(prefix="/bank", tags=["Bank"])

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://qazwsxres.github.io",
    "Access-Control-Allow-Credentials": "true",
}

# Global in-memory state
_bank_summary = {
    "balance": 0.0,
    "inflows": 0.0,
    "outflows": 0.0,
}

# NEW: daily cashflow (list of {"date": "YYYY-MM-DD", "balance": float})
_bank_daily = []


# ---------------- BANK UPLOAD ----------------

@router.post("/upload")
async def upload_bank_statement(file: UploadFile = File(...)):
    """
    Upload a bank statement CSV and compute:
    - inflows / outflows / total balance
    - daily cumulative balance line for /bank/cashflow
    """
    global _bank_summary, _bank_daily

    if file.content_type not in ("text/csv", "application/vnd.ms-excel"):
        return JSONResponse(
            content={"detail": "Veuillez fournir un fichier CSV"},
            status_code=400,
            headers=CORS_HEADERS
        )

    try:
        wrapper = TextIOWrapper(file.file, encoding="utf-8")
        reader = csv.DictReader(wrapper)

        inflows = 0.0
        outflows = 0.0
        per_day = {}  # date_str -> total amount that day

        for row in reader:
            # --- Amount ---
            raw_amount = (
                row.get("amount")
                or row.get("montant")
                or row.get("Amount")
                or row.get("Montant")
            )
            if raw_amount is None:
                continue

            try:
                amount = float(str(raw_amount).replace(",", "."))
            except Exception:
                continue

            # --- Date ---
            raw_date = (
                row.get("date")
                or row.get("Date")
                or row.get("transaction_date")
            )
            if not raw_date:
                continue

            # Keep only YYYY-MM-DD part
            date_str = str(raw_date).split(" ")[0]

            # Aggregate by day
            per_day.setdefault(date_str, 0.0)
            per_day[date_str] += amount

            # Summary totals
            if amount >= 0:
                inflows += amount
            else:
                outflows += amount

        # Compute cumulative daily balance
        balance = 0.0
        daily = []
        for day in sorted(per_day.keys()):
            balance += per_day[day]
            daily.append({"date": day, "balance": balance})

        # Store in globals
        _bank_summary["balance"] = balance
        _bank_summary["inflows"] = inflows
        _bank_summary["outflows"] = outflows
        _bank_daily = daily

        return JSONResponse(
            content={
                "ok": True,
                "balance": balance,
                "inflows": inflows,
                "outflows": outflows,
            },
            headers=CORS_HEADERS
        )

    except Exception as e:
        return JSONResponse(
            content={"detail": f"Erreur fichier: {e}"},
            status_code=500,
            headers=CORS_HEADERS
        )


# ---------------- BANK SUMMARY ----------------

@router.get("/summary")
def bank_summary():
    return JSONResponse(
        content=_bank_summary,
        headers=CORS_HEADERS
    )


# ---------------- DAILY CASHFLOW ----------------

@router.get("/cashflow")
def bank_cashflow():
    """
    Returns the daily cumulative balance line, used by the front-end chart.
    Format: [{"date": "2025-01-01", "balance": 1234.56}, ...]
    """
    return JSONResponse(
        content=_bank_daily,
        headers=CORS_HEADERS
    )
