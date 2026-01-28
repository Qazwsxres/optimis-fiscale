"""
COMPLETE pointages.py - COPY THIS ENTIRE FILE
Replace your app/routers/pointages.py with this
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
from datetime import datetime, date
from pydantic import BaseModel

from app.database import get_db
from app.models_extended import Pointage

router = APIRouter(prefix="/api/pointages", tags=["pointages"])


# ============================================================
# PYDANTIC SCHEMAS
# ============================================================

class PointageCreate(BaseModel):
    employee_name: str
    clock_in_time: Optional[str] = None
    notes: Optional[str] = None


class PointageResponse(BaseModel):
    id: int
    employee_name: str
    clock_in_time: str
    clock_out_time: Optional[str]
    total_hours: Optional[float]
    date: str

    class Config:
        from_attributes = True


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/", response_model=List[PointageResponse])
async def get_pointages(
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    employee: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get pointages with filtering"""
    try:
        query = db.query(Pointage)
        
        if date_from:
            query = query.filter(func.date(Pointage.clock_in) >= date_from)
        
        if date_to:
            query = query.filter(func.date(Pointage.clock_in) <= date_to)
        
        if employee:
            query = query.filter(Pointage.employee.ilike(f"%{employee}%"))
        
        query = query.order_by(Pointage.clock_in.desc())
        pointages = query.all()
        
        return [
            PointageResponse(
                id=p.id,
                employee_name=p.employee,
                clock_in_time=p.clock_in.isoformat() if p.clock_in else None,
                clock_out_time=p.clock_out.isoformat() if p.clock_out else None,
                total_hours=float(p.total_hours) if p.total_hours else None,
                date=p.clock_in.date().isoformat() if p.clock_in else None
            )
            for p in pointages
        ]
        
    except Exception as e:
        print(f"❌ Error in get_pointages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_pointage_stats(
    date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get pointage statistics"""
    try:
        target_date = date if date else datetime.now().date().isoformat()
        
        query = db.query(Pointage).filter(
            func.date(Pointage.clock_in) == target_date
        )
        
        all_pointages = query.all()
        present = len([p for p in all_pointages if p.clock_out is None])
        total = len(all_pointages)
        
        return {
            "present": present,
            "absent": 0,
            "late": 0,
            "total": total,
            "date": target_date
        }
        
    except Exception as e:
        print(f"❌ Error in get_pointage_stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clock-in", status_code=status.HTTP_201_CREATED)
async def clock_in(
    data: PointageCreate,
    db: Session = Depends(get_db)
):
    """Clock in an employee"""
    try:
        clock_in_time = datetime.fromisoformat(data.clock_in_time) if data.clock_in_time else datetime.now()
        
        new_pointage = Pointage(
            employee=data.employee_name,
            clock_in=clock_in_time,
            notes=data.notes
        )
        
        db.add(new_pointage)
        db.commit()
        db.refresh(new_pointage)
        
        print(f"✅ Clock in: {data.employee_name} at {clock_in_time}")
        
        return {
            "id": new_pointage.id,
            "employee_name": new_pointage.employee,
            "clock_in_time": new_pointage.clock_in.isoformat(),
            "message": "Clocked in successfully"
        }
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error in clock_in: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def pointages_health():
    """Health check"""
    return {
        "status": "ok",
        "router": "pointages",
        "message": "Pointages router with query parameter support"
    }


print("✅ Pointages router loaded with GET endpoints")
