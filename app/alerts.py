from fastapi import APIRouter
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models_extended import Alert
from datetime import date

router = APIRouter(prefix="/alerts", tags=["Alerts"])

@router.get("/")
def list_alerts():
    with SessionLocal() as db:
        return db.query(Alert).all()

@router.post("/")
def create_alert(msg: str, due: date):
    with SessionLocal() as db:
        a = Alert(message=msg, due_date=due, type="fiscal")
        db.add(a)
        db.commit()
        db.refresh(a)
    return a
