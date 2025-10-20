import os, time, logging, asyncio
from typing import List

import httpx
import pandas as pd
from jose import jwt, JWTError
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from collections import defaultdict

from .models import AnalysisResult
from .analyzers import analyze_trial_balance

# -----------------------------------------------------------------------------
# App & CORS
# -----------------------------------------------------------------------------
app = FastAPI(title="Optimis Fiscale MVP", version="0.1.0")

ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN") or "https://qazwsxres.github.io"  # your Pages origin

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=True,    # allow cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------------------------
# Auth & Secrets
# -----------------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME")   # set in Railway
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")        # set in Railway
ALGO = "HS256"
COOKIE_NAME = "session"

def validate_company_password(company_id: str, password: str) -> bool:
    env_key = f"COMPANY_{company_id}_PASSWORD"
    expected = os.getenv(env_key)
    return bool(expected and password == expected)

def make_token(company_id: str, ttl_seconds: int = 60 * 60) -> str:
    now = int(time.time())
    return jwt.encode({"sub": company_id, "iat": now, "exp": now + ttl_seconds}, SECRET_KEY, algorithm=ALGO)

def parse_token(token: str) -> str:
    try:
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGO])
        return data["sub"]
    except JWTError:
        raise HTTPException(401, "Invalid or expired session")

def set_session_cookie(resp: Response, token: str):
    # Cross-site cookie so GitHub Pages (frontend) can use Railway API
    resp.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        path="/",
        max_age=60 * 60,
    )

def require_auth(request: Request) -> str:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(401, "Not authenticated")
    return parse_token(token)

# -----------------------------------------------------------------------------
# Health & root
# -----------------------------------------------------------------------------
@app.get("/")
def root():
    return {"ok": True, "service": "optimis-fiscale-api"}

@app.get("/health")
def health():
    return {"status": "ok"}

# -----------------------------------------------------------------------------
# Analysis endpoints
# -----------------------------------------------------------------------------
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
    # Attendu : {"trial_balance": [{account,label,debit,credit}, ...], "turnover": 123456.78}
    try:
        df = pd.DataFrame(payload["trial_balance"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"JSON invalide : {e}")
    turnover = payload.get("turnover")
    return analyze_trial_balance(df, turnover=turnover)

# -----------------------------------------------------------------------------
# Auth endpoints
# -----------------------------------------------------------------------------
class LoginBody(BaseModel):
    company_id: str
    password: str

@app.post("/auth/login")
def login(body: LoginBody, response: Response):
    if not validate_company_password(body.company_id, body.password):
        raise HTTPException(401, "Bad credentials")
    token = make_token(body.company_id)
    set_session_cookie(response, token)
    return {"ok": True, "company_id": body.company_id}

@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}

# -----------------------------------------------------------------------------
# Chat endpoint with retry/backoff + throttle
# -----------------------------------------------------------------------------
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

class ChatResponse(BaseModel):
    reply: str

# Very small in-memory throttle per company (best-effort, single-process)
_last_call = defaultdict(float)
def throttle(company_id: str, min_interval: float = 2.0):
    now = time.time()
    if now - _last_call[company_id] < min_interval:
        raise HTTPException(429, "Trop de requêtes. Réessayez dans 2–3 secondes.")
    _last_call[company_id] = now

async def call_openai_with_retry(json_payload, api_key, max_retries: int = 4) -> str:
    """
    Call OpenAI Chat Completions with exponential backoff.
    Respects Retry-After when provided. Raises HTTPException on failure.
    """
    backoff = 1.5  # seconds
    async with httpx.AsyncClient(timeout=40) as client:
        for attempt in range(1, max_retries + 1):
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=json_payload,
            )
            if r.status_code == 200:
                data = r.json()
                return data["choices"][0]["message"]["content"]

            if r.status_code == 429 and attempt < max_retries:
                retry_after = r.headers.get("retry-after")
                wait_s = float(retry_after) if retry_after else backoff
                await asyncio.sleep(wait_s)
                backoff *= 2
                continue

            # Other error or no retries left
            try:
                r.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise HTTPException(
                    status_code=502,
                    detail=f"OpenAI error {e.response.status_code}: {e.response.text[:200]}",
                )

        raise HTTPException(429, "OpenAI rate limit: merci de réessayer dans quelques secondes.")

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, company_id: str = Depends(require_auth)):
    """Ephemeral chat: no content is stored."""
    if not OPENAI_API_KEY:
        raise HTTPException(500, "Server missing OPENAI_API_KEY")

    # avoid accidental spam
    throttle(company_id, min_interval=2.0)

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Tu es Albert, un assistant fiscal pour les PME françaises. Sois professionnel, clair et concis."},
            *[m.model_dump() for m in req.messages],
        ],
        "temperature": 0.2,
    }

    reply = await call_openai_with_retry(payload, OPENAI_API_KEY, max_retries=4)
    return ChatResponse(reply=reply)
