import os, time, httpx, logging
from typing import List

from fastapi import FastAPI, UploadFile, File, Request, Response, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import pandas as pd
from .models import AnalysisResult
from .analyzers import analyze_trial_balance

# (Optional) keep only errors in access logs so no request lines with payloads get logged
logging.getLogger("uvicorn.access").disabled = True

app = FastAPI(title="Optimis Fiscale MVP", version="0.1.0")

# --- CORS (lock to your Pages origin) ---
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN") or "https://qazwsxres.github.io"
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=True,   # needed for cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Auth/session + LLM config ---
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_ME")   # set in Railway
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
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

# --- Health & root ---
@app.get("/")
def root():
    return {"ok": True, "service": "optimis-fiscale-api"}

@app.get("/health")
def health():
    return {"status": "ok"}

# --- Analysis endpoints ---
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

# --- Auth + Chat (ephemeral, private) ---
from jose import jwt, JWTError  # keep after FastAPI app is created

class LoginBody(BaseModel):
    company_id: str
    password: str

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

class ChatResponse(BaseModel):
    reply: str

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

@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, company_id: str = Depends(require_auth)):
    """Ephemeral chat: no content is stored."""
    if not OPENAI_API_KEY:
        raise HTTPException(500, "Server missing OPENAI_API_KEY")

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Tu es Albert, un assistant fiscal pour les PME françaises. Sois professionnel, clair et concis."},
            *[m.model_dump() for m in req.messages],
        ],
        "temperature": 0.2,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        r.raise_for_status()
        data = r.json()
        reply = data["choices"][0]["message"]["content"]
        return ChatResponse(reply=reply)
    except httpx.HTTPError as e:
        raise HTTPException(500, f"Chat backend error: {e}")
