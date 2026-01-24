"""
Enhanced Banking Models for Bankin/Finary Integration
Compatible with external banking aggregators
FIXED: All 'metadata' fields renamed to 'provider_metadata'
"""

from sqlalchemy import (
    Column, Integer, String, Numeric, Date, Text, ForeignKey,
    Boolean, JSON, TIMESTAMP, func
)
from sqlalchemy.orm import relationship
from app.database import Base


# ============================================
# BANK ACCOUNTS
# ============================================
class BankAccount(Base):
    """
    Bank accounts - can be synced from Bankin/Finary
    """
    __tablename__ = "bank_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(255), unique=True, index=True)  # ID from Bankin/Finary
    name = Column(String(255), nullable=False)
    bank_name = Column(String(255))
    iban = Column(String(34))
    bic = Column(String(11))
    account_type = Column(String(50), default="checking")  # checking, savings, credit
    currency = Column(String(3), default="EUR")
    balance = Column(Numeric(15, 2), default=0)
    is_active = Column(Boolean, default=True)
    last_sync = Column(TIMESTAMP)
    
    # Provider info
    provider = Column(String(50))  # bankin, finary, bridge, manual
    
    # FIXED: renamed from metadata to provider_metadata (SQLAlchemy reserved word)
    provider_metadata = Column(JSON)  # Store full JSON response from aggregator
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relations
    transactions = relationship("BankTransactionEnhanced", back_populates="account")
    sync_logs = relationship("SyncLog", back_populates="account")


# ============================================
# ENHANCED BANK TRANSACTIONS
# ============================================
class BankTransactionEnhanced(Base):
    """
    Enhanced transactions table with categorization and external sync
    """
    __tablename__ = "bank_transactions_enhanced"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("bank_accounts.id"), nullable=False)
    external_id = Column(String(255), unique=True, index=True)  # ID from aggregator
    
    # Transaction details
    date = Column(Date, nullable=False, index=True)
    value_date = Column(Date)  # Date de valeur (for interest calculation)
    label = Column(Text)
    raw_label = Column(Text)  # Original label from bank
    amount = Column(Numeric(15, 2), nullable=False)
    balance = Column(Numeric(15, 2))
    
    # Categorization
    category_id = Column(Integer, ForeignKey("categories.id"))
    sub_category = Column(String(100))
    is_recurring = Column(Boolean, default=False)
    confidence_score = Column(Numeric(3, 2))  # 0.00 to 1.00 for ML categorization
    
    # Business logic linking
    invoice_sale_id = Column(Integer, ForeignKey("invoices_sales.id"))
    invoice_purchase_id = Column(Integer, ForeignKey("invoices_purchases.id"))
    
    # Flags
    is_reconciled = Column(Boolean, default=False)
    is_internal_transfer = Column(Boolean, default=False)
    
    # FIXED: renamed from metadata to provider_metadata
    provider_metadata = Column(JSON)  # Metadata from aggregator
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relations
    account = relationship("BankAccount", back_populates="transactions")
    category = relationship("Category")


# ============================================
# CATEGORIES
# ============================================
class Category(Base):
    """
    Transaction categories (hierarchical)
    """
    __tablename__ = "categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id"))
    
    # Display
    icon = Column(String(50))  # emoji or icon class
    color = Column(String(7))  # Hex color like #FF5733
    
    # Type
    type = Column(String(20), default="expense")  # income, expense, transfer, savings
    
    # System vs user categories
    is_system = Column(Boolean, default=False)
    
    # Tax deductibility
    is_deductible = Column(Boolean, default=False)
    deduction_rate = Column(Numeric(3, 2))  # 0.00 to 1.00
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relations
    parent = relationship("Category", remote_side=[id], backref="children")


# ============================================
# BUDGETS
# ============================================
class Budget(Base):
    """
    Monthly/yearly budgets per category
    """
    __tablename__ = "budgets"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"))
    
    # Budget amount
    amount = Column(Numeric(12, 2), nullable=False)
    
    # Period
    period_type = Column(String(20), default="monthly")  # monthly, quarterly, yearly
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Alerts
    alert_threshold = Column(Numeric(3, 2), default=0.80)  # Alert at 80% used
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # Relations
    category = relationship("Category")


# ============================================
# SYNC LOGS
# ============================================
class SyncLog(Base):
    """
    Track synchronization attempts with external providers
    """
    __tablename__ = "sync_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False)  # bankin, finary, bridge
    account_id = Column(Integer, ForeignKey("bank_accounts.id"))
    
    # Status
    status = Column(String(20), default="pending")  # pending, running, success, failed, partial
    
    # Metrics
    transactions_fetched = Column(Integer, default=0)
    transactions_created = Column(Integer, default=0)
    transactions_updated = Column(Integer, default=0)
    transactions_skipped = Column(Integer, default=0)
    
    # Error tracking
    error_message = Column(Text)
    error_code = Column(String(50))
    
    # Timing
    started_at = Column(TIMESTAMP)
    completed_at = Column(TIMESTAMP)
    duration_seconds = Column(Integer)
    
    # FIXED: renamed from metadata to provider_metadata
    provider_metadata = Column(JSON)  # Additional sync metadata
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relations
    account = relationship("BankAccount", back_populates="sync_logs")


# ============================================
# RECURRING TRANSACTIONS
# ============================================
class RecurringTransaction(Base):
    """
    Detected recurring transactions (subscriptions, salaries, etc.)
    """
    __tablename__ = "recurring_transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("bank_accounts.id"))
    category_id = Column(Integer, ForeignKey("categories.id"))
    
    # Pattern
    label_pattern = Column(String(255))
    amount_min = Column(Numeric(12, 2))
    amount_max = Column(Numeric(12, 2))
    
    # Frequency
    frequency = Column(String(20))  # daily, weekly, monthly, yearly
    day_of_month = Column(Integer)  # For monthly (1-31)
    day_of_week = Column(Integer)  # For weekly (0-6)
    
    # Next expected
    next_expected_date = Column(Date)
    last_occurrence_date = Column(Date)
    
    # Confidence
    confidence = Column(Numeric(3, 2))  # 0.00 to 1.00
    occurrence_count = Column(Integer, default=0)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())


# ============================================
# FINANCIAL GOALS
# ============================================
class FinancialGoal(Base):
    """
    Savings goals and targets
    """
    __tablename__ = "financial_goals"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Target
    target_amount = Column(Numeric(12, 2), nullable=False)
    current_amount = Column(Numeric(12, 2), default=0)
    
    # Timeline
    start_date = Column(Date, nullable=False)
    target_date = Column(Date, nullable=False)
    
    # Category (optional - track specific category savings)
    category_id = Column(Integer, ForeignKey("categories.id"))
    
    # Status
    is_completed = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


# ============================================
# WEBHOOKS
# ============================================
class WebhookEvent(Base):
    """
    Store webhook events from external providers
    """
    __tablename__ = "webhook_events"
    
    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String(50), nullable=False)
    event_type = Column(String(100), nullable=False)
    
    # Data
    payload = Column(JSON, nullable=False)
    headers = Column(JSON)
    
    # Processing
    status = Column(String(20), default="pending")  # pending, processed, failed
    processed_at = Column(TIMESTAMP)
    error_message = Column(Text)
    
    # Deduplication
    external_event_id = Column(String(255), unique=True)
    
    received_at = Column(TIMESTAMP, server_default=func.now())


print("✅ Banking models loaded - all metadata fields renamed to provider_metadata")
