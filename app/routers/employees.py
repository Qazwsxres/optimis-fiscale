"""
COMPLETE employees.py - COPY THIS ENTIRE FILE
Replace your app/routers/employees.py with this
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.models_extended import Employee

router = APIRouter(prefix="/api/employees", tags=["employees"])


# ============================================================
# PYDANTIC SCHEMAS
# ============================================================

class EmployeeCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    position: Optional[str] = None
    contract_type: str = "CDI"
    gross_salary: float
    start_date: Optional[str] = None


class EmployeeResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    position: Optional[str]
    contract_type: str
    gross_salary: float
    start_date: Optional[str]
    status: str

    class Config:
        from_attributes = True


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/", response_model=List[EmployeeResponse])
async def get_employees(
    status: Optional[str] = Query(None),
    contract_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all employees with filtering"""
    try:
        query = db.query(Employee)
        
        if status:
            query = query.filter(Employee.status == status)
        
        if contract_type:
            query = query.filter(Employee.contract_type == contract_type)
        
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Employee.first_name.ilike(search_pattern),
                    Employee.last_name.ilike(search_pattern),
                    Employee.email.ilike(search_pattern)
                )
            )
        
        query = query.order_by(Employee.last_name, Employee.first_name)
        employees = query.all()
        
        return [
            EmployeeResponse(
                id=emp.id,
                first_name=emp.first_name,
                last_name=emp.last_name,
                email=emp.email,
                position=emp.position,
                contract_type=emp.contract_type,
                gross_salary=float(emp.gross_salary),
                start_date=emp.start_date.isoformat() if emp.start_date else None,
                status=emp.status
            )
            for emp in employees
        ]
        
    except Exception as e:
        print(f"❌ Error in get_employees: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific employee"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return EmployeeResponse(
        id=employee.id,
        first_name=employee.first_name,
        last_name=employee.last_name,
        email=employee.email,
        position=employee.position,
        contract_type=employee.contract_type,
        gross_salary=float(employee.gross_salary),
        start_date=employee.start_date.isoformat() if employee.start_date else None,
        status=employee.status
    )


@router.post("/", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
async def create_employee(
    employee_data: EmployeeCreate,
    db: Session = Depends(get_db)
):
    """Create a new employee"""
    try:
        # Check if email exists
        existing = db.query(Employee).filter(Employee.email == employee_data.email).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")
        
        start_date = datetime.fromisoformat(employee_data.start_date).date() if employee_data.start_date else datetime.now().date()
        
        new_employee = Employee(
            first_name=employee_data.first_name,
            last_name=employee_data.last_name,
            email=employee_data.email,
            position=employee_data.position,
            contract_type=employee_data.contract_type,
            gross_salary=employee_data.gross_salary,
            start_date=start_date,
            status="active"
        )
        
        db.add(new_employee)
        db.commit()
        db.refresh(new_employee)
        
        print(f"✅ Employee created: {new_employee.first_name} {new_employee.last_name}")
        
        return EmployeeResponse(
            id=new_employee.id,
            first_name=new_employee.first_name,
            last_name=new_employee.last_name,
            email=new_employee.email,
            position=new_employee.position,
            contract_type=new_employee.contract_type,
            gross_salary=float(new_employee.gross_salary),
            start_date=new_employee.start_date.isoformat(),
            status="active"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating employee: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def employees_health():
    """Health check"""
    return {
        "status": "ok",
        "router": "employees",
        "message": "Employees router with query parameter support"
    }


print("✅ Employees router loaded with GET endpoint")
