"""
COMPLETE models_extended.py - COPY THIS ENTIRE FILE
Replace your app/models_extended.py with this complete version
"""

from sqlalchemy import (
    Column, Integer, String, Numeric, Date, Text, ForeignKey,
    Boolean, TIMESTAMP, func
)
from sqlalchemy.orm import relationship
from app.database import Base


# ----------------------------
# DAILY CASHFLOW
# ----------------------------
class DailyCashflow(Base):
    __tablename__ = "cashflow_daily"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, index=True)
    balance = Column(Numeric(12, 2))


# ----------------------------
# CLIENTS
# ----------------------------
class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    payment_terms = Column(Integer, default=30)
    created_at = Column(TIMESTAMP, server_default=func.now())


# ----------------------------
# SUPPLIERS
# ----------------------------
class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255))
    payment_terms = Column(Integer, default=30)
    created_at = Column(TIMESTAMP, server_default=func.now())


# ----------------------------
# SALES INVOICES
# ----------------------------
class InvoiceSale(Base):
    __tablename__ = "invoices_sales"

    id = Column(Integer, primary_key=True, index=True)
    client_name = Column(String, nullable=False)
    client_email = Column(String)
    number = Column(String, nullable=False)
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    amount_ht = Column(Numeric(12, 2))
    vat_rate = Column(Numeric(4, 3), default=0.20)
    amount_ttc = Column(Numeric(12, 2))
    description = Column(Text)
    status = Column(String, default="unpaid")
    created_at = Column(TIMESTAMP, server_default=func.now())


# ----------------------------
# PURCHASE INVOICES
# ----------------------------
class InvoicePurchase(Base):
    __tablename__ = "invoices_purchases"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    number = Column(String(255))
    issue_date = Column(Date)
    due_date = Column(Date)
    amount = Column(Numeric(12, 2))
    vat = Column(Numeric(12, 2))
    status = Column(String(50), default="pending")
    paid_at = Column(Date)
    created_at = Column(TIMESTAMP, server_default=func.now())
    supplier = relationship("Supplier")


# ----------------------------
# BANK TRANSACTIONS
# ----------------------------
class BankTransaction(Base):
    __tablename__ = "bank_transactions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, index=True, nullable=False)
    label = Column(Text)
    amount = Column(Numeric(12, 2), nullable=False)
    balance = Column(Numeric(12, 2))
    category = Column(String(255))
    created_at = Column(TIMESTAMP, server_default=func.now())


# ----------------------------
# ALERTS
# ----------------------------
class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50))
    related_id = Column(Integer, nullable=True)
    message = Column(Text)
    due_date = Column(Date)
    status = Column(String(50), default="pending")
    created_at = Column(TIMESTAMP, server_default=func.now())


# ============================================================
# ✅ NEW MODELS ADDED BELOW - THESE WERE MISSING!
# ============================================================

# ----------------------------
# ✅ EMPLOYEES (NEW)
# ----------------------------
class Employee(Base):
    """Employee information - ADDED"""
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    position = Column(String(100))
    contract_type = Column(String(50), default="CDI")
    gross_salary = Column(Numeric(12, 2), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    status = Column(String(20), default="active")
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


# ----------------------------
# ✅ POINTAGES (NEW - CRITICAL FIX)
# ----------------------------
class Pointage(Base):
    """
    Time tracking - ADDED
    ✅ CRITICAL: Uses 'employee' column (String), NOT 'employee_id'
    This matches your database schema
    """
    __tablename__ = "pointages"

    id = Column(Integer, primary_key=True, index=True)
    
    # ✅ CRITICAL FIX: employee (String), not employee_id (Integer)
    employee = Column(String, nullable=False, index=True)
    
    clock_in = Column(TIMESTAMP, nullable=False)
    clock_out = Column(TIMESTAMP)
    break_duration = Column(Integer, default=0)
    total_hours = Column(Numeric(5, 2))
    notes = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())


# ----------------------------
# ✅ TASKS (NEW)
# ----------------------------
class Task(Base):
    """Task management - ADDED"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    assigned_to = Column(String(255))
    priority = Column(String(20), default="medium")
    status = Column(String(20), default="todo")
    due_date = Column(Date)
    completed_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


# ----------------------------
# ✅ USERS (NEW)
# ----------------------------
class User(Base):
    """User accounts - ADDED"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    company_name = Column(String(255))
    siret = Column(String(14))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    last_login = Column(TIMESTAMP)


print("✅ Extended models loaded - Pointage, Employee, Task, User models added")
