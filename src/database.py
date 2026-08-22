"""
FinnPayments - Database Layer
SQLite database with SQLAlchemy ORM for invoice and accounting data.
"""

import os
import json
import logging
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from contextlib import contextmanager

logger = logging.getLogger("FinnPayments.Database")

DATABASE_URL = os.getenv("FINNPAYMENTS_DB_URL", "sqlite:///finnpayments.db")

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ─── ORM Models ──────────────────────────────────────────

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(String(50), unique=True, nullable=False, index=True)
    invoice_type = Column(String(20), default="supplier")
    status = Column(String(20), default="pending_review")
    
    # Vendor/Client Info
    vendor_name = Column(String(255), nullable=False)
    vendor_address = Column(Text)
    vendor_brn = Column(String(50))
    vendor_vat = Column(String(50))
    
    # Invoice Details
    invoice_number = Column(String(100), index=True)
    invoice_date = Column(String(20))
    due_date = Column(String(20))
    purchase_order = Column(String(100))
    currency = Column(String(10), default="MUR")
    
    # Amounts
    subtotal = Column(Float, default=0.0)
    tax_total = Column(Float, default=0.0)
    total_amount = Column(Float, default=0.0)
    
    # Metadata
    payment_terms = Column(Text)
    bank_details = Column(Text)
    notes = Column(Text)
    project_code = Column(String(50))
    cost_center = Column(String(50))
    
    # AI Processing
    confidence_score = Column(Float, default=0.0)
    raw_text = Column(Text)
    ai_analysis = Column(Text)  # JSON string
    source_file = Column(String(500))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Multi-company
    company_id = Column(String(50), index=True)

    # Maker/checker
    approved_by = Column(String(50))
    posted_by = Column(String(50))

    # TDS (Tax Deducted at Source)
    tds_applicable = Column(Boolean, default=False)
    tds_rate = Column(Float, default=0.0)
    tds_amount = Column(Float, default=0.0)
    tds_paid_to_mra = Column(Boolean, default=False)
    tds_paid_date = Column(String(20))

    # Vendor master link
    vendor_id = Column(Integer, index=True)
    vendor_match_confidence = Column(Float, default=0.0)

    # Relationships
    line_items = relationship("InvoiceLineItemDB", back_populates="invoice", cascade="all, delete-orphan")
    journal_entries = relationship("JournalEntryDB", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceLineItemDB(Base):
    __tablename__ = "invoice_line_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(String(50), ForeignKey("invoices.invoice_id"), nullable=False)
    line_number = Column(Integer)
    description = Column(Text)
    quantity = Column(Float, default=1.0)
    unit_price = Column(Float, default=0.0)
    amount = Column(Float, default=0.0)
    tax_rate = Column(Float, default=15.0)
    tax_amount = Column(Float, default=0.0)
    account_code = Column(String(20))
    cost_center = Column(String(50))
    project_code = Column(String(50))
    
    invoice = relationship("Invoice", back_populates="line_items")


class JournalEntryDB(Base):
    __tablename__ = "journal_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(String(50), unique=True, nullable=False, index=True)
    invoice_id = Column(String(50), ForeignKey("invoices.invoice_id"))
    entry_date = Column(String(20))
    reference = Column(String(100))
    description = Column(Text)
    total_debit = Column(Float, default=0.0)
    total_credit = Column(Float, default=0.0)
    is_balanced = Column(Boolean, default=True)
    status = Column(String(20), default="draft")
    created_by = Column(String(100), default="system")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Multi-company
    company_id = Column(String(50), index=True)

    # Maker/checker
    approved_by = Column(String(50))
    posted_by = Column(String(50))

    invoice = relationship("Invoice", back_populates="journal_entries")
    lines = relationship("JournalEntryLineDB", back_populates="journal_entry", cascade="all, delete-orphan")


class JournalEntryLineDB(Base):
    __tablename__ = "journal_entry_lines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(String(50), ForeignKey("journal_entries.entry_id"), nullable=False)
    account_code = Column(String(20))
    account_name = Column(String(255))
    description = Column(Text)
    debit = Column(Float, default=0.0)
    credit = Column(Float, default=0.0)
    cost_center = Column(String(50))
    project_code = Column(String(50))
    
    journal_entry = relationship("JournalEntryDB", back_populates="lines")


class ChartOfAccountsDB(Base):
    __tablename__ = "chart_of_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    category = Column(String(20))  # asset, liability, equity, revenue, expense
    parent_code = Column(String(20))
    description = Column(Text)
    is_active = Column(Boolean, default=True)


# ─── Database Initialization ─────────────────────────────



class ClassificationRule(Base):
    __tablename__ = "classification_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vendor_name = Column(String(255), index=True)
    description_pattern = Column(String(500))
    account_code = Column(String(20), nullable=False)
    account_name = Column(String(255))
    user_context = Column(Text)
    source = Column(String(20), default="reclassify")  # reclassify, manual
    times_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Multi-company
    company_id = Column(String(50), index=True)


class TDSRate(Base):
    __tablename__ = "tds_rates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_type = Column(String(100), nullable=False)
    description = Column(Text)
    rate = Column(Float, nullable=False)
    threshold = Column(Float, default=0.0)
    resident = Column(Boolean, default=True)
    non_resident = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company_id = Column(String(50), index=True)


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    aliases = Column(Text)  # JSON array of alternative names for fuzzy matching
    brn = Column(String(50))
    vat = Column(String(50))
    address = Column(Text)
    phone = Column(String(50))
    email = Column(String(255))
    default_account_code = Column(String(20))
    default_tds_rate = Column(Float, default=0.0)
    payment_terms = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    company_id = Column(String(50), index=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(String(50))
    user_email = Column(String(255))
    action = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(50))
    entity_id = Column(String(100))
    description = Column(Text)
    company_id = Column(String(50), index=True)
    ip_address = Column(String(45))


def init_db():
    """Create all tables, run migrations, and seed chart of accounts"""
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created")
    _migrate_business_db()
    _seed_chart_of_accounts()
    _seed_tds_rates()


def _migrate_business_db():
    """Add company_id columns to existing tables and backfill to default company."""
    import sqlite3
    import os
    from src.auth_models import auth_db

    db_path = os.getenv("FINNPAYMENTS_DB_URL", "sqlite:///finnpayments.db")
    if db_path.startswith("sqlite:///"):
        db_path = db_path.replace("sqlite:///", "")

    if not os.path.exists(db_path):
        return  # fresh DB, create_all already made columns

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    def column_exists(table, column):
        cursor.execute(f"PRAGMA table_info({table})")
        return any(row[1] == column for row in cursor.fetchall())

    # Add company_id to invoices, journal_entries, classification_rules
    for table in ["invoices", "journal_entries", "classification_rules"]:
        if not column_exists(table, "company_id"):
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN company_id TEXT")
            logger.info(f"✅ Added company_id column to {table}")

    # Add maker/checker columns to invoices and journal_entries
    for table in ["invoices", "journal_entries"]:
        for col in ["approved_by", "posted_by"]:
            if not column_exists(table, col):
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} TEXT")
                logger.info(f"✅ Added {col} column to {table}")

    # Add TDS columns to invoices
    tds_columns = [
        ("tds_applicable", "INTEGER DEFAULT 0"),
        ("tds_rate", "REAL DEFAULT 0.0"),
        ("tds_amount", "REAL DEFAULT 0.0"),
        ("tds_paid_to_mra", "INTEGER DEFAULT 0"),
        ("tds_paid_date", "TEXT"),
    ]
    for col, coltype in tds_columns:
        if not column_exists("invoices", col):
            cursor.execute(f"ALTER TABLE invoices ADD COLUMN {col} {coltype}")
            logger.info(f"✅ Added {col} column to invoices")

    # Add vendor link columns to invoices
    vendor_columns = [
        ("vendor_id", "INTEGER"),
        ("vendor_match_confidence", "REAL DEFAULT 0.0"),
    ]
    for col, coltype in vendor_columns:
        if not column_exists("invoices", col):
            cursor.execute(f"ALTER TABLE invoices ADD COLUMN {col} {coltype}")
            logger.info(f"✅ Added {col} column to invoices")

    conn.commit()

    # Backfill: assign all existing rows to the default company
    companies = auth_db.get_companies()
    if not companies:
        conn.close()
        return

    default_company_id = companies[0]['id']

    for table in ["invoices", "journal_entries", "classification_rules"]:
        cursor.execute(f"UPDATE {table} SET company_id = ? WHERE company_id IS NULL", (default_company_id,))
        if cursor.rowcount > 0:
            logger.info(f"✅ Backfilled {cursor.rowcount} rows in {table} to default company")

    # Create index on company_id for performance
    for table in ["invoices", "journal_entries", "classification_rules"]:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS ix_{table}_company_id ON {table} (company_id)")
        except Exception:
            pass

    conn.commit()
    conn.close()


