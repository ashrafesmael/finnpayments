"""
FinnPayments - FastAPI Application
REST API for invoice processing and accounting entries.
Architecture mirrors FinnVerify's api.py.
"""

import os
import time
import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel as PydanticBaseModel

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Form, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse

from src.models import (
    InvoiceStatus, InvoiceType, Currency,
    InvoiceCreateRequest, InvoiceResponse,
    DocumentUploadResponse, DashboardStats,
    JournalEntry, AccountingEntriesResponse
)
from src.database import (
    init_db, get_db, Invoice, InvoiceLineItemDB,
    JournalEntryDB, JournalEntryLineDB, ChartOfAccountsDB, ClassificationRule
)
from src.invoice_engine import process_invoice, generate_invoice_id
from src.accounting_engine import (
    generate_accounting_entries, validate_journal_entry, suggest_account_code
)
from src.auth_api import router as auth_router, get_current_company, get_current_user

logger = logging.getLogger("FinnPayments.API")

# ─── App Configuration ────────────────────────────────────

app = FastAPI(
    title="FinnPayments API",
    description="Invoice Processing & Accounting Entries - A product of AlgoDynamix Ltd",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS - allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files & uploads
upload_directory = Path("uploads")
upload_directory.mkdir(exist_ok=True)
# Keep temp_uploads for backward compatibility
Path("temp_uploads").mkdir(exist_ok=True)
static_directory = Path("static")
static_directory.mkdir(exist_ok=True)

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except:
    pass

# In-memory results store (mirrors FinnVerify pattern)
results_store: Dict[str, Dict] = {}

# ─── Authentication router ───────────────────────────────
app.include_router(auth_router)


# ─── Startup ──────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    logger.info("🚀 FinnPayments API started")


# ─── Root & Health ────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "message": "FinnPayments API",
        "product": "Invoice Processing & Accounting Entries",
        "company": "AlgoDynamix Ltd",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "upload": "/invoices/upload",
            "invoices": "/invoices",
            "entries": "/accounting/entries",
            "accounts": "/accounting/chart-of-accounts",
            "dashboard": "/dashboard/stats",
        }
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "FinnPayments",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }


# ─── Invoice Upload & Processing ─────────────────────────

@app.post("/invoices/upload", response_model=None)
async def upload_invoice(
    file: UploadFile = File(...),
    invoice_type: str = Form("supplier"),
    project_code: Optional[str] = Form(None),
    cost_center: Optional[str] = Form(None),
    company: dict = Depends(get_current_company),
):
    """
    Upload an invoice document for processing.
    Supports PDF, images, CSV, Excel.
    """
    start_time = time.time()
    
    # Validate file type
    allowed_extensions = ('.pdf', '.png', '.jpg', '.jpeg', '.docx', '.doc', '.txt', '.csv', '.xlsx', '.xls', '.bmp', '.tiff', '.webp')
    if not file.filename.lower().endswith(allowed_extensions):
        raise HTTPException(status_code=400, detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}")
    
    # Save uploaded file
    file_path = upload_directory / f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}"
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        logger.info(f"📁 Saved upload: {file_path} ({len(content)} bytes)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    
    # Process the invoice
    try:
        result = await process_invoice(str(file_path), invoice_type, company_id=company['id'])
    except Exception as e:
        logger.error(f"❌ Processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    
    # Handle multi-invoice PDF (result is a list)
    if isinstance(result, list):
        logger.info(f"📋 Multi-invoice upload: {len(result)} invoices detected")
        for r in result:
            try:
                _save_invoice_to_db(r, invoice_type, str(file_path), project_code, cost_center, company['id'])
                results_store[r["invoice_id"]] = r
            except Exception as e:
                logger.error(f"❌ Database save error for {r['invoice_id']}: {e}")
        
        total_time = time.time() - start_time
        return {
            "multi_invoice": True,
            "count": len(result),
            "invoices": result,
            "processing_time": round(total_time, 2),
            "message": f"{len(result)} invoices detected and processed in {total_time:.1f}s"
        }
    
    # Single invoice
    try:
        _save_invoice_to_db(result, invoice_type, str(file_path), project_code, cost_center, company['id'])
    except Exception as e:
        logger.error(f"❌ Database save error: {e}")
    
    results_store[result["invoice_id"]] = result
    
    processing_time = time.time() - start_time
    result["processing_time"] = round(processing_time, 2)
    
    return result


@app.post("/invoices/manual")
async def create_manual_invoice(request: InvoiceCreateRequest, company: dict = Depends(get_current_company)):
    """Create an invoice manually (no document upload)"""
    invoice_id = generate_invoice_id()
    
    invoice_data = {
        "vendor_name": request.vendor_name,
        "vendor_brn": request.vendor_brn,
        "invoice_number": request.invoice_number,
        "invoice_date": request.invoice_date,
        "due_date": request.due_date,
        "currency": request.currency.value if hasattr(request.currency, 'value') else request.currency,
        "line_items": [item.model_dump() for item in request.line_items],
        "subtotal": sum(item.amount - item.tax_amount for item in request.line_items),
        "tax_total": sum(item.tax_amount for item in request.line_items),
        "total_amount": sum(item.amount for item in request.line_items),
        "notes": request.notes,
        "project_code": request.project_code,
        "cost_center": request.cost_center,
        "confidence_score": 1.0,
    }
    
    # Generate accounting entries
    entries = generate_accounting_entries(invoice_id, invoice_data, request.invoice_type.value, company_id=company['id'])
    
    result = {
        "invoice_id": invoice_id,
        "status": "pending_review",
        "extracted_data": invoice_data,
        "suggested_entries": entries,
        "processing_time": 0.0,
        "message": "Manual invoice created successfully"
    }
    
    _save_invoice_to_db(result, request.invoice_type.value, None, request.project_code, request.cost_center, company['id'])
    results_store[invoice_id] = result
    
    return result


# ─── Invoice CRUD ─────────────────────────────────────────

@app.get("/invoices")
async def list_invoices(
    status: Optional[str] = None,
    invoice_type: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    search: Optional[str] = None,
    company: dict = Depends(get_current_company),
):
    """List all invoices with optional filtering"""
    with get_db() as db:
        query = db.query(Invoice).filter(Invoice.company_id == company['id']).order_by(Invoice.created_at.desc())
        
        if status:
            query = query.filter(Invoice.status == status)
        if invoice_type:
            query = query.filter(Invoice.invoice_type == invoice_type)
        if search:
            query = query.filter(
                (Invoice.vendor_name.ilike(f"%{search}%")) |
                (Invoice.invoice_number.ilike(f"%{search}%"))
            )
        
        total = query.count()
        invoices = query.offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "invoices": [_invoice_to_dict(inv) for inv in invoices],
            "limit": limit,
            "offset": offset,
        }


@app.get("/invoices/{invoice_id}")
async def get_invoice(invoice_id: str, company: dict = Depends(get_current_company)):
    """Get invoice details with line items and journal entries"""
    with get_db() as db:
        invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id, Invoice.company_id == company['id']).first()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        result = _invoice_to_dict(invoice)
        
        # Include line items
        result["line_items"] = [
            {
                "line_number": li.line_number,
                "description": li.description,
                "quantity": li.quantity,
                "unit_price": li.unit_price,
                "amount": li.amount,
                "tax_rate": li.tax_rate,
                "tax_amount": li.tax_amount,
                "account_code": li.account_code,
                "cost_center": li.cost_center,
                "project_code": li.project_code,
            }
            for li in invoice.line_items
        ]
        
        # Include journal entries
        result["journal_entries"] = [
            {
                "entry_id": je.entry_id,
                "entry_date": je.entry_date,
                "reference": je.reference,
                "description": je.description,
                "total_debit": je.total_debit,
                "total_credit": je.total_credit,
                "is_balanced": je.is_balanced,
                "status": je.status,
                "lines": [
                    {
                        "account_code": jel.account_code,
                        "account_name": jel.account_name,
                        "description": jel.description,
                        "debit": jel.debit,
                        "credit": jel.credit,
                        "cost_center": jel.cost_center,
                        "project_code": jel.project_code,
                    }
                    for jel in je.lines
                ]
            }
            for je in invoice.journal_entries
        ]
        
        # Include from memory store if available
        if invoice_id in results_store:
            result["ai_analysis"] = results_store[invoice_id].get("extracted_data", {}).get("notes")
        
        return result


