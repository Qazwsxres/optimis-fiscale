# app/routers/employees.py
"""
Employee Management Router
Handles employee CRUD operations
"""

import os
from datetime import date
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import Optional

from ..database import SessionLocal, Base
from sqlalchemy import Column, Integer, String, Numeric, Date, TIMESTAMP, func

router = APIRouter(prefix="/employees", tags=["Employees"])

# Get CORS origin
FRONTEND_URL = os.getenv("ALLOWED_ORIGIN", "https://qazwsxres.github.io").split(",")[0]

def get_cors_headers():
    return {
        "Access-Control-Allow-Origin": FRONTEND_URL,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "*"
    }

# =====================================================
# DATABASE MODEL
# =====================================================

class Employee(Base):
    __tablename__ = "employees"
    
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True)
    position = Column(String(255))
    salary = Column(Numeric(12, 2))
    start_date = Column(Date)
    created_at = Column(TIMESTAMP, server_default=func.now())

# =====================================================
# PYDANTIC SCHEMAS
# =====================================================

class EmployeeCreate(BaseModel):
    firstName: str
    lastName: str
    email: EmailStr
    position: str
    salary: float
    startDate: date

class EmployeeResponse(BaseModel):
    id: int
    firstName: str
    lastName: str
    email: str
    position: str
    salary: float
    startDate: str
    
    class Config:
        from_attributes = True

# =====================================================
# ROUTES
# =====================================================

@router.post("/", status_code=201)
def create_employee(emp: EmployeeCreate):
    """Create a new employee"""
    try:
        with SessionLocal() as db:
            # Check if email already exists
            existing = db.query(Employee).filter(Employee.email == emp.email).first()
            if existing:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Email already exists"},
                    headers=get_cors_headers()
                )
            
            obj = Employee(
                first_name=emp.firstName,
                last_name=emp.lastName,
                email=emp.email,
                position=emp.position,
                salary=emp.salary,
                start_date=emp.startDate
            )
            
            db.add(obj)
            db.commit()
            db.refresh(obj)
            
            return JSONResponse(
                content={
                    "id": obj.id,
                    "firstName": obj.first_name,
                    "lastName": obj.last_name,
                    "email": obj.email,
                    "position": obj.position,
                    "salary": float(obj.salary or 0),
                    "startDate": str(obj.start_date)
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
def list_employees():
    """List all employees"""
    try:
        with SessionLocal() as db:
            items = db.query(Employee).order_by(Employee.last_name.asc()).all()
            
            data = [
                {
                    "id": e.id,
                    "firstName": e.first_name,
                    "lastName": e.last_name,
                    "email": e.email,
                    "position": e.position,
                    "salary": float(e.salary or 0),
                    "startDate": str(e.start_date)
                }
                for e in items
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

@router.get("/{employee_id}")
def get_employee(employee_id: int):
    """Get employee by ID"""
    try:
        with SessionLocal() as db:
            emp = db.query(Employee).filter(Employee.id == employee_id).first()
            
            if not emp:
                return JSONResponse(
                    status_code=404,
                    content={"error": "Employee not found"},
                    headers=get_cors_headers()
                )
            
            return JSONResponse(
                content={
                    "id": emp.id,
                    "firstName": emp.first_name,
                    "lastName": emp.last_name,
                    "email": emp.email,
                    "position": emp.position,
                    "salary": float(emp.salary or 0),
                    "startDate": str(emp.start_date)
                },
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )

@router.post("/{employee_id}/payslip")
def generate_payslip(employee_id: int):
    """Generate payslip for employee (placeholder)"""
    try:
        with SessionLocal() as db:
            emp = db.query(Employee).filter(Employee.id == employee_id).first()
            
            if not emp:
                return JSONResponse(
                    status_code=404,
                    content={"error": "Employee not found"},
                    headers=get_cors_headers()
                )
            
            # TODO: Implement actual PDF generation
            return JSONResponse(
                content={
                    "message": "Payslip generation in progress",
                    "employee_id": employee_id,
                    "employee_name": f"{emp.first_name} {emp.last_name}",
                    "url": None  # Will contain PDF URL when implemented
                },
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )

@router.put("/{employee_id}")
def update_employee(employee_id: int, emp: EmployeeCreate):
    """Update employee"""
    try:
        with SessionLocal() as db:
            existing = db.query(Employee).filter(Employee.id == employee_id).first()
            
            if not existing:
                return JSONResponse(
                    status_code=404,
                    content={"error": "Employee not found"},
                    headers=get_cors_headers()
                )
            
            existing.first_name = emp.firstName
            existing.last_name = emp.lastName
            existing.email = emp.email
            existing.position = emp.position
            existing.salary = emp.salary
            existing.start_date = emp.startDate
            
            db.commit()
            db.refresh(existing)
            
            return JSONResponse(
                content={
                    "id": existing.id,
                    "firstName": existing.first_name,
                    "lastName": existing.last_name,
                    "email": existing.email,
                    "position": existing.position,
                    "salary": float(existing.salary or 0),
                    "startDate": str(existing.start_date)
                },
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )

@router.delete("/{employee_id}")
def delete_employee(employee_id: int):
    """Delete employee"""
    try:
        with SessionLocal() as db:
            emp = db.query(Employee).filter(Employee.id == employee_id).first()
            
            if not emp:
                return JSONResponse(
                    status_code=404,
                    content={"error": "Employee not found"},
                    headers=get_cors_headers()
                )
            
            db.delete(emp)
            db.commit()
            
            return JSONResponse(
                content={"message": "Employee deleted"},
                status_code=204,
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )
