"""
Pointages Router - COMPLET AVEC GET ENDPOINTS
Copier ce fichier pour remplacer app/routers/pointages.py
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, DateTime, Float, func
import os

router = APIRouter(prefix="/api/pointages", tags=["Pointages"])

from ..database import SessionLocal, engine, Base

FRONTEND_URL = os.getenv("ALLOWED_ORIGIN", "https://qazwsxres.github.io").split(",")[0]

def get_cors_headers():
    return {
        "Access-Control-Allow-Origin": FRONTEND_URL,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
        "Access-Control-Allow-Headers": "*"
    }

# ============================================
# MODEL
# ============================================
class Pointage(Base):
    __tablename__ = "pointages"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer)
    clock_in = Column(DateTime)
    clock_out = Column(DateTime, nullable=True)
    break_duration = Column(Integer, default=0)
    total_hours = Column(Float, nullable=True)
    notes = Column(String, nullable=True)

Base.metadata.create_all(bind=engine)

# ============================================
# PYDANTIC MODELS
# ============================================
class PointageCreate(BaseModel):
    employee_id: int
    notes: Optional[str] = None

class PointageClockOut(BaseModel):
    break_duration: Optional[int] = 0
    notes: Optional[str] = None

# ============================================
# 🆕 GET POINTAGES (NOUVEAU)
# ============================================
@router.get("/")
def get_pointages(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """
    Liste des pointages avec filtres date
    
    Query Parameters:
    - date_from: Date de début (YYYY-MM-DD)
    - date_to: Date de fin (YYYY-MM-DD)
    """
    try:
        with SessionLocal() as db:
            query = db.query(Pointage)
            
            # Filtrer par date
            if date_from:
                try:
                    date_from_obj = datetime.fromisoformat(date_from)
                    query = query.filter(Pointage.clock_in >= date_from_obj)
                except ValueError:
                    pass
            
            if date_to:
                try:
                    date_to_obj = datetime.fromisoformat(date_to)
                    query = query.filter(Pointage.clock_in <= date_to_obj)
                except ValueError:
                    pass
            
            pointages = query.order_by(Pointage.clock_in.desc()).all()
            
            return JSONResponse(
                content=[{
                    "id": p.id,
                    "employee_id": p.employee_id,
                    "clock_in": p.clock_in.isoformat() if p.clock_in else None,
                    "clock_out": p.clock_out.isoformat() if p.clock_out else None,
                    "break_duration": p.break_duration or 0,
                    "total_hours": float(p.total_hours) if p.total_hours else 0,
                    "notes": p.notes or "",
                    "status": "completed" if p.clock_out else "in_progress"
                } for p in pointages],
                headers=get_cors_headers()
            )
    except Exception as e:
        print(f"❌ Error in get_pointages: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


# ============================================
# 🆕 GET STATS (NOUVEAU)
# ============================================
@router.get("/stats")
def get_pointage_stats(date: Optional[str] = None):
    """
    Statistiques pointages pour une date
    
    Query Parameters:
    - date: Date cible (YYYY-MM-DD), défaut = aujourd'hui
    """
    try:
        from datetime import date as dt_date
        
        # Parse date ou utiliser aujourd'hui
        if date:
            try:
                target_date = datetime.fromisoformat(date).date()
            except ValueError:
                target_date = dt_date.today()
        else:
            target_date = dt_date.today()
        
        with SessionLocal() as db:
            # Pointages du jour
            pointages = db.query(Pointage).filter(
                func.date(Pointage.clock_in) == target_date
            ).all()
            
            # Calculs
            total_hours = sum(float(p.total_hours or 0) for p in pointages)
            total_breaks = sum(p.break_duration or 0 for p in pointages)
            active = sum(1 for p in pointages if p.clock_out is None)
            completed = sum(1 for p in pointages if p.clock_out is not None)
            
            return JSONResponse(
                content={
                    "date": target_date.isoformat(),
                    "total_pointages": len(pointages),
                    "active": active,
                    "completed": completed,
                    "total_hours": round(total_hours, 2),
                    "total_breaks": total_breaks,
                    "average_hours": round(total_hours / len(pointages), 2) if pointages else 0
                },
                headers=get_cors_headers()
            )
    except Exception as e:
        print(f"❌ Error in get_pointage_stats: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


# ============================================
# POST - CREATE POINTAGE (Clock In)
# ============================================
@router.post("/")
def create_pointage(pointage: PointageCreate):
    """Créer un nouveau pointage (Clock In)"""
    try:
        with SessionLocal() as db:
            new_pointage = Pointage(
                employee_id=pointage.employee_id,
                clock_in=datetime.now(),
                notes=pointage.notes
            )
            db.add(new_pointage)
            db.commit()
            db.refresh(new_pointage)
            
            return JSONResponse(
                content={
                    "id": new_pointage.id,
                    "employee_id": new_pointage.employee_id,
                    "clock_in": new_pointage.clock_in.isoformat(),
                    "message": "Pointage créé"
                },
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


# ============================================
# PATCH - CLOCK OUT
# ============================================
@router.patch("/{pointage_id}/clock-out")
def clock_out(pointage_id: int, data: PointageClockOut):
    """Terminer un pointage (Clock Out)"""
    try:
        with SessionLocal() as db:
            pointage = db.query(Pointage).filter(Pointage.id == pointage_id).first()
            
            if not pointage:
                raise HTTPException(404, "Pointage not found")
            
            pointage.clock_out = datetime.now()
            pointage.break_duration = data.break_duration or 0
            
            # Calculate total hours
            if pointage.clock_in and pointage.clock_out:
                duration = pointage.clock_out - pointage.clock_in
                hours = duration.total_seconds() / 3600
                hours -= (pointage.break_duration or 0) / 60
                pointage.total_hours = max(0, hours)
            
            if data.notes:
                pointage.notes = data.notes
            
            db.commit()
            db.refresh(pointage)
            
            return JSONResponse(
                content={
                    "id": pointage.id,
                    "total_hours": pointage.total_hours,
                    "message": "Pointage clôturé"
                },
                headers=get_cors_headers()
            )
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


print("✅ Pointages router loaded with GET endpoints")