@app.patch("/invoices/{invoice_id}/status")
async def update_invoice_status(
    invoice_id: str,
    status: str,
    company: dict = Depends(get_current_company),
    user: dict = Depends(get_current_user),
):
    """Update invoice status (approve, reject, post, etc.)"""
    valid_statuses = [s.value for s in InvoiceStatus]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
    
    with get_db() as db:
        invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id, Invoice.company_id == company['id']).first()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        old_status = invoice.status

        # Maker/checker: the user who approved cannot also post
        if status == "posted" and company.get('maker_checker_enabled'):
            if invoice.approved_by and invoice.approved_by == user['id']:
                raise HTTPException(
                    status_code=403,
                    detail="Maker/checker: You approved this invoice and cannot post it. Another user must post it."
                )

        # Track who approved
        if status == "approved":
            invoice.approved_by = user['id']

        # Track who posted
        if status == "posted":
            invoice.posted_by = user['id']

        invoice.status = status
        invoice.updated_at = datetime.utcnow()
        
        # If posting, also post journal entries
        if status == "posted":
            for je in invoice.journal_entries:
                je.status = "posted"
                je.posted_by = user['id']
        
        db.commit()
        
        return {
            "invoice_id": invoice_id,
            "old_status": old_status,
            "new_status": status,
            "message": f"Invoice status updated to {status}"
        }




@app.get("/invoices/{invoice_id}/document")
async def get_invoice_document(invoice_id: str, company: dict = Depends(get_current_company)):
    """Serve the original uploaded document for an invoice"""
    with get_db() as db:
        invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id, Invoice.company_id == company['id']).first()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if not invoice.source_file:
            raise HTTPException(status_code=404, detail="No document attached to this invoice")

        file_path = Path(invoice.source_file)

        # Also check temp_uploads if file was uploaded before migration
        if not file_path.exists():
            alt_path = Path("temp_uploads") / file_path.name
            if alt_path.exists():
                file_path = alt_path
            else:
                raise HTTPException(status_code=404, detail="Document file not found on disk")

        # Determine media type
        ext = file_path.suffix.lower()
        media_types = {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".bmp": "image/bmp",
            ".tiff": "image/tiff",
            ".webp": "image/webp",
        }
        media_type = media_types.get(ext, "application/octet-stream")

        return FileResponse(
            str(file_path),
            media_type=media_type,
            filename=file_path.name,
            headers={"Content-Disposition": f"inline; filename={file_path.name}"}
        )



@app.get("/invoices/{invoice_id}/document/preview")
async def get_invoice_document_preview(invoice_id: str, page: int = Query(0, ge=0), company: dict = Depends(get_current_company)):
    """Return invoice document pages as base64 images for inline viewing."""
    import base64
    from io import BytesIO

    with get_db() as db:
        invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id, Invoice.company_id == company['id']).first()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if not invoice.source_file:
            raise HTTPException(status_code=404, detail="No document attached")

        file_path = Path(invoice.source_file)
        if not file_path.exists():
            # Check temp_uploads fallback
            alt_path = Path("temp_uploads") / file_path.name
            if alt_path.exists():
                file_path = alt_path
            else:
                raise HTTPException(status_code=404, detail="File not found on disk")

        ext = file_path.suffix.lower()

        if ext in (".png", ".jpg", ".jpeg", ".bmp", ".webp", ".tiff"):
            # Image file: return as-is
            with open(file_path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode()
            mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                    "bmp": "image/bmp", "webp": "image/webp", "tiff": "image/tiff"}
            return {
                "total_pages": 1,
                "current_page": 0,
                "mime_type": mime.get(ext.lstrip("."), "image/png"),
                "image": img_data,
            }

        elif ext == ".pdf":
            try:
                from pdf2image import convert_from_path
                # Get total pages first
                from pdf2image.pdf2image import pdfinfo_from_path
                info = pdfinfo_from_path(str(file_path))
                total_pages = info.get("Pages", 1)

                # Clamp page number
                page = min(page, total_pages - 1)

                # Convert requested page (1-indexed for pdf2image)
                images = convert_from_path(
                    str(file_path),
                    first_page=page + 1,
                    last_page=page + 1,
                    dpi=150,
                    fmt="png"
                )

                if images:
                    buf = BytesIO()
                    images[0].save(buf, format="PNG")
                    img_data = base64.b64encode(buf.getvalue()).decode()
                    return {
                        "total_pages": total_pages,
                        "current_page": page,
                        "mime_type": "image/png",
                        "image": img_data,
                    }
                else:
                    raise HTTPException(status_code=500, detail="Failed to render PDF page")
            except ImportError:
                raise HTTPException(status_code=500, detail="pdf2image not installed")
        else:
            raise HTTPException(status_code=400, detail=f"Preview not supported for {ext} files")



