import os
import time
import asyncio
from typing import List, Optional
from collections import defaultdict

import httpx
import pandas as pd
from jose import jwt, JWTError
from fastapi import (
    FastAPI, UploadFile, File, HTTPException,
    Request, Response, Depends, Form
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------
# INTERNAL IMPORTS
# ---------------------------------------------------------------------
from app.models import AnalysisResult
from app.analyzers import analyze_trial_balance
from app.database import Base, engine
from .routers import bank, invoices, alerts, cashflow, overdue

# =====================================================
# HTTPS REDIRECT MIDDLEWARE
# =====================================================
class HTTPSRedirectMiddleware:
    """Force HTTPS on Railway by checking x-forwarded-proto header"""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            forwarded_proto = headers.get(b"x-forwarded-proto", b"https").decode()
            
            if forwarded_proto == "http":
                host = headers.get(b"host", b"").decode()
                path = scope.get("path", "")
                query = scope.get("query_string", b"").decode()
                url = f"https://{host}{path}"
                if query:
                    url += f"?{query}"
                
                response = JSONResponse(
                    {"detail": "Redirecting to HTTPS"},
                    status_code=301,
                    headers={"Location": url}
                )
                await response(scope, receive, send)
                return
        
        await self.app(scope, receive, send)

# ---------------------------------------------------------------------
# FASTAPI APP
# ---------------------------------------------------------------------
app = FastAPI(title="Optimis Fiscale MVP", version="0.2.1")

# =====================================================
# MIDDLEWARE CONFIGURATION
# =====================================================

# 1. HTTPS Redirect (must be first)
app.add_middleware(HTTPSRedirectMiddleware)

# 2. CORS (global configuration)
_env_origins = os.getenv("ALLOWED_ORIGIN")
if _env_origins:
    ALLOWED_ORIGINS = [o.strip() for o in _env_origins.split(",") if o.strip()]
else:
    ALLOWED_ORIGINS = [
        "https://qazwsxres.github.io",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600
)

# =====================================================
# DATABASE SETUP (SINGLE STARTUP EVENT)
# =====================================================
@app.on_event("startup")
def create_tables():
    """Create all database tables on startup"""
    print("🚀 Creating database tables if missing…")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")

# =====================================================
# CORS HEADERS HELPER
# =====================================================
def get_cors_headers():
    """Standard CORS headers for all responses"""
    origin = ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else "*"
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "*"
    }

# =====================================================
# GLOBAL OPTIONS HANDLER
# =====================================================
@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    """Handle all OPTIONS requests globally"""
    return JSONResponse(
        content={"message": "OK"},
        status_code=200,
        headers=get_cors_headers()
    )

# ---------------------------------------------------------------------
# AUTH & SECURITY
# ---------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or SECRET_KEY == "CHANGE_ME":
    raise RuntimeError("SECRET_KEY must be set in Railway variables")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ALGO = "HS256"
COOKIE_NAME = "session"


def validate_company_password(company_id: str, password: str) -> bool:
    expected = os.getenv(f"COMPANY_{company_id}_PASSWORD")
    return bool(expected and password == expected)


def make_token(company_id: str, ttl_seconds: int = 60 * 60) -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": company_id, "iat": now, "exp": now + ttl_seconds},
        SECRET_KEY,
        algorithm=ALGO,
    )


def parse_token(token: str) -> str:
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=[ALGO])
        return decoded["sub"]
    except JWTError:
        raise HTTPException(401, "Invalid or expired session")


def set_session_cookie(resp: Response, token: str):
    resp.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,  # HTTPS only
        samesite="none",
        path="/",
        max_age=3600,
    )


