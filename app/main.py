import os, time, httpx, logging
from typing import List
from jose import jwt, JWTError
from fastapi import Request, Response, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from .models import AnalysisResult
from .analyzers import analyze_trial_balance

app = FastAPI(title="Optimis Fiscale MVP", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/analyze/trial-balance", response_model=AnalysisResult)
async def analyze_trial_balance_endpoint(file: UploadFile = File(...), turnover: float | None = None):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Veuillez fournir un CSV (colonnes: account,label,debit,credit).")
    content = await file.read()
    try:
        import io
        df = pd.read_csv(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"CSV illisible: {e}")
    try:
        return analyze_trial_balance(df, turnover=turnover)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/analyze/json", response_model=AnalysisResult)
async def analyze_json_endpoint(payload: dict):
    # Attendu : payload = {"trial_balance": [{account,label,debit,credit}, ...], "turnover": 123456.78}
    try:
        df = pd.DataFrame(payload["trial_balance"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"JSON invalide : {e}")
    turnover = payload.get("turnover")
    return analyze_trial_balance(df, turnover=turnover)