def _seed_chart_of_accounts():
    """Seed default chart of accounts if empty"""
    db = SessionLocal()
    try:
        if db.query(ChartOfAccountsDB).count() > 0:
            return
        
        default_accounts = [
            # Assets
            ("1000", "Cash and Cash Equivalents", "asset", None),
            ("1010", "Petty Cash", "asset", "1000"),
            ("1100", "Accounts Receivable", "asset", None),
            ("1200", "Prepaid Expenses", "asset", None),
            ("1300", "Inventory", "asset", None),
            ("1500", "Property, Plant & Equipment", "asset", None),
            ("1510", "Land & Buildings", "asset", "1500"),
            ("1520", "Furniture & Equipment", "asset", "1500"),
            ("1530", "Motor Vehicles", "asset", "1500"),
            ("1590", "Accumulated Depreciation", "asset", "1500"),
            
            # Liabilities
            ("2000", "Accounts Payable", "liability", None),
            ("2100", "VAT Payable", "liability", None),
            ("2110", "VAT Input (Receivable)", "liability", None),
            ("2200", "Accrued Expenses", "liability", None),
            ("2300", "Short-term Loans", "liability", None),
            ("2500", "Long-term Loans", "liability", None),
            
            # Equity
            ("3000", "Share Capital", "equity", None),
            ("3100", "Retained Earnings", "equity", None),
            ("3200", "Current Year Earnings", "equity", None),
            
            # Revenue
            ("4000", "Sales Revenue", "revenue", None),
            ("4010", "Property Sales", "revenue", "4000"),
            ("4020", "Rental Income", "revenue", "4000"),
            ("4030", "Management Fees", "revenue", "4000"),
            ("4040", "Golf & Leisure Revenue", "revenue", "4000"),
            ("4100", "Other Income", "revenue", None),
            ("4110", "Interest Income", "revenue", "4100"),
            
            # Expenses
            ("5000", "Cost of Sales", "expense", None),
            ("5100", "Construction Costs", "expense", "5000"),
            ("5200", "Land Costs", "expense", "5000"),
            ("6000", "Operating Expenses", "expense", None),
            ("6010", "Salaries & Wages", "expense", "6000"),
            ("6020", "Employee Benefits", "expense", "6000"),
            ("6030", "Rent & Utilities", "expense", "6000"),
            ("6040", "Insurance", "expense", "6000"),
            ("6050", "Professional Fees", "expense", "6000"),
            ("6060", "Marketing & Advertising", "expense", "6000"),
            ("6070", "Office Supplies", "expense", "6000"),
            ("6080", "Travel & Entertainment", "expense", "6000"),
            ("6090", "Repairs & Maintenance", "expense", "6000"),
            ("6100", "Depreciation", "expense", "6000"),
            ("6110", "IT & Software", "expense", "6000"),
            ("6120", "Security", "expense", "6000"),
            ("6130", "Landscaping & Grounds", "expense", "6000"),
            ("7000", "Finance Costs", "expense", None),
            ("7010", "Bank Charges", "expense", "7000"),
            ("7020", "Interest Expense", "expense", "7000"),
            ("7030", "Foreign Exchange Loss", "expense", "7000"),
        ]
        
        for code, name, category, parent in default_accounts:
            db.add(ChartOfAccountsDB(
                code=code, name=name, category=category, parent_code=parent
            ))
        
        db.commit()
        logger.info(f"✅ Seeded {len(default_accounts)} chart of accounts entries")
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding accounts: {e}")
    finally:
        db.close()


