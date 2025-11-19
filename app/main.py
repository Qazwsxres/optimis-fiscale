import os
import time
import logging
import asyncio
from typing import List, Optional
from collections import defaultdict
from .routers import cashflow
app.include_router(cashflow.router)

import httpx
import pandas as pd
from jose import jwt, JWTError
from fastapi import (
    FastAPI, UploadFile, File, HTTPException,
    Request, Response, Depends, Form
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ---------------------------------------------------------------------
# App imports (your existing analyzers & routers)
# ---------------------------------------------------------------------
from app.models import AnalysisResult
from app.analyzers import analyze_trial_balance
from .routers import bank, invoices, alerts

# ---------------------------------------------------------------------
# App & CORS
# ---------------------------------------------------------------------
app = FastAPI(title="Optimis Fiscale MVP", version="0.2.1")

# Allow GitHub Pages + local dev by default
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
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------
# Auth & Secrets
# ---------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY or SECRET_KEY == "CHANGE_ME":
    raise RuntimeError("SECRET_KEY must be set in environment")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ALGO = "HS256"
COOKIE_NAME = "session"


def validate_company_password(company_id: str, password: str) -> bool:
    env_key = f"COMPANY_{company_id}_PASSWORD"
    expected = os.getenv(env_key)
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
        data = jwt.decode(token, SECRET_KEY, algorithms=[ALGO])
        return data["sub"]
    except JWTError:
        raise HTTPException(401, "Invalid or expired session")


def set_session_cookie(resp: Response, token: str):
    resp.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=True,      # required for cross-site cookies over HTTPS
        samesite="none",  # so GitHub Pages can send the cookie
        path="/",
        max_age=60 * 60,
    )


def require_auth(request: Request) -> str:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(401, "Not authenticated")
    return parse_token(token)

# ---------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------


@app.get("/")
def root():
    return {"ok": True, "service": "optimis-fiscale-api"}


@app.get("/health")
def health():
    return {"status": "ok"}

# ---------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------


@app.post("/analyze/trial-balance", response_model=AnalysisResult)
async def analyze_trial_balance_endpoint(
    file: UploadFile = File(...),
    turnover: float | None = None,
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            400,
            "Veuillez fournir un CSV (colonnes: account,label,debit,credit).",
        )
    try:
        import io
        df = pd.read_csv(io.BytesIO(await file.read()))
        df.columns = df.columns.str.strip().str.lower()
    except Exception:
        raise HTTPException(400, "CSV illisible")
    try:
        return analyze_trial_balance(df, turnover=turnover)
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post("/analyze/json", response_model=AnalysisResult)
async def analyze_json_endpoint(payload: dict):
    try:
        df = pd.DataFrame(payload["trial_balance"])
        df.columns = df.columns.str.strip().str.lower()
    except Exception:
        raise HTTPException(400, "JSON invalide")
    turnover = payload.get("turnover")
    return analyze_trial_balance(df, turnover=turnover)

# ---------------------------------------------------------------------
# Auth
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
    return {"ok": True, "company_id": body.company_id}


@app.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"ok": True}

# ---------------------------------------------------------------------
# Chat (OpenAI)
# ---------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]


class ChatResponse(BaseModel):
    reply: str


_last_call = defaultdict(float)


def throttle(company_id: str, min_interval: float = 2.0):
    now = time.time()
    if now - _last_call[company_id] < min_interval:
        raise HTTPException(
            429,
            "Trop de requêtes. Réessayez dans 2–3 secondes.",
        )
    _last_call[company_id] = now


async def call_openai_with_retry(
    json_payload,
    api_key: str,
    max_retries: int = 4,
) -> str:
    backoff = 1.5
    async with httpx.AsyncClient(timeout=40) as client:
        for attempt in range(1, max_retries + 1):
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
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

            raise HTTPException(
                502,
                f"OpenAI error {r.status_code}: {r.text[:200]}",
            )
        raise HTTPException(
            429,
            "OpenAI rate limit: réessayez plus tard.",
        )


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, company_id: str = Depends(require_auth)):
    if not OPENAI_API_KEY:
        raise HTTPException(500, "Server missing OPENAI_API_KEY")
    throttle(company_id, 2.0)
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": (
                    "Tu es Albert, un assistant fiscal pour les PME françaises. "
                    "Sois professionnel, clair et concis."
                ),
            },
            *[m.model_dump() for m in req.messages],
        ],
        "temperature": 0.2,
    }
    reply = await call_openai_with_retry(payload, OPENAI_API_KEY, 4)
    return ChatResponse(reply=reply)