class ReclassifyRequest(PydanticBaseModel):
    user_context: str


@app.post("/invoices/{invoice_id}/reclassify")
async def reclassify_invoice(invoice_id: str, request: ReclassifyRequest, company: dict = Depends(get_current_company)):
    """
    Reclassify invoice line items using user-provided context.
    Called when the system defaulted to Licences (01-6000-04) and the user
    provides additional context about the nature of the expense.
    """
    import httpx

    with get_db() as db:
        invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id, Invoice.company_id == company['id']).first()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        line_items = db.query(InvoiceLineItemDB).filter(
            InvoiceLineItemDB.invoice_id == invoice_id
        ).order_by(InvoiceLineItemDB.line_number).all()

        if not line_items:
            raise HTTPException(status_code=400, detail="No line items found")

        # Build context for LLM
        items_text = "\n".join([
            f"  Line {li.line_number}: {li.description} | Amount: {li.amount} | Current account: {li.account_code}"
            for li in line_items
        ])

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="AI service not configured")

        prompt = f"""You are an accounting classification expert for Mont Choisy Golf, a Mauritian property/golf company.

VENDOR: {invoice.vendor_name}
INVOICE #: {invoice.invoice_number}
DATE: {invoice.invoice_date}
TOTAL: {invoice.currency} {invoice.total_amount}

LINE ITEMS:
{items_text}

USER CONTEXT (the user has described this expense as):
"{request.user_context}"

CHART OF ACCOUNTS (assign the best account_code per line item):
01-5100-04  Basic Salary_Admin
01-5102-04  Statutory Contribution (NPS & TWEF)
01-5105-04  Staff Travelling Cost
01-5108-04  Recruitment Cost
01-5110-04  Training Staff Cost
01-5133-04  Medical Scheme
01-5002-01  Golf Cart Maintenance & General
01-5007-02  Event Cost
01-5201-01  Operating Supplies_Golf Course
01-6000-04  Licences (software licences, permits, domain renewals)
01-6001-04  Insurance_General
01-6002-04  Telephone, Mobiles and Internet
01-6003-04  ICT Expenses (software, IT services, hosting, SaaS, hardware)
01-6005-04  Printing, Postage & Stationery
01-6006-04  Professional Fees ADM (legal, consulting, advisory, law firms, court costs, notary, architects)
01-6007-04  Health & Safety Expenses
01-6008-04  Security Fees (security companies, cash handling, guarding)
01-6008-06  Marketing Cost_Others
01-6009-04  Pest Control
01-6010-04  Waste Removal
01-6010-06  General Marketing Materials
01-6015-04  Cleaning Expenses
01-6020-04  Office Supplies & Consumables
01-6021-04  Payroll Processing Fee
01-6022-04  Audit Fee
01-6023-04  Secretarial Fee
01-6025-04  Taxation Fee
01-6030-04  Subscriptions & Memberships
01-6050-05  R&M - Golf Course Fertilizers
01-6051-05  R&M - Fuel and Diesel
01-6053-05  R&M - Equipment Repairs
01-6057-05  R&M - Golf Course Chemicals
01-6058-05  R&M - Golf Course (Plant, Seed, Sand)
01-6059-05  R&M - Golf Course Maintenance Others
01-6070-05  Building Maintenance (painting, plumbing, electrical)
01-6075-05  External Maintenance Contractor
01-6076-05  Gas Clubhouse
01-6080-05  R&M - Irrigation Pumping Station
01-6090-05  Vehicle Running Expenses
01-6100-04  Uniforms & Protective Clothing
01-6250-04  Electricity (CEB, power)
01-6251-04  Water (CWA)
01-6300-07  Rental of Land
01-6301-07  Credit Card Commission and Bank Charges
01-6302-07  Surcharge & Penalties
01-6401-07  Corporate Management Fee
01-6403-07  Estate Shared Cost
01-8001-08  Bank Interest on Loan
01-1005-01  PPE-Cost-Other Equipment (capital purchases)
01-1006-01  PPE-Cost-Furniture and Fittings (capital purchases)

Based on the vendor name, line item descriptions, and the user's context, assign the BEST matching account_code for EACH line item.

Return ONLY a JSON array like:
[
  {{"line_number": 1, "account_code": "01-XXXX-XX", "reason": "Brief explanation"}},
  {{"line_number": 2, "account_code": "01-XXXX-XX", "reason": "Brief explanation"}}
]

Return ONLY valid JSON, no markdown."""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "llama-3.3-70b-versatile",
                        "messages": [
                            {"role": "system", "content": "You are an expert accountant. Return only valid JSON arrays."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1,
                        "max_tokens": 1000
                    }
                )

                if response.status_code != 200:
                    raise HTTPException(status_code=502, detail=f"AI service error: {response.status_code}")

                import re as re_mod
                result = response.json()
                ai_content = result["choices"][0]["message"]["content"]
                ai_content = re_mod.sub(r'^```json\s*', '', ai_content)
                ai_content = re_mod.sub(r'\s*```$', '', ai_content)
                classifications = json.loads(ai_content)

        except json.JSONDecodeError:
            raise HTTPException(status_code=502, detail="AI returned invalid response")
        except Exception as e:
            logger.error(f"Reclassify error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

        # Update line items with new account codes
        from src.accounting_engine import lookup_account_name
        updates = []
        for cls in classifications:
            line_num = cls.get("line_number")
            new_code = cls.get("account_code")
            reason = cls.get("reason", "")
            if not line_num or not new_code:
                continue

            for li in line_items:
                if li.line_number == line_num:
                    old_code = li.account_code
                    li.account_code = new_code
                    updates.append({
                        "line_number": line_num,
                        "old_account": old_code,
                        "new_account": new_code,
                        "account_name": lookup_account_name(new_code),
                        "reason": reason,
                        "description": li.description,
                    })
                    break

        # Delete old journal entries and regenerate
        old_entries = db.query(JournalEntryDB).filter(
            JournalEntryDB.invoice_id == invoice_id
        ).all()
        for oe in old_entries:
            db.query(JournalEntryLineDB).filter(
                JournalEntryLineDB.entry_id == oe.entry_id
            ).delete()
            db.delete(oe)

        # Rebuild invoice data for entry generation
        invoice_data = {
            "vendor_name": invoice.vendor_name,
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date,
            "total_amount": invoice.total_amount,
            "tax_total": invoice.tax_total,
            "subtotal": invoice.subtotal,
            "line_items": [
                {
                    "description": li.description,
                    "amount": li.amount,
                    "tax_amount": li.tax_amount,
                    "account_code": li.account_code,
                }
                for li in line_items
            ],
            "suggested_cost_center": invoice.cost_center,
            "project_code": invoice.project_code,
        }

        from src.accounting_engine import generate_accounting_entries
        from src.invoice_engine import generate_entry_id
        new_entries = generate_accounting_entries(invoice_id, invoice_data, invoice.invoice_type or "supplier")

        for entry in new_entries:
            je = JournalEntryDB(
                entry_id=entry["entry_id"],
                invoice_id=invoice_id,
                entry_date=entry.get("entry_date"),
                reference=entry.get("reference"),
                description=entry.get("description"),
                total_debit=entry.get("total_debit", 0),
                total_credit=entry.get("total_credit", 0),
                is_balanced=entry.get("is_balanced", True),
                status="draft",
                created_by="reclassify",
            )
            db.add(je)
            for line in entry.get("lines", []):
                jel = JournalEntryLineDB(
                    entry_id=entry["entry_id"],
                    account_code=line.get("account_code"),
                    account_name=line.get("account_name"),
                    description=line.get("description"),
                    debit=line.get("debit", 0),
                    credit=line.get("credit", 0),
                    cost_center=line.get("cost_center"),
                    project_code=line.get("project_code"),
                )
                db.add(jel)

        db.commit()
        # Save classification rules for future learning
        for u in updates:
            if u["new_account"] != "01-6000-04":  # Don't learn the default
                existing = db.query(ClassificationRule).filter(
                    ClassificationRule.vendor_name == invoice.vendor_name,
                    ClassificationRule.account_code == u["new_account"],
                    ClassificationRule.company_id == company['id'],
                ).first()
                if existing:
                    existing.user_context = request.user_context
                    existing.times_used = (existing.times_used or 0) + 1
                    existing.updated_at = datetime.utcnow()
                else:
                    db.add(ClassificationRule(
                        vendor_name=invoice.vendor_name,
                        description_pattern=u.get("description", "")[:200] if u.get("description") else None,
                        account_code=u["new_account"],
                        account_name=u.get("account_name", ""),
                        user_context=request.user_context,
                        source="reclassify",
                        times_used=1,
                        company_id=company['id'],
                    ))
                db.commit()

        logger.info(f"🔄 Reclassified invoice {invoice_id}: {len(updates)} line items updated")
        logger.info(f"📚 Saved {len([u for u in updates if u['new_account'] != '01-6000-04'])} classification rule(s) for future learning")

        return {
            "invoice_id": invoice_id,
            "updates": updates,
            "message": f"{len(updates)} line item(s) reclassified based on your context",
            "user_context": request.user_context,
        }

@app.delete("/invoices/{invoice_id}")
async def delete_invoice(invoice_id: str, company: dict = Depends(get_current_company)):
    """Delete an invoice (only if draft or pending)"""
    with get_db() as db:
        invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id, Invoice.company_id == company['id']).first()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        
        if invoice.status in ("posted", "paid"):
            raise HTTPException(status_code=400, detail="Cannot delete posted or paid invoices")
        
        db.delete(invoice)
        db.commit()
        
        if invoice_id in results_store:
            del results_store[invoice_id]
        
        return {"message": f"Invoice {invoice_id} deleted"}


