from fastapi import APIRouter, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
import pandas as pd, io
from ..database import SessionLocal
from ..models_extended import BankTransaction

router = APIRouter(prefix="/bank", tags=["Bank"])

@router.post("/upload")
async def upload_bank_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Veuillez fournir un fichier CSV.")
    content = await file.read()
    df = pd.read_csv(io.BytesIO(content))
    required = {"Date", "Label", "Amount"}
    if not required.issubset(df.columns):
        raise HTTPException(400, f"Colonnes manquantes : {', '.join(required - set(df.columns))}")
    with SessionLocal() as db:
        for _, row in df.iterrows():
            db.add(BankTransaction(
                date=row["Date"],
                label=row["Label"],
                amount=row["Amount"],
                balance=row.get("Balance")
            ))
        db.commit()
    return {"ok": True, "rows": len(df)}

@router.get("/summary")
def get_summary():
    with SessionLocal() as db:
        latest = db.query(BankTransaction).order_by(BankTransaction.date.desc()).first()
        inflows = db.query(func.sum(BankTransaction.amount)).filter(BankTransaction.amount > 0).scalar() or 0
        outflows = db.query(func.sum(BankTransaction.amount)).filter(BankTransaction.amount < 0).scalar() or 0
    return {
        "balance": float(latest.balance) if latest and latest.balance else float(inflows + outflows),
        "inflows": float(inflows),
        "outflows": float(outflows)
    }