# ---------------------------------------------------------------------
# Include your existing DB routers (bank / invoices / alerts)
# ---------------------------------------------------------------------
app.include_router(bank.router)
app.include_router(invoices.router)
app.include_router(alerts.router)

# ---------------------------------------------------------------------
# Audit
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
    standard = (standard or "IFRS").strip().upper()
    framework = "USGAAP" if standard.startswith("US") else "IFRS"

    if not file.filename.endswith(".csv"):
        raise HTTPException(
            400,
            "Veuillez fournir un CSV (colonnes: account,label,debit,credit).",
        )

    import io

    try:
        df = pd.read_csv(io.BytesIO(await file.read()))
        df.columns = df.columns.str.strip().str.lower()
    except Exception:
        raise HTTPException(400, "CSV illisible")

    required = {"account", "label", "debit", "credit"}
    if not required.issubset(df.columns):
        missing = sorted(list(required - set(df.columns)))
        raise HTTPException(
            400,
            f"Colonnes manquantes: {', '.join(missing)}",
        )

    for c in ["debit", "credit"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)

    total_debit = float(df["debit"].sum())
    total_credit = float(df["credit"].sum())
    imbalance = float(abs(total_debit - total_credit))

    issues: List[AuditIssue] = []
    if imbalance > 0.01:
        issues.append(
            AuditIssue(
                code="IMBALANCE",
                severity="error",
                message=f"Écart entre débits et crédits: {imbalance:,.2f} €",
            )
        )

    missing_labels = int(
        df["label"].isna().sum()
        + (df["label"].astype(str).str.strip() == "").sum()
    )
    if missing_labels > 0:
        issues.append(
            AuditIssue(
                code="MISSING_LABELS",
                severity="warning",
                message="Libellés manquants",
                count=missing_labels,
            )
        )

    neg_debit = int((df["debit"] < 0).sum())
    neg_credit = int((df["credit"] < 0).sum())
    if neg_debit > 0:
        issues.append(
            AuditIssue(
                code="NEG_DEBIT",
                severity="warning",
                message="Débits négatifs détectés",
                count=neg_debit,
            )
        )
    if neg_credit > 0:
        issues.append(
            AuditIssue(
                code="NEG_CREDIT",
                severity="warning",
                message="Crédits négatifs détectés",
                count=neg_credit,
            )
        )

    dups = df["account"].astype(str).str.strip().duplicated().sum()
    if dups > 0:
        issues.append(
            AuditIssue(
                code="DUP_ACCOUNTS",
                severity="info",
                message="Comptes apparaissant plusieurs fois",
                count=int(dups),
            )
        )

    issues.append(
        AuditIssue(
            code="FRAMEWORK",
            severity="info",
            message=f"Contrôles exécutés avec le référentiel {framework}.",
        )
    )

    df["balance"] = df["debit"] - df["credit"]
    grp = (
        df.groupby(["account", "label"], dropna=False)["balance"]
        .sum()
        .reset_index()
    )
    grp["abs_balance"] = grp["balance"].abs()
    top = grp.sort_values("abs_balance", ascending=False).head(10)
    top = (
        top.assign(
            account=top["account"].astype(str),
            label=top["label"].astype(str),
            balance=top["balance"].round(2),
            abs_balance=top["abs_balance"].round(2),
        )[["account", "label", "balance", "abs_balance"]]
        .to_dict(orient="records")
    )

    summary = AuditSummary(
        ok=(
            imbalance <= 0.01
            and missing_labels == 0
            and neg_debit == 0
            and neg_credit == 0
        ),
        total_rows=len(df),
        total_debit=round(total_debit, 2),
        total_credit=round(total_credit, 2),
        imbalance=round(imbalance, 2),
        framework=framework,
    )
    return AuditResult(summary=summary, issues=issues, top_accounts=top)
