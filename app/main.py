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

ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN") or "https://qazwsxres.github.io"

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],  # only your Pages site
    allow_credentials=True,          # allow cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME")   # set in Railway
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")        # set in Railway
ALGO = "HS256"
COOKIE_NAME = "session"

def validate_company_password(company_id: str, password: str) -> bool:
    env_key = f"COMPANY_{company_id}_PASSWORD"
    expected = os.getenv(env_key)
    return bool(expected and password == expected)

def make_token(company_id: str, ttl_seconds: int = 60*60) -> str:
    now = int(time.time())
    return jwt.encode({"sub": company_id, "iat": now, "exp": now + ttl_seconds}, SECRET_KEY, algorithm=ALGO)

def parse_token(token: str) -> str:
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGO])
        return data["sub"]
    except JWTError:
        raise HTTPException(401, "Invalid or expired session")

def set_session_cookie(resp: Response, token: str):
    resp.set_cookie(
        key=COOKIE_NAME, value=token, httponly=True, secure=True,
        samesite="strict", path="/", max_age=60*60
    )

def require_auth(request: Request) -> str:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(401, "Not authenticated")
    return parse_token(token)

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