# ─── Admin / Reset ────────────────────────────────────────

class ResetConfirmRequest(PydanticBaseModel):
    confirm: bool = False


@app.post("/admin/reset")
async def reset_all_data(
    request: ResetConfirmRequest,
    company: dict = Depends(get_current_company),
    user: dict = Depends(get_current_user),
):
    """Delete ALL invoices, line items and journal entries for the current company, plus their uploaded documents.
    Chart of accounts and learned classification rules are preserved.
    Admin only."""
    if user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required to reset data")
    if not request.confirm:
        raise HTTPException(status_code=400, detail='Confirmation required: pass {"confirm": true}')

    with get_db() as db:
        invoice_count = db.query(Invoice).filter(Invoice.company_id == company['id']).count()
        entry_count = db.query(JournalEntryDB).filter(JournalEntryDB.company_id == company['id']).count()
        source_files = [row[0] for row in db.query(Invoice.source_file).filter(Invoice.company_id == company['id']).all()]

        # Delete children first, scoped by company
        entry_ids = [row[0] for row in db.query(JournalEntryDB.entry_id).filter(JournalEntryDB.company_id == company['id']).all()]
        if entry_ids:
            db.query(JournalEntryLineDB).filter(JournalEntryLineDB.entry_id.in_(entry_ids)).delete(synchronize_session=False)
        db.query(JournalEntryDB).filter(JournalEntryDB.company_id == company['id']).delete(synchronize_session=False)

        invoice_ids = [row[0] for row in db.query(Invoice.invoice_id).filter(Invoice.company_id == company['id']).all()]
        if invoice_ids:
            db.query(InvoiceLineItemDB).filter(InvoiceLineItemDB.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
        db.query(Invoice).filter(Invoice.company_id == company['id']).delete(synchronize_session=False)
        db.commit()

    # Remove uploaded documents that belonged to the deleted invoices
    safe_dirs = {upload_directory.resolve(), (Path.cwd() / "temp_uploads").resolve()}
    files_removed = 0
    for rel_path in source_files:
        if not rel_path:
            continue
        p = Path(rel_path)
        if not p.is_absolute():
            p = Path.cwd() / p
        try:
            if p.resolve().parent in safe_dirs and p.exists():
                p.unlink()
                files_removed += 1
        except OSError:
            logger.warning(f"Could not remove uploaded file: {p}")

    logger.info(f"Reset complete for {company['name']}: {invoice_count} invoices, {entry_count} journal entries, {files_removed} files removed")
    return {
        "message": f"All invoice records and journal entries deleted for {company['name']}",
        "invoices_deleted": invoice_count,
        "journal_entries_deleted": entry_count,
        "files_removed": files_removed,
    }


# ─── Accounting Entries ───────────────────────────────────

@app.get("/accounting/entries")
async def list_journal_entries(
    status: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    company: dict = Depends(get_current_company),
):
    """List all journal entries"""
    with get_db() as db:
        query = db.query(JournalEntryDB).filter(JournalEntryDB.company_id == company['id']).order_by(JournalEntryDB.created_at.desc())
        
        if status:
            query = query.filter(JournalEntryDB.status == status)
        
        total = query.count()
        entries = query.offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "entries": [
                {
                    "entry_id": e.entry_id,
                    "invoice_id": e.invoice_id,
                    "entry_date": e.entry_date,
                    "reference": e.reference,
                    "description": e.description,
                    "total_debit": e.total_debit,
                    "total_credit": e.total_credit,
                    "is_balanced": e.is_balanced,
                    "status": e.status,
                    "currency": e.invoice.currency if e.invoice else "MUR",
                    "posted_by": e.posted_by,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                    "lines": [
                        {
                            "account_code": l.account_code,
                            "account_name": l.account_name,
                            "description": l.description,
                            "debit": l.debit,
                            "credit": l.credit,
                        }
                        for l in e.lines
                    ]
                }
                for e in entries
            ],
        }


