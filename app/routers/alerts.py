import os
from datetime import date
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..database import SessionLocal
from ..models_extended import Alert

router = APIRouter(prefix="/alerts", tags=["Alerts"])

# Get CORS origin from environment
FRONTEND_URL = os.getenv("ALLOWED_ORIGIN", "https://qazwsxres.github.io").split(",")[0]

def get_cors_headers():
    """Standard CORS headers for all responses"""
    return {
        "Access-Control-Allow-Origin": FRONTEND_URL,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "*"
    }


# --------------------------
# Request Model
# --------------------------
class AlertIn(BaseModel):
    message: str
    due_date: date


# --------------------------
# GET /alerts
# --------------------------
@router.get("/")
def list_alerts():
    try:
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
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


# --------------------------
# POST /alerts
# --------------------------
@router.post("/")
def create_alert(alert: AlertIn):
    try:
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
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )
