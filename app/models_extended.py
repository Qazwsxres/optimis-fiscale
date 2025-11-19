from sqlalchemy import Column, Integer, String, Numeric, Date, Text, ForeignKey, CheckConstraint, TIMESTAMP, func
from sqlalchemy.orm import relationship
from .database import Base
from sqlalchemy import Column, Integer, Float, Date
from app.database import Base

class DailyCashflow(Base):
    __tablename__ = "cashflow_daily"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, index=True)
    balance = Column(Float)

class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String)
    payment_terms = Column(Integer, default=30)
    created_at = Column(TIMESTAMP, server_default=func.now())

class Supplier(Base):
    __tablename__ = "suppliers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String)
    payment_terms = Column(Integer, default=30)
    created_at = Column(TIMESTAMP, server_default=func.now())

class InvoiceSale(Base):
    __tablename__ = "invoices_sales"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    number = Column(String)
    issue_date = Column(Date)
    due_date = Column(Date)
    amount = Column(Numeric(12,2))
    vat = Column(Numeric(12,2))
    status = Column(String, default="draft")
    paid_at = Column(Date)
    created_at = Column(TIMESTAMP, server_default=func.now())
    client = relationship("Client")

class InvoicePurchase(Base):
    __tablename__ = "invoices_purchases"
    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"))
    number = Column(String)
    issue_date = Column(Date)
    due_date = Column(Date)
    amount = Column(Numeric(12,2))
    vat = Column(Numeric(12,2))
    status = Column(String, default="pending")
    paid_at = Column(Date)
    created_at = Column(TIMESTAMP, server_default=func.now())
    supplier = relationship("Supplier")

class BankTransaction(Base):
    __tablename__ = "bank_transactions"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False)
    label = Column(Text)
    amount = Column(Numeric(12,2), nullable=False)
    balance = Column(Numeric(12,2))
    category = Column(String)
    created_at = Column(TIMESTAMP, server_default=func.now())

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String)
    related_id = Column(Integer)
    message = Column(Text)
    due_date = Column(Date)
    status = Column(String, default="pending")
    created_at = Column(TIMESTAMP, server_default=func.now())