@app.post("/accounting/entries/{entry_id}/post")
async def post_journal_entry(
    entry_id: str,
    company: dict = Depends(get_current_company),
    user: dict = Depends(get_current_user),
):
    """Post a journal entry (make it permanent)"""
    with get_db() as db:
        entry = db.query(JournalEntryDB).filter(JournalEntryDB.entry_id == entry_id, JournalEntryDB.company_id == company['id']).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Journal entry not found")
        
        if entry.status == "posted":
            raise HTTPException(status_code=400, detail="Entry already posted")
        
        # Maker/checker: the user who approved the invoice cannot post the entry
        if company.get('maker_checker_enabled') and entry.invoice:
            if entry.invoice.approved_by and entry.invoice.approved_by == user['id']:
                raise HTTPException(
                    status_code=403,
                    detail="Maker/checker: You approved this invoice and cannot post the journal entry. Another user must post it."
                )

        # Validate before posting
        entry_dict = {
            "lines": [
                {"account_code": l.account_code, "debit": l.debit, "credit": l.credit}
                for l in entry.lines
            ]
        }
        validation = validate_journal_entry(entry_dict)
        if not validation["is_valid"]:
            raise HTTPException(status_code=400, detail=f"Validation failed: {validation['issues']}")
        
        entry.status = "posted"
        entry.posted_by = user['id']
        db.commit()
        
        return {"entry_id": entry_id, "status": "posted", "message": "Journal entry posted successfully"}


@app.post("/accounting/entries/{entry_id}/reverse")
async def reverse_journal_entry(
    entry_id: str,
    company: dict = Depends(get_current_company),
    user: dict = Depends(get_current_user),
):
    """Create a reversing entry"""
    with get_db() as db:
        original = db.query(JournalEntryDB).filter(JournalEntryDB.entry_id == entry_id, JournalEntryDB.company_id == company['id']).first()
        if not original:
            raise HTTPException(status_code=404, detail="Journal entry not found")
        
        # Maker/checker: the user who posted cannot reverse
        if company.get('maker_checker_enabled'):
            if original.posted_by and original.posted_by == user['id']:
                raise HTTPException(
                    status_code=403,
                    detail="Maker/checker: You posted this entry and cannot reverse it. Another user must reverse it."
                )

        from src.invoice_engine import generate_entry_id
        reversal_id = generate_entry_id()
        
        reversal = JournalEntryDB(
            entry_id=reversal_id,
            invoice_id=original.invoice_id,
            entry_date=datetime.now().strftime("%Y-%m-%d"),
            reference=f"REV-{original.reference}",
            description=f"Reversal of {original.entry_id}: {original.description}",
            total_debit=original.total_credit,
            total_credit=original.total_debit,
            is_balanced=True,
            status="draft",
            created_by="system",
            company_id=company['id'],
        )
        db.add(reversal)
        
        for line in original.lines:
            rev_line = JournalEntryLineDB(
                entry_id=reversal_id,
                account_code=line.account_code,
                account_name=line.account_name,
                description=f"Reversal: {line.description}",
                debit=line.credit,  # Swap
                credit=line.debit,  # Swap
                cost_center=line.cost_center,
                project_code=line.project_code,
            )
            db.add(rev_line)
        
        original.status = "reversed"
        db.commit()
        
        return {
            "original_entry_id": entry_id,
            "reversal_entry_id": reversal_id,
            "message": "Reversal entry created"
        }


# ─── Chart of Accounts ───────────────────────────────────



