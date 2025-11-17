from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models_extended import Alert
from datetime import date

router = APIRouter(prefix="/alerts", tags=["Alerts"])

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "https://qazwsxres.github.io",
    "Access-Control-Allow-Credentials": "true",
}


@router.get("/")
def list_alerts():
    with SessionLocal() as db:
        items = db.query(Alert).all()
        # Convert SQLAlchemy objects → dict to avoid serialization errors
        data = [
            {
                "id": a.id,
                "message": a.message,
                "due_date": str(a.due_date),
                "type": a.type
            }
            for a in items
        ]
        return JSONResponse(content=data, headers=CORS_HEADERS)


@router.post("/")
def create_alert(msg: str, due: date):
    with SessionLocal() as db:
        a = Alert(message=msg, due_date=due, type="fiscal")
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
