from sqlalchemy import (
    Column, Integer, String, Numeric, Date, Text, ForeignKey,
    TIMESTAMP, func
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
    vat_rate = Column(Numeric(4, 3), default=0.20)  # ex: 0.20
    amount_ttc = Column(Numeric(12, 2))

    description = Column(Text)
    status = Column(String, default="unpaid")  # unpaid / paid / sent
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