@app.get("/accounting/classification-rules")
async def list_classification_rules(company: dict = Depends(get_current_company)):
    """List all learned classification rules"""
    with get_db() as db:
        rules = db.query(ClassificationRule).filter(
            ClassificationRule.company_id == company['id']
        ).order_by(
            ClassificationRule.times_used.desc(),
            ClassificationRule.updated_at.desc()
        ).all()
        return {
            "total": len(rules),
            "rules": [
                {
                    "id": r.id,
                    "vendor_name": r.vendor_name,
                    "description_pattern": r.description_pattern,
                    "account_code": r.account_code,
                    "account_name": r.account_name,
                    "user_context": r.user_context,
                    "source": r.source,
                    "times_used": r.times_used,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                }
                for r in rules
            ]
        }


@app.delete("/accounting/classification-rules/{rule_id}")
async def delete_classification_rule(rule_id: int, company: dict = Depends(get_current_company)):
    """Delete a learned classification rule"""
    with get_db() as db:
        rule = db.query(ClassificationRule).filter(
            ClassificationRule.id == rule_id,
            ClassificationRule.company_id == company['id'],
        ).first()
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        db.delete(rule)
        db.commit()
        return {"message": f"Rule deleted: {rule.vendor_name} → {rule.account_code}"}

@app.get("/accounting/chart-of-accounts")
async def get_chart_of_accounts(category: Optional[str] = None):
    """Get the chart of accounts"""
    with get_db() as db:
        query = db.query(ChartOfAccountsDB).filter(ChartOfAccountsDB.is_active == True)
        if category:
            query = query.filter(ChartOfAccountsDB.category == category)
        accounts = query.order_by(ChartOfAccountsDB.code).all()
        
        return {
            "total": len(accounts),
            "accounts": [
                {
                    "code": a.code,
                    "name": a.name,
                    "category": a.category,
                    "parent_code": a.parent_code,
                    "description": a.description,
                }
                for a in accounts
            ]
        }