def _seed_tds_rates():
    """Seed default Mauritian TDS rates if no rates exist for any company."""
    from src.auth_models import auth_db
    db = SessionLocal()
    try:
        if db.query(TDSRate).count() > 0:
            return

        companies = auth_db.get_companies()
        if not companies:
            return

        default_rates = [
            ("Professional Fees", "Legal, audit, consultancy, advisory services", 5.0, 0, True, True),
            ("Rent", "Rental of property, land, buildings", 5.0, 0, True, True),
            ("Interest", "Interest on loans, debentures, deposits", 15.0, 0, False, True),
            ("Royalties", "Royalty payments for use of intellectual property", 15.0, 0, False, True),
            ("Contractor Payments", "Construction, subcontracting, public works", 3.0, 0, True, True),
            ("Transport", "Transport of goods, haulage, freight", 3.0, 0, True, True),
            ("Security Services", "Security guarding, cash-in-transit", 3.0, 0, True, True),
            ("Cleaning Services", "Cleaning, janitorial, pest control", 3.0, 0, True, True),
            ("Catering", "Catering and food supply", 3.0, 0, True, True),
            ("Management Fees", "Corporate management, administrative fees", 5.0, 0, True, True),
        ]

        for company in companies:
            for payment_type, desc, rate, threshold, resident, non_resident in default_rates:
                db.add(TDSRate(
                    payment_type=payment_type,
                    description=desc,
                    rate=rate,
                    threshold=threshold,
                    resident=resident,
                    non_resident=non_resident,
                    is_active=True,
                    company_id=company['id'],
                ))

        db.commit()
        logger.info(f"✅ Seeded {len(default_rates)} TDS rates for {len(companies)} company(ies)")
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding TDS rates: {e}")
    finally:
        db.close()


@contextmanager
def get_db():
    """Database session context manager"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
