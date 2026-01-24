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

# Import ALL routers (11 core + 7 banking = 18 total)
from .routers import (
    # Core routers (11)
    bank,
    invoices,
    alerts,
    cashflow,
    overdue,
    employees,
    tasks,
    pointages,
    users,
    email_import,
    finance,
    
    # Banking routers v2.0 (7)
    accounts,
    router_sync as sync,
    categories,
    budgets,
    analytics,
    webhooks,
    exports
)

# Import banking models
from .models_banking import (
    BankAccount,
    BankTransactionEnhanced,
    Category,
    Budget,
    SyncLog,
    RecurringTransaction,
    FinancialGoal,
    WebhookEvent
)

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
app = FastAPI(
    title="NUMMA API v2.0",
    description="API complète pour gestion PME avec intégration Bankin/Finary",
    version="2.0.0"
)

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
        "https://gestion-227fe8d8.base44.app",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600
)

# =====================================================
# DATABASE SETUP
# =====================================================
@app.on_event("startup")
def create_tables():
    """Create all database tables on startup"""
    print("🚀 Initializing NUMMA Backend v2.0...")
    
    try:
        from sqlalchemy import inspect
        inspector = inspect(engine)
        
        # Check if invoices_sales table exists and has old schema
        if 'invoices_sales' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('invoices_sales')]
            
            if 'client_name' not in columns or 'amount_ttc' not in columns:
                print("⚠️  Old schema detected! Resetting database...")
                Base.metadata.drop_all(bind=engine)
                print("🗑️  Old tables dropped")
        
        # Import router models
        try:
            from .routers.employees import Employee
            from .routers.tasks import Task
            from .routers.pointages import Pointage
            from .routers.users import User
            print("✅ Router models imported")
        except ImportError as e:
            print(f"⚠️  Could not import some models: {e}")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created")
        
        # Print summary
        print("\n📊 Database Models:")
        print("  ✅ Core models (7): DailyCashflow, Client, Supplier, InvoiceSale, InvoicePurchase, BankTransaction, Alert")
        print("  ✅ Router models (4): Employee, Task, Pointage, User")
        print("  ✅ Banking models (8): BankAccount, BankTransactionEnhanced, Category, Budget, SyncLog, RecurringTransaction, FinancialGoal, WebhookEvent")
        
    except Exception as e:
        print(f"⚠️  Database error: {e}")
        Base.metadata.create_all(bind=engine)

# =====================================================
# CORS HEADERS HELPER
# =====================================================
def get_cors_headers():
    """Standard CORS headers for all responses"""
    origin = ALLOWED_ORIGINS[0] if ALLOWED_ORIGINS else "*"
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
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
        secure=True,
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
            "service": "numma-api",
            "version": "2.0.0",
            "https": "enforced",
            "banking_integration": True,
            "total_routers": 18
        },
        headers=get_cors_headers()
    )


@app.get("/health")
def health():
    return JSONResponse(
        content={
            "status": "ok",
            "version": "2.0.0",
            "routers": 18,
            "banking": True
        },
        headers=get_cors_headers()
    )


# =====================================================
# DATABASE RESET ENDPOINT (TEMPORARY)
# =====================================================
@app.post("/admin/reset-database")
def reset_database(secret_key: str):
    """⚠️ DANGER: Drops and recreates all database tables"""
    expected_secret = os.getenv("SECRET_KEY", "")
    
    if secret_key != expected_secret:
        raise HTTPException(403, "Invalid secret key")
    
    try:
        print("🗑️  Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        
        print("🔨 Creating new tables...")
        Base.metadata.create_all(bind=engine)
        
        print("✅ Database reset complete!")
        
        return JSONResponse(
            content={
                "success": True,
                "message": "Database reset successfully"
            },
            headers=get_cors_headers()
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)},
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


# =====================================================
# INCLUDE ALL 18 ROUTERS
# =====================================================

# Core routers (11)
app.include_router(bank.router)
app.include_router(invoices.router)
app.include_router(alerts.router)
app.include_router(cashflow.router)
app.include_router(overdue.router)
app.include_router(employees.router)
app.include_router(tasks.router)
app.include_router(pointages.router)
app.include_router(users.router)
app.include_router(email_import.router)
app.include_router(finance.router)

print("\n📦 Core routers loaded (11):")
print("  ✅ bank, invoices, alerts, cashflow, overdue")
print("  ✅ employees, tasks, pointages, users")
print("  ✅ email_import, finance")

# Banking routers v2.0 (7)
app.include_router(accounts.router)
app.include_router(sync.router)
app.include_router(categories.router)
app.include_router(budgets.router)
app.include_router(analytics.router)
app.include_router(webhooks.router)
app.include_router(exports.router)

print("\n🆕 Banking routers v2.0 loaded (7):")
print("  ✅ accounts, sync, categories, budgets")
print("  ✅ analytics, webhooks, exports")
print("\n🎉 TOTAL: 18 routers loaded!")


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
# API DOCUMENTATION
# =====================================================
@app.get("/api/routes")
def list_routes():
    """List all available API routes"""
    routes = []
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": route.name
            })
    
    return JSONResponse(
        content={
            "total_routes": len(routes),
            "routes": sorted(routes, key=lambda x: x["path"]),
            "banking_integration": True
        },
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


# =====================================================
# STARTUP MESSAGE
# =====================================================
@app.on_event("startup")
async def startup_message():
    print("\n" + "="*70)
    print("🚀 NUMMA Backend API v2.0 - Ready!")
    print("="*70)
    print(f"📡 Environment: {'Production' if os.getenv('RAILWAY_ENVIRONMENT') else 'Development'}")
    print(f"🔗 CORS: {', '.join(ALLOWED_ORIGINS[:2])}...")
    print(f"🔐 HTTPS: Enforced")
    print(f"💾 Database: PostgreSQL")
    print(f"🤖 OpenAI: {'Enabled' if OPENAI_API_KEY else 'Disabled'}")
    print(f"🏦 Banking: ✅ Enabled")
    
    print("\n📋 Core Modules (11):")
    print("  ✅ Authentication & Security")
    print("  ✅ Bank Transactions")
    print("  ✅ Invoices (Sales/Purchases)")
    print("  ✅ Cashflow Management")
    print("  ✅ Alerts & Notifications")
    print("  ✅ Overdue Tracking")
    print("  ✅ Employees & HR")
    print("  ✅ Tasks Management")
    print("  ✅ Time Tracking (Pointages)")
    print("  ✅ User Management")
    print("  ✅ Email Import")
    print("  ✅ Finance Routes")
    print("  ✅ AI Chat (Albert)")
    
    print("\n🆕 Banking Integration v2.0 (7):")
    print("  ✅ Multi-Bank Accounts")
    print("  ✅ Sync (Bankin/Finary/Bridge)")
    print("  ✅ Auto-Categorization")
    print("  ✅ Smart Budgets")
    print("  ✅ Advanced Analytics")
    print("  ✅ Real-time Webhooks")
    print("  ✅ Accounting Exports (FEC)")
    
    print(f"\n📊 Total Routers: 18")
    print(f"📍 Total Endpoints: ~140")
    print(f"🗄️  Total Models: 19")
    print("\n🌐 API Documentation: /docs")
    print("💚 Health Check: /health")
    print("📚 Routes List: /api/routes")
    print("="*70 + "\n")