def require_auth(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(401, "Not authenticated")
    return parse_token(token)


# ---------------------------------------------------------------------
# HEALTH ROUTES
# ---------------------------------------------------------------------
@app.get("/")
def root():
    return JSONResponse(
        content={
            "ok": True,
            "service": "optimis-fiscale-api",
            "https": "enforced"
        },
        headers=get_cors_headers()
    )


@app.get("/health")
def health():
    return JSONResponse(
        content={"status": "ok"},
        headers=get_cors_headers()
    )


# ---------------------------------------------------------------------
# ANALYSIS
# ---------------------------------------------------------------------
@app.post("/analyze/trial-balance", response_model=AnalysisResult)
async def analyze_trial_balance_endpoint(
    file: UploadFile = File(...),
    turnover: float | None = None,
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Veuillez fournir un CSV.")

    import io
    try:
        df = pd.read_csv(io.BytesIO(await file.read()))
        df.columns = df.columns.str.lower().str.strip()
    except Exception:
        raise HTTPException(400, "CSV illisible")

    result = analyze_trial_balance(df, turnover=turnover)
    return JSONResponse(
        content=result.model_dump(),
        headers=get_cors_headers()
    )


@app.post("/analyze/json", response_model=AnalysisResult)
async def analyze_json_endpoint(payload: dict):
    try:
        df = pd.DataFrame(payload["trial_balance"])
        df.columns = df.columns.str.lower().str.strip()
    except Exception:
        raise HTTPException(400, "JSON invalide")

    result = analyze_trial_balance(df, payload.get("turnover"))
    return JSONResponse(
        content=result.model_dump(),
        headers=get_cors_headers()
    )


# ---------------------------------------------------------------------
# AUTH ROUTES
# ---------------------------------------------------------------------
class LoginBody(BaseModel):
    company_id: str
    password: str


@app.post("/auth/login")
def login(body: LoginBody, response: Response):
    if not validate_company_password(body.company_id, body.password):
        raise HTTPException(401, "Bad credentials")

    token = make_token(body.company_id)
    set_session_cookie(response, token)
    
    return JSONResponse(
        content={"ok": True, "company_id": body.company_id},
        headers=get_cors_headers()
    )


@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return JSONResponse(
        content={"ok": True},
        headers=get_cors_headers()
    )


# ---------------------------------------------------------------------
# CHAT
# ---------------------------------------------------------------------
class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


class ChatResponse(BaseModel):
    reply: str


_last_call = defaultdict(float)


def throttle(cid: str, interval=2.0):
    now = time.time()
    if now - _last_call[cid] < interval:
        raise HTTPException(429, "Trop de requêtes")
    _last_call[cid] = now


async def call_openai_with_retry(payload, api_key, max_retries=4):
    backoff = 1.5
    async with httpx.AsyncClient(timeout=40) as client:
        for attempt in range(max_retries):
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
            if r.status_code == 429:
                await asyncio.sleep(backoff)
                backoff *= 2
                continue
            raise HTTPException(502, f"OpenAI error {r.status_code}: {r.text[:200]}")
    raise HTTPException(429, "OpenAI rate limit reached")


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, company_id: str = Depends(require_auth)):
    if not OPENAI_API_KEY:
        raise HTTPException(500, "Server missing OPENAI_API_KEY")

    throttle(company_id)
    payload = {
        "model": "gpt-4o-mini",
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": "Tu es Albert, assistant fiscal pour PME françaises.",
            },
            *[m.model_dump() for m in req.messages],
        ],
    }
    reply = await call_openai_with_retry(payload, OPENAI_API_KEY)
    
    return JSONResponse(
        content={"reply": reply},
        headers=get_cors_headers()
    )


# ---------------------------------------------------------------------
# ROUTERS
# ---------------------------------------------------------------------
app.include_router(bank.router)
app.include_router(invoices.router)
app.include_router(alerts.router)
app.include_router(cashflow.router)
app.include_router(overdue.router)


# ---------------------------------------------------------------------
# AUDIT
# ---------------------------------------------------------------------
class AuditIssue(BaseModel):
    code: str
    severity: str
    message: str
    count: Optional[int] = None


class AuditSummary(BaseModel):
    ok: bool
    total_rows: int
    total_debit: float
    total_credit: float
    imbalance: float
    framework: str


class AuditResult(BaseModel):
    summary: AuditSummary
    issues: List[AuditIssue]
    top_accounts: List[dict]


@app.post("/audit/test", response_model=AuditResult)
async def test_audit(
    file: UploadFile = File(...),
    standard: str = Form("IFRS"),
    company_id: str = Depends(require_auth),
):
    import io

    df = pd.read_csv(io.BytesIO(await file.read()))
    df.columns = df.columns.str.strip().str.lower()

    required = {"account", "label", "debit", "credit"}
    if not required.issubset(df.columns):
        raise HTTPException(400, "Colonnes manquantes")

    df["debit"] = pd.to_numeric(df["debit"], errors="coerce").fillna(0)
    df["credit"] = pd.to_numeric(df["credit"], errors="coerce").fillna(0)

    total_debit = df["debit"].sum()
    total_credit = df["credit"].sum()
    imbalance = abs(total_debit - total_credit)

    issues = []
    if imbalance > 0.01:
        issues.append(
            AuditIssue(
                code="IMBALANCE",
                severity="error",
                message=f"Écart de {imbalance:.2f}€",
            )
        )

    summary = AuditSummary(
        ok=imbalance <= 0.01,
        total_rows=len(df),
        total_debit=round(total_debit, 2),
        total_credit=round(total_credit, 2),
        imbalance=round(imbalance, 2),
        framework="USGAAP" if standard.upper().startswith("US") else "IFRS",
    )

    df["balance"] = df["debit"] - df["credit"]
    grp = df.groupby(["account", "label"])["balance"].sum().reset_index()
    grp["abs_balance"] = grp["balance"].abs()
    top = grp.sort_values("abs_balance", ascending=False).head(10)
    top = top.to_dict(orient="records")

    result = AuditResult(summary=summary, issues=issues, top_accounts=top)
    
    return JSONResponse(
        content=result.model_dump(),
        headers=get_cors_headers()
    )


# =====================================================
# GLOBAL EXCEPTION HANDLER
# =====================================================
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers=get_cors_headers()
    )
