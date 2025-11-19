from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import date
from ..database import SessionLocal
from ..models_extended import Alert

router = APIRouter(prefix="/alerts", tags=["Alerts"])

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://qazwsxres.github.io",
    "Access-Control-Allow-Credentials": "true",
    "Access-Control-Allow-Methods": "*",
    "Access-Control-Allow-Headers": "*",
    "Content-Type": "application/json",
    "Access-Control-Max-Age": "3600",
}

# --------------------------
# Request Model
# --------------------------
class AlertIn(BaseModel):
    message: str
    due_date: date


# --------------------------
# CORS Preflight (ALL ROUTES)
# --------------------------
@router.options("/{path:path}")
def alerts_preflight(path: str):
    return JSONResponse(
        content={"ok": True},
        status_code=200,
        headers=CORS_HEADERS
    )


# --------------------------
# GET /alerts
# --------------------------
@router.get("/")
def list_alerts():
    with SessionLocal() as db:
        items = db.query(Alert).order_by(Alert.due_date.asc()).all()

        data = [
            {
                "id": a.id,
                "message": a.message,
                "due_date": str(a.due_date),
                "type": a.type,
            }
            for a in items
        ]

        return JSONResponse(
            content=data,
            headers=CORS_HEADERS
        )


# --------------------------
# POST /alerts
# --------------------------
@router.post("/")
def create_alert(alert: AlertIn):
    with SessionLocal() as db:
        a = Alert(
            message=alert.message,
            due_date=alert.due_date,
            type="fiscal"
        )
        db.add(a)
        db.commit()
        db.refresh(a)

        return JSONResponse(
            content={
                "id": a.id,
                "message": a.message,
                "due_date": str(a.due_date),
                "type": a.type,
            },
            headers=CORS_HEADERS
        )
