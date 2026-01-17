# app/routers/tasks.py
"""
Task Management Router
"""

import os
from datetime import date
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from ..database import SessionLocal, Base
from sqlalchemy import Column, Integer, String, Date, Text, TIMESTAMP, func

router = APIRouter(prefix="/tasks", tags=["Tasks"])

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

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    due_date = Column(Date, nullable=False)
    priority = Column(String(50), default="medium")  # low, medium, high
    status = Column(String(50), default="in-progress")  # in-progress, completed, overdue
    assigned_to = Column(String(255))
    created_at = Column(TIMESTAMP, server_default=func.now())

# =====================================================
# SCHEMAS
# =====================================================

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    dueDate: date
    priority: str = "medium"
    status: str = "in-progress"
    assignedTo: Optional[str] = None

# =====================================================
# ROUTES
# =====================================================

@router.post("/", status_code=201)
def create_task(task: TaskCreate):
    try:
        with SessionLocal() as db:
            obj = Task(
                title=task.title,
                description=task.description,
                due_date=task.dueDate,
                priority=task.priority,
                status=task.status,
                assigned_to=task.assignedTo
            )
            
            db.add(obj)
            db.commit()
            db.refresh(obj)
            
            return JSONResponse(
                content={
                    "id": obj.id,
                    "title": obj.title,
                    "description": obj.description,
                    "dueDate": str(obj.due_date),
                    "priority": obj.priority,
                    "status": obj.status,
                    "assignedTo": obj.assigned_to
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
def list_tasks(status: Optional[str] = None, priority: Optional[str] = None):
    try:
        with SessionLocal() as db:
            query = db.query(Task)
            
            if status:
                query = query.filter(Task.status == status)
            if priority:
                query = query.filter(Task.priority == priority)
            
            items = query.order_by(Task.due_date.asc()).all()
            
            data = [
                {
                    "id": t.id,
                    "title": t.title,
                    "description": t.description,
                    "dueDate": str(t.due_date),
                    "priority": t.priority,
                    "status": t.status,
                    "assignedTo": t.assigned_to
                }
                for t in items
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

@router.patch("/{task_id}")
def update_task_status(task_id: int, status: str):
    try:
        with SessionLocal() as db:
            task = db.query(Task).filter(Task.id == task_id).first()
            
            if not task:
                return JSONResponse(
                    status_code=404,
                    content={"error": "Task not found"},
                    headers=get_cors_headers()
                )
            
            task.status = status
            db.commit()
            
            return JSONResponse(
                content={"id": task_id, "status": status},
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )
