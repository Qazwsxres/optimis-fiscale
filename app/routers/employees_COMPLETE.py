"""
Employees Router - COMPLET AVEC GET ENDPOINT
Remplacer app/routers/employees.py par ce fichier
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import date
from typing import Optional
from sqlalchemy import Column, Integer, String, Date, Float
import os

router = APIRouter(prefix="/api/employees", tags=["Employees"])

from ..database import SessionLocal, engine, Base

FRONTEND_URL = os.getenv("ALLOWED_ORIGIN", "https://qazwsxres.github.io").split(",")[0]

def get_cors_headers():
    return {
        "Access-Control-Allow-Origin": FRONTEND_URL,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "*"
    }

# ============================================
# MODEL
# ============================================
class Employee(Base):
    __tablename__ = "employees"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    position = Column(String)
    email = Column(String)
    phone = Column(String)
    hire_date = Column(Date)
    salary = Column(Float)

Base.metadata.create_all(bind=engine)

# ============================================
# PYDANTIC MODELS
# ============================================
class EmployeeCreate(BaseModel):
    name: str
    position: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    hire_date: Optional[date] = None
    salary: Optional[float] = None

class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    position: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    salary: Optional[float] = None

# ============================================
# 🆕 GET EMPLOYEES (NOUVEAU)
# ============================================
@router.get("/")
def get_employees():
    """
    Liste tous les employés
    """
    try:
        with SessionLocal() as db:
            employees = db.query(Employee).order_by(Employee.name).all()
            
            return JSONResponse(
                content=[{
                    "id": e.id,
                    "name": e.name,
                    "position": e.position or "",
                    "email": e.email or "",
                    "phone": e.phone or "",
                    "hire_date": e.hire_date.isoformat() if e.hire_date else None,
                    "salary": float(e.salary) if e.salary else 0
                } for e in employees],
                headers=get_cors_headers()
            )
    except Exception as e:
        print(f"❌ Error in get_employees: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )


# ============================================
# GET EMPLOYEE BY ID
# ============================================
@router.get("/{employee_id}")
def get_employee(employee_id: int):
    """Détails d'un employé"""
    try:
        with SessionLocal() as db:
            employee = db.query(Employee).filter(Employee.id == employee_id).first()
            
            if not employee:
                raise HTTPException(404, "Employee not found")
            
            return JSONResponse(
                content={
                    "id": employee.id,
                    "name": employee.name,
                    "position": employee.position,
                    "email": employee.email,
                    "phone": employee.phone,
                    "hire_date": employee.hire_date.isoformat() if employee.hire_date else None,
                    "salary": float(employee.salary) if employee.salary else None
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


# ============================================
# POST - CREATE EMPLOYEE
# ============================================
@router.post("/")
def create_employee(employee: EmployeeCreate):
    """Créer un nouvel employé"""
    try:
        with SessionLocal() as db:
            new_employee = Employee(
                name=employee.name,
                position=employee.position,
                email=employee.email,
                phone=employee.phone,
                hire_date=employee.hire_date,
                salary=employee.salary
            )
            db.add(new_employee)
            db.commit()
            db.refresh(new_employee)
            
            return JSONResponse(
                content={
                    "id": new_employee.id,
                    "name": new_employee.name,
                    "message": "Employé créé"
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
# PUT - UPDATE EMPLOYEE
# ============================================
@router.put("/{employee_id}")
def update_employee(employee_id: int, employee: EmployeeUpdate):
    """Modifier un employé"""
    try:
        with SessionLocal() as db:
            emp = db.query(Employee).filter(Employee.id == employee_id).first()
            
            if not emp:
                raise HTTPException(404, "Employee not found")
            
            if employee.name is not None:
                emp.name = employee.name
            if employee.position is not None:
                emp.position = employee.position
            if employee.email is not None:
                emp.email = employee.email
            if employee.phone is not None:
                emp.phone = employee.phone
            if employee.salary is not None:
                emp.salary = employee.salary
            
            db.commit()
            db.refresh(emp)
            
            return JSONResponse(
                content={
                    "id": emp.id,
                    "message": "Employé modifié"
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


# ============================================
# DELETE EMPLOYEE
# ============================================
@router.delete("/{employee_id}")
def delete_employee(employee_id: int):
    """Supprimer un employé"""
    try:
        with SessionLocal() as db:
            employee = db.query(Employee).filter(Employee.id == employee_id).first()
            
            if not employee:
                raise HTTPException(404, "Employee not found")
            
            db.delete(employee)
            db.commit()
            
            return JSONResponse(
                content={"message": "Employé supprimé"},
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


# ============================================
# POST PAYSLIP (Fiche de paie)
# ============================================
@router.post("/{employee_id}/payslip")
def generate_payslip(employee_id: int):
    """Générer fiche de paie (simplifié)"""
    try:
        with SessionLocal() as db:
            employee = db.query(Employee).filter(Employee.id == employee_id).first()
            
            if not employee:
                raise HTTPException(404, "Employee not found")
            
            # Calculs simplifiés
            gross_salary = float(employee.salary or 0)
            social_charges = gross_salary * 0.22  # 22% charges sociales
            net_salary = gross_salary - social_charges
            
            return JSONResponse(
                content={
                    "employee_id": employee.id,
                    "employee_name": employee.name,
                    "gross_salary": round(gross_salary, 2),
                    "social_charges": round(social_charges, 2),
                    "net_salary": round(net_salary, 2),
                    "message": "Fiche de paie générée"
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


print("✅ Employees router loaded with GET endpoint")