@app.get("/accounting/export/excel")
async def export_journal_entries_excel(
    status: Optional[str] = "posted",
    company: dict = Depends(get_current_company),
):
    """Export journal entries to Excel. Defaults to posted entries only."""
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    import tempfile

    with get_db() as db:
        query = db.query(JournalEntryDB).filter(JournalEntryDB.company_id == company['id']).order_by(JournalEntryDB.entry_date.asc(), JournalEntryDB.created_at.asc())
        if status:
            query = query.filter(JournalEntryDB.status == status)
        entries = query.all()

        if not entries:
            raise HTTPException(status_code=404, detail="No journal entries found to export")

        wb = openpyxl.Workbook()

        # --- Sheet 1: Journal Entries Detail ---
        ws = wb.active
        ws.title = "Journal Entries"

        # Styles
        header_font = Font(name="Arial", bold=True, size=11, color="FFFFFF")
        header_fill = PatternFill("solid", fgColor="1B4332")
        data_font = Font(name="Arial", size=10)
        accent_font = Font(name="Arial", size=10, color="1B7A43")
        debit_font = Font(name="Arial", size=10, color="C0392B")
        credit_font = Font(name="Arial", size=10, color="27AE60")
        total_font = Font(name="Arial", size=10, bold=True)
        total_fill = PatternFill("solid", fgColor="F0F4F0")
        border = Border(
            bottom=Side(style="thin", color="D5D5D5")
        )
        currency_fmt = '#,##0.00'

        # Title
        ws.merge_cells("A1:G1")
        ws["A1"] = "MC Golf - Journal Entries Export"
        ws["A1"].font = Font(name="Arial", bold=True, size=14, color="1B4332")
        ws["A2"] = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        ws["A2"].font = Font(name="Arial", size=9, color="888888")
        ws["A3"] = f"Filter: {status or 'All'} | Total entries: {len(entries)}"
        ws["A3"].font = Font(name="Arial", size=9, color="888888")

        # Headers
        headers = ["Entry ID", "Date", "Vendor / Reference", "Account Code", "Account Name", "Description", "Debit", "Credit"]
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=5, column=col, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")

        row = 6
        grand_debit = 0
        grand_credit = 0

        for entry in entries:
            # Get vendor name from related invoice
            vendor = ""
            if entry.invoice:
                vendor = entry.invoice.vendor_name or ""

            entry_start_row = row
            for line in entry.lines:
                ws.cell(row=row, column=1, value=entry.entry_id).font = accent_font
                ws.cell(row=row, column=2, value=entry.entry_date).font = data_font
                ws.cell(row=row, column=3, value=vendor or entry.reference or "").font = data_font
                ws.cell(row=row, column=4, value=line.account_code).font = Font(name="Consolas", size=10)
                ws.cell(row=row, column=5, value=line.account_name).font = data_font
                ws.cell(row=row, column=6, value=line.description or "").font = data_font

                debit_cell = ws.cell(row=row, column=7, value=line.debit if line.debit > 0 else None)
                debit_cell.font = debit_font
                debit_cell.number_format = currency_fmt

                credit_cell = ws.cell(row=row, column=8, value=line.credit if line.credit > 0 else None)
                credit_cell.font = credit_font
                credit_cell.number_format = currency_fmt

                for c in range(1, 9):
                    ws.cell(row=row, column=c).border = border

                grand_debit += line.debit or 0
                grand_credit += line.credit or 0
                row += 1

            # Entry subtotal row
            ws.cell(row=row, column=6, value=f"Entry Total ({entry.entry_id})").font = total_font
            ws.cell(row=row, column=6).alignment = Alignment(horizontal="right")
            sub_debit = ws.cell(row=row, column=7, value=entry.total_debit)
            sub_debit.font = total_font
            sub_debit.number_format = currency_fmt
            sub_debit.fill = total_fill
            sub_credit = ws.cell(row=row, column=8, value=entry.total_credit)
            sub_credit.font = total_font
            sub_credit.number_format = currency_fmt
            sub_credit.fill = total_fill
            row += 1  # blank row separator

        # Grand total
        row += 1
        ws.cell(row=row, column=6, value="GRAND TOTAL").font = Font(name="Arial", bold=True, size=11)
        ws.cell(row=row, column=6).alignment = Alignment(horizontal="right")
        gt_debit = ws.cell(row=row, column=7, value=grand_debit)
        gt_debit.font = Font(name="Arial", bold=True, size=11, color="C0392B")
        gt_debit.number_format = currency_fmt
        gt_credit = ws.cell(row=row, column=8, value=grand_credit)
        gt_credit.font = Font(name="Arial", bold=True, size=11, color="27AE60")
        gt_credit.number_format = currency_fmt

        # Column widths
        widths = [22, 12, 25, 14, 25, 45, 15, 15]
        for i, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w

        ws.sheet_view.showGridLines = False
        ws.freeze_panes = "A6"

        # --- Sheet 2: Summary by Account ---
        ws2 = wb.create_sheet("Summary by Account")
        ws2.merge_cells("A1:E1")
        ws2["A1"] = "Journal Entries Summary by Account"
        ws2["A1"].font = Font(name="Arial", bold=True, size=14, color="1B4332")

        summary_headers = ["Account Code", "Account Name", "Total Debit", "Total Credit", "Net"]
        for col, h in enumerate(summary_headers, 1):
            cell = ws2.cell(row=3, column=col, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        # Aggregate by account
        account_totals = {}
        for entry in entries:
            for line in entry.lines:
                key = (line.account_code or "", line.account_name or "")
                if key not in account_totals:
                    account_totals[key] = {"debit": 0, "credit": 0}
                account_totals[key]["debit"] += line.debit or 0
                account_totals[key]["credit"] += line.credit or 0

        srow = 4
        for (code, name), totals in sorted(account_totals.items()):
            ws2.cell(row=srow, column=1, value=code).font = Font(name="Consolas", size=10)
            ws2.cell(row=srow, column=2, value=name).font = data_font
            d = ws2.cell(row=srow, column=3, value=totals["debit"])
            d.font = debit_font
            d.number_format = currency_fmt
            c = ws2.cell(row=srow, column=4, value=totals["credit"])
            c.font = credit_font
            c.number_format = currency_fmt
            net = ws2.cell(row=srow, column=5, value=totals["debit"] - totals["credit"])
            net.font = data_font
            net.number_format = currency_fmt
            for col in range(1, 6):
                ws2.cell(row=srow, column=col).border = border
            srow += 1

        ws2.column_dimensions["A"].width = 16
        ws2.column_dimensions["B"].width = 30
        ws2.column_dimensions["C"].width = 15
        ws2.column_dimensions["D"].width = 15
        ws2.column_dimensions["E"].width = 15
        ws2.sheet_view.showGridLines = False
        ws2.freeze_panes = "A4"

        # Save to temp file
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx", dir="temp_uploads")
        wb.save(tmp.name)
        tmp.close()

        filename = f"MC_Golf_Journal_Entries_{status or 'all'}_{datetime.now().strftime('%Y%m%d')}.xlsx"
        return FileResponse(
            tmp.name,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=filename
        )

@app.get("/accounting/export/sage200")
async def export_journal_entries_sage200(
    status: Optional[str] = "posted",
    transaction_type: str = "JL",
    company: dict = Depends(get_current_company),
):
    """Export journal entries as a Sage 200 Evolution GL Journal Batch CSV.

    Produces a single consolidated CSV file ready for import via:
    General Ledger | Transactions | Journal Batches | New Batch | Batch | Import

    Query params:
        status           - entry status filter (default 'posted')
        transaction_type - Sage Transaction Type code (default 'JL'; adjust to
                           match the customer's Transaction Types under
                           Maintenance | Maintenance | Transaction Types)
    """
    import csv
    import tempfile
    import re

    def clean_text(value: str, max_len: int = 100) -> str:
        """Strip Sage-illegal characters and whitespace."""
        if not value:
            return ""
        value = str(value).strip()
        value = re.sub(r"[,;:'\"<>*&$@/\\()]", "", value)
        value = re.sub(r"\s+", " ", value)
        return value[:max_len]

    def format_date(date_str: str) -> str:
        """Convert YYYY-MM-DD (or similar) to dd/mm/yyyy for Sage."""
        if not date_str:
            return ""
        try:
            dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return date_str

    def fmt_amount(value: float) -> str:
        """Format to 2 decimal places, no thousands separator."""
        return f"{float(value or 0):.2f}"

    tmp = tempfile.NamedTemporaryFile(
        delete=False, suffix=".csv", dir="temp_uploads", mode="w", newline="", encoding="utf-8"
    )
    writer = csv.writer(tmp)

    # Header row — Sage 200 Evolution GL Journal Batch minimum columns
    writer.writerow([
        "Date",
        "AccountCode",
        "TransactionType",
        "Reference",
        "Description",
        "Debit",
        "Credit",
    ])

    with get_db() as db:
        query = db.query(JournalEntryDB).filter(JournalEntryDB.company_id == company['id']).order_by(
            JournalEntryDB.entry_date.asc(), JournalEntryDB.created_at.asc()
        )
        if status:
            query = query.filter(JournalEntryDB.status == status)
        entries = query.all()

        if not entries:
            tmp.close()
            os.unlink(tmp.name)
            raise HTTPException(status_code=404, detail="No journal entries found to export")

        for entry in entries:
            ref = clean_text(entry.reference or (entry.invoice.invoice_number if entry.invoice else ""), 30)
            for line in entry.lines:
                writer.writerow([
                    format_date(entry.entry_date),
                    clean_text(line.account_code, 20),
                    transaction_type,
                    ref,
                    clean_text(line.description or "", 100),
                    fmt_amount(line.debit),
                    fmt_amount(line.credit),
                ])

    tmp.close()

    filename = f"Sage200_GL_Journal_{status or 'all'}_{transaction_type}_{datetime.now().strftime('%Y%m%d')}.csv"
    return FileResponse(
        tmp.name,
        media_type="text/csv",
        filename=filename,
    )

@app.get("/accounting/suggest-account")
async def suggest_account(description: str, type: str = "supplier", company: dict = Depends(get_current_company)):
    """AI-powered account code suggestion"""
    code, name = suggest_account_code(description, type, company_id=company['id'])
    return {"account_code": code, "account_name": name, "description": description}


# ─── Dashboard ────────────────────────────────────────────

@app.get("/dashboard/stats")
async def get_dashboard_stats(company: dict = Depends(get_current_company)):
    """Get dashboard statistics"""
    with get_db() as db:
        total = db.query(Invoice).filter(Invoice.company_id == company['id']).count()
        pending = db.query(Invoice).filter(Invoice.company_id == company['id'], Invoice.status == "pending_review").count()
        approved = db.query(Invoice).filter(Invoice.company_id == company['id'], Invoice.status == "approved").count()
        posted = db.query(Invoice).filter(Invoice.company_id == company['id'], Invoice.status == "posted").count()
        
        # Totals by type
        from sqlalchemy import func
        payable = db.query(func.sum(Invoice.total_amount)).filter(
            Invoice.company_id == company['id'],
            Invoice.invoice_type == "supplier",
            Invoice.status.in_(["pending_review", "approved", "posted"])
        ).scalar() or 0.0
        
        receivable = db.query(func.sum(Invoice.total_amount)).filter(
            Invoice.company_id == company['id'],
            Invoice.invoice_type == "client",
            Invoice.status.in_(["pending_review", "approved", "posted"])
        ).scalar() or 0.0
        
        # Recent invoices
        recent = db.query(Invoice).filter(Invoice.company_id == company['id']).order_by(Invoice.created_at.desc()).limit(10).all()
        
        return {
            "total_invoices": total,
            "pending_review": pending,
            "approved": approved,
            "posted": posted,
            "total_payable": round(payable, 2),
            "total_receivable": round(receivable, 2),
            "recent_invoices": [_invoice_to_dict(inv) for inv in recent],
        }


# ─── Helper Functions ─────────────────────────────────────

def _invoice_to_dict(invoice: Invoice) -> Dict[str, Any]:
    """Convert Invoice ORM object to dict"""
    return {
        "invoice_id": invoice.invoice_id,
        "invoice_type": invoice.invoice_type,
        "status": invoice.status,
        "vendor_name": invoice.vendor_name,
        "invoice_number": invoice.invoice_number,
        "invoice_date": invoice.invoice_date,
        "due_date": invoice.due_date,
        "currency": invoice.currency,
        "subtotal": invoice.subtotal,
        "tax_total": invoice.tax_total,
        "total_amount": invoice.total_amount,
        "project_code": invoice.project_code,
        "cost_center": invoice.cost_center,
        "confidence_score": invoice.confidence_score,
        "approved_by": invoice.approved_by,
        "posted_by": invoice.posted_by,
        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        "updated_at": invoice.updated_at.isoformat() if invoice.updated_at else None,
        "has_document": bool(invoice.source_file and Path(invoice.source_file).exists()),
    }


def _save_invoice_to_db(result: Dict, invoice_type: str, file_path: Optional[str], project_code: Optional[str], cost_center: Optional[str], company_id: str = None):
    """Save processed invoice and its entries to the database"""
    extracted = result.get("extracted_data", {})
    invoice_id = result["invoice_id"]
    
    with get_db() as db:
        invoice = Invoice(
            invoice_id=invoice_id,
            invoice_type=invoice_type,
            status=result.get("status", "pending_review"),
            vendor_name=extracted.get("vendor_name") or "Unknown Vendor",
            vendor_address=extracted.get("vendor_address"),
            vendor_brn=extracted.get("vendor_brn"),
            vendor_vat=extracted.get("vendor_vat"),
            invoice_number=extracted.get("invoice_number") or "N/A",
            invoice_date=extracted.get("invoice_date"),
            due_date=extracted.get("due_date"),
            purchase_order=extracted.get("purchase_order"),
            currency=extracted.get("currency", "MUR"),
            subtotal=extracted.get("subtotal", 0.0),
            tax_total=extracted.get("tax_total", 0.0),
            total_amount=extracted.get("total_amount", 0.0),
            payment_terms=extracted.get("payment_terms"),
            notes=extracted.get("notes"),
            project_code=project_code,
            cost_center=cost_center,
            confidence_score=extracted.get("confidence_score", 0.0),
            raw_text=extracted.get("raw_text", "")[:5000],
            ai_analysis=json.dumps(extracted.get("ai_analysis")) if extracted.get("ai_analysis") else None,
            source_file=file_path,
            company_id=company_id,
        )
        db.add(invoice)
        
        # Save line items
        line_items = extracted.get("line_items", [])
        for i, item in enumerate(line_items):
            if isinstance(item, dict):
                li = InvoiceLineItemDB(
                    invoice_id=invoice_id,
                    line_number=item.get("line_number", i + 1),
                    description=item.get("description", ""),
                    quantity=item.get("quantity", 1),
                    unit_price=item.get("unit_price", 0),
                    amount=item.get("amount", 0),
                    tax_rate=item.get("tax_rate", 15.0),
                    tax_amount=item.get("tax_amount", 0),
                    account_code=item.get("account_code") or suggest_account_code(item.get("description", ""), invoice_type, company_id=company_id)[0],
                    cost_center=cost_center,
                    project_code=project_code,
                )
                db.add(li)
        
        # Save journal entries
        for entry in result.get("suggested_entries", []):
            je = JournalEntryDB(
                entry_id=entry["entry_id"],
                invoice_id=invoice_id,
                entry_date=entry.get("entry_date"),
                reference=entry.get("reference"),
                description=entry.get("description"),
                total_debit=entry.get("total_debit", 0),
                total_credit=entry.get("total_credit", 0),
                is_balanced=entry.get("is_balanced", True),
                status="draft",
                created_by=entry.get("created_by", "system"),
                company_id=company_id,
            )
            db.add(je)
            
            for line in entry.get("lines", []):
                jel = JournalEntryLineDB(
                    entry_id=entry["entry_id"],
                    account_code=line.get("account_code"),
                    account_name=line.get("account_name"),
                    description=line.get("description"),
                    debit=line.get("debit", 0),
                    credit=line.get("credit", 0),
                    cost_center=line.get("cost_center"),
                    project_code=line.get("project_code"),
                )
                db.add(jel)
        
        db.commit()
        logger.info(f"💾 Saved invoice {invoice_id} to database")
