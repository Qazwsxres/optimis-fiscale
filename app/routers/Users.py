# app/routers/users.py
"""
User Management Router
"""

import os
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr

from ..database import SessionLocal, Base
from sqlalchemy import Column, Integer, String, TIMESTAMP, func

router = APIRouter(prefix="/users", tags=["Users"])

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

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    role = Column(String(50), default="user")  # admin, user, viewer
    status = Column(String(50), default="invited")  # invited, active, suspended
    created_at = Column(TIMESTAMP, server_default=func.now())

# =====================================================
# SCHEMAS
# =====================================================

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    role: str = "user"
    status: str = "invited"

# =====================================================
# ROUTES
# =====================================================

@router.post("/", status_code=201)
def create_user(user: UserCreate):
    try:
        with SessionLocal() as db:
            # Check if email exists
            existing = db.query(User).filter(User.email == user.email).first()
            if existing:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Email already exists"},
                    headers=get_cors_headers()
                )
            
            obj = User(
                name=user.name,
                email=user.email,
                role=user.role,
                status=user.status
            )
            
            db.add(obj)
            db.commit()
            db.refresh(obj)
            
            # TODO: Send invitation email
            
            return JSONResponse(
                content={
                    "id": obj.id,
                    "name": obj.name,
                    "email": obj.email,
                    "role": obj.role,
                    "status": obj.status
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
def list_users():
    try:
        with SessionLocal() as db:
            items = db.query(User).order_by(User.created_at.desc()).all()
            
            data = [
                {
                    "id": u.id,
                    "name": u.name,
                    "email": u.email,
                    "role": u.role,
                    "status": u.status
                }
                for u in items
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

@router.get("/{user_id}")
def get_user(user_id: int):
    try:
        with SessionLocal() as db:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return JSONResponse(
                    status_code=404,
                    content={"error": "User not found"},
                    headers=get_cors_headers()
                )
            
            return JSONResponse(
                content={
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "role": user.role,
                    "status": user.status
                },
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )

@router.put("/{user_id}")
def update_user(user_id: int, user: UserCreate):
    try:
        with SessionLocal() as db:
            existing = db.query(User).filter(User.id == user_id).first()
            
            if not existing:
                return JSONResponse(
                    status_code=404,
                    content={"error": "User not found"},
                    headers=get_cors_headers()
                )
            
            existing.name = user.name
            existing.email = user.email
            existing.role = user.role
            existing.status = user.status
            
            db.commit()
            db.refresh(existing)
            
            return JSONResponse(
                content={
                    "id": existing.id,
                    "name": existing.name,
                    "email": existing.email,
                    "role": existing.role,
                    "status": existing.status
                },
                headers=get_cors_headers()
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
            headers=get_cors_headers()
        )
