from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import csv
from io import TextIOWrapper

router = APIRouter(prefix="/bank", tags=["Bank"])

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://qazwsxres.github.io",
    "Access-Control-Allow-Credentials": "true",
}

_bank_summary = {
    "balance": 0.0,
    "inflows": 0.0,
    "outflows": 0.0,
}


# ---------------- BANK UPLOAD ----------------

@router.post("/upload")
async def upload_bank_statement(file: UploadFile = File(...)):
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

        for row in reader:
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
            except:
                continue

            if amount >= 0:
                inflows += amount
            else:
                outflows += amount

        balance = inflows + outflows

        _bank_summary["balance"] = balance
        _bank_summary["inflows"] = inflows
        _bank_summary["outflows"] = outflows

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
