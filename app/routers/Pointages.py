# app/routers/pointages.py
"""
Time Tracking (Pointage) Router
"""

import os
from datetime import date
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from ..database import SessionLocal, Base
from sqlalchemy import Column, Integer, String, Date, TIMESTAMP, func

router = APIRouter(prefix="/pointages", tags=["Pointages"])

FRONTEND_URL = os.getenv("ALLOWED_ORIGIN", "https://qazwsxres.github.io").split(",")[0]

def get_cors_headers():
    return {
        "Access-Control-Allow-Origin": FRONTEND_URL,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "*"
    }

# =====================================================
# MODEL
# =====================================================

class Pointage(Base):
    __tablename__ = "pointages"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    clock_in = Column(String(10), nullable=False)  # HH:MM format
    clock_out = Column(String(10))  # HH:MM format
    employee = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

# =====================================================
# SCHEMAS
# =====================================================

class PointageCreate(BaseModel):
    date: date
    clockIn: str
    employee: str
    clockOut: Optional[str] = None

# =====================================================
# ROUTES
# =====================================================

@router.post("/", status_code=201)
def create_pointage(pointage: PointageCreate):
    try:
        with SessionLocal() as db:
            obj = Pointage(
                date=pointage.date,
                clock_in=pointage.clockIn,
                clock_out=pointage.clockOut,
                employee=pointage.employee
            )
            
            db.add(obj)
            db.commit()
            db.refresh(obj)
            
            return JSONResponse(
                content={
                    "id": obj.id,
                    "date": str(obj.date),
                    "clockIn": obj.clock_in,
                    "clockOut": obj.clock_out,
                    "employee": obj.employee
                },
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )

@router.get("/")
def list_pointages(
    date: Optional[date] = None,
    employee: Optional[str] = None
):
    try:
        with SessionLocal() as db:
            query = db.query(Pointage)
            
            if date:
                query = query.filter(Pointage.date == date)
            if employee:
                query = query.filter(Pointage.employee == employee)
            
            items = query.order_by(Pointage.date.desc()).all()
            
            data = [
                {
                    "id": p.id,
                    "date": str(p.date),
                    "clockIn": p.clock_in,
                    "clockOut": p.clock_out,
                    "employee": p.employee
                }
                for p in items
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

@router.patch("/{pointage_id}/clock-out")
def clock_out(pointage_id: int, clock_out: str):
    try:
        with SessionLocal() as db:
            pointage = db.query(Pointage).filter(Pointage.id == pointage_id).first()
            
            if not pointage:
                return JSONResponse(
                    status_code=404,
                    content={"error": "Pointage not found"},
                    headers=get_cors_headers()
                )
            
            pointage.clock_out = clock_out
            db.commit()
            
            return JSONResponse(
                content={"id": pointage_id, "clockOut": clock_out},
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )
