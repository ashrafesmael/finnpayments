"""
FinnPayments - Data Models
Pydantic models for invoice processing and accounting entries.
Mirrors FinnVerify's model architecture.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import date, datetime


# ─── Enums ────────────────────────────────────────────────

class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    POSTED = "posted"
    PAID = "paid"
    CANCELLED = "cancelled"


class InvoiceType(str, Enum):
    SUPPLIER = "supplier"        # Accounts Payable
    CLIENT = "client"            # Accounts Receivable
    CREDIT_NOTE = "credit_note"
    DEBIT_NOTE = "debit_note"
    PROFORMA = "proforma"


class EntryType(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class AccountCategory(str, Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"


class Currency(str, Enum):
    MUR = "MUR"
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    ZAR = "ZAR"


# ─── Chart of Accounts ───────────────────────────────────

class AccountCode(BaseModel):
    """Chart of Accounts entry"""
    code: str = Field(..., description="Account code (e.g., 2100, 4010)")
    name: str = Field(..., description="Account name")
    category: AccountCategory
    parent_code: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


# ─── Line Items ───────────────────────────────────────────

class InvoiceLineItem(BaseModel):
    """Individual line item on an invoice"""
    line_number: int
    description: str
    quantity: float = 1.0
    unit_price: float
    amount: float
    tax_rate: float = 15.0  # Mauritius VAT default
    tax_amount: float = 0.0
    account_code: Optional[str] = None  # GL account to post to
    cost_center: Optional[str] = None
    project_code: Optional[str] = None


# ─── Invoice Models ───────────────────────────────────────

class InvoiceExtracted(BaseModel):
    """Data extracted from uploaded invoice document"""
    vendor_name: Optional[str] = None
    vendor_address: Optional[str] = None
    vendor_brn: Optional[str] = None       # Business Registration Number
    vendor_vat: Optional[str] = None       # VAT Registration Number
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    purchase_order: Optional[str] = None
    currency: str = "MUR"
    subtotal: Optional[float] = None
    tax_total: Optional[float] = None
    total_amount: Optional[float] = None
    line_items: List[InvoiceLineItem] = []
    payment_terms: Optional[str] = None
    bank_details: Optional[str] = None
    notes: Optional[str] = None
    confidence_score: float = 0.0
    raw_text: Optional[str] = None


class InvoiceCreateRequest(BaseModel):
    """Request to create an invoice manually"""
    invoice_type: InvoiceType = InvoiceType.SUPPLIER
    vendor_name: str
    vendor_brn: Optional[str] = None
    invoice_number: str
    invoice_date: str
    due_date: Optional[str] = None
    currency: Currency = Currency.MUR
    line_items: List[InvoiceLineItem]
    notes: Optional[str] = None
    project_code: Optional[str] = None
    cost_center: Optional[str] = None


class InvoiceResponse(BaseModel):
    """Response after invoice processing"""
    invoice_id: str
    status: InvoiceStatus
    invoice_type: InvoiceType
    vendor_name: str
    invoice_number: str
    invoice_date: str
    due_date: Optional[str] = None
    currency: str = "MUR"
    subtotal: float
    tax_total: float
    total_amount: float
    line_items: List[InvoiceLineItem]
    accounting_entries: List[Dict[str, Any]] = []
    ai_suggestions: Optional[Dict[str, Any]] = None
    confidence_score: float = 0.0
    created_at: str
    updated_at: str


# ─── Accounting Entry Models ─────────────────────────────

class JournalEntryLine(BaseModel):
    """Single line in a journal entry"""
    account_code: str
    account_name: str
    description: str
    debit: float = 0.0
    credit: float = 0.0
    cost_center: Optional[str] = None
    project_code: Optional[str] = None


class JournalEntry(BaseModel):
    """Complete journal entry (double-entry bookkeeping)"""
    entry_id: str
    invoice_id: Optional[str] = None
    entry_date: str
    reference: str
    description: str
    lines: List[JournalEntryLine]
    total_debit: float
    total_credit: float
    is_balanced: bool = True
    status: str = "draft"  # draft, posted, reversed
    created_by: str = "system"
    created_at: str


class AccountingEntriesResponse(BaseModel):
    """Response containing generated accounting entries"""
    invoice_id: str
    journal_entries: List[JournalEntry]
    summary: Dict[str, Any]


# ─── Dashboard Models ────────────────────────────────────

class DashboardStats(BaseModel):
    """Dashboard statistics"""
    total_invoices: int = 0
    pending_review: int = 0
    approved: int = 0
    posted: int = 0
    total_payable: float = 0.0
    total_receivable: float = 0.0
    this_month_processed: int = 0
    avg_processing_time: float = 0.0
    recent_invoices: List[Dict[str, Any]] = []
    monthly_totals: List[Dict[str, Any]] = []


# ─── Upload Response ─────────────────────────────────────

class DocumentUploadResponse(BaseModel):
    """Response after document upload and extraction"""
    invoice_id: str
    status: str
    extracted_data: InvoiceExtracted
    suggested_entries: List[JournalEntry] = []
    ai_analysis: Optional[Dict[str, Any]] = None
    processing_time: float
    message: str
