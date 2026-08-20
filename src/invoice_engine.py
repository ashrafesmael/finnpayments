"""
FinnPayments - Invoice Processing Engine
Extracts data from uploaded invoices using PDF parsing + AI enhancement.
Mirrors FinnVerify's screening_engine.py architecture.
"""

import os
import re
import json
import time
import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

logger = logging.getLogger("FinnPayments.InvoiceEngine")


def generate_invoice_id() -> str:
    """Generate unique invoice ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    short_uuid = uuid.uuid4().hex[:6].upper()
    return f"FP-{timestamp}-{short_uuid}"


def generate_entry_id() -> str:
    """Generate unique journal entry ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    short_uuid = uuid.uuid4().hex[:4].upper()
    return f"JE-{timestamp}-{short_uuid}"


# ─── PDF Text Extraction ─────────────────────────────────

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using pdfplumber, with OCR fallback for scanned PDFs."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
                # Also try extracting tables
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row:
                            text_parts.append(" | ".join([str(cell) if cell else "" for cell in row]))
        
        full_text = "\n".join(text_parts)
        
        # OCR fallback: if pdfplumber got nothing, the PDF is likely a scanned image
        if len(full_text.strip()) < 50:
            logger.info("📷 PDF appears to be scanned - falling back to OCR")
            full_text = ocr_pdf(file_path)
        
        logger.info(f"📄 Extracted {len(full_text)} chars from PDF")
        return full_text
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        return ""


def ocr_pdf(file_path: str) -> str:
    """Convert PDF pages to images and run Tesseract OCR."""
    try:
        from pdf2image import convert_from_path
        import pytesseract
        
        images = convert_from_path(file_path, dpi=300, first_page=1, last_page=3)
        text_parts = []
        for i, img in enumerate(images):
            text = pytesseract.image_to_string(img)
            if text and text.strip():
                text_parts.append(text)
                logger.info(f"📷 OCR page {i+1}: {len(text)} chars")
        
        return "\n".join(text_parts)
    except Exception as e:
        logger.error(f"OCR fallback error: {e}")
        return ""




def extract_pages_from_pdf(file_path: str) -> list:
    """Extract text per page from PDF. Returns list of page texts."""
    pages = []
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                parts = []
                text = page.extract_text()
                if text:
                    parts.append(text)
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row:
                            parts.append(" | ".join([str(c) if c else "" for c in row]))
                pages.append("\n".join(parts))
    except Exception as e:
        logger.error(f"PDF page extraction error: {e}")
    return pages


def detect_invoice_groups(pages: list) -> list:
    """Detect individual invoices in a multi-page PDF."""
    if len(pages) <= 1:
        return []
    invoice_pattern = re.compile(
        r'(?:INVOICE\s*(?:No\.?|Number|#|Num))\s*[:\-]?\s*([A-Z0-9][\w\-/]{2,20})',
        re.IGNORECASE
    )
    page_invoices = []
    for i, page_text in enumerate(pages):
        matches = invoice_pattern.findall(page_text)
        unique_numbers = list(dict.fromkeys(matches))
        page_invoices.append(unique_numbers)
    all_numbers = set()
    for nums in page_invoices:
        all_numbers.update(nums)
    logger.info(f"Found {len(all_numbers)} unique invoice number(s) across {len(pages)} pages: {all_numbers}")
    if len(all_numbers) <= 1:
        return []
    groups = []
    current_group = []
    current_inv_num = None
    for i, page_text in enumerate(pages):
        nums = page_invoices[i]
        if nums:
            primary_num = nums[0]
            if primary_num != current_inv_num:
                if current_group:
                    groups.append("\n\n--- PAGE BREAK ---\n\n".join(current_group))
                current_group = [page_text]
                current_inv_num = primary_num
            else:
                current_group.append(page_text)
        else:
            if current_group:
                current_group.append(page_text)
            else:
                current_group = [page_text]
    if current_group:
        groups.append("\n\n--- PAGE BREAK ---\n\n".join(current_group))
    logger.info(f"Split into {len(groups)} invoice groups")
    return groups if len(groups) > 1 else []


async def process_multi_invoice_pdf(file_path: str, invoice_type: str = "supplier", company_id: str = None) -> list:
    """Process a PDF containing multiple invoices."""
    pages = extract_pages_from_pdf(file_path)
    groups = detect_invoice_groups(pages)
    if not groups:
        return []
    logger.info(f"Processing {len(groups)} invoices from multi-invoice PDF")
    results = []
    for i, invoice_text in enumerate(groups):
        start_time = time.time()
        invoice_id = generate_invoice_id()
        logger.info(f"Processing invoice {i+1}/{len(groups)}: {invoice_id}")
        regex_result = parse_invoice_with_regex(invoice_text)
        regex_result["raw_text"] = invoice_text
        enhanced_data = await enhance_with_ai(invoice_text, regex_result, company_id=company_id)
        from src.accounting_engine import generate_accounting_entries
        entries = generate_accounting_entries(invoice_id, enhanced_data, invoice_type, company_id=company_id)
        processing_time = time.time() - start_time
        result = {
            "invoice_id": invoice_id,
            "status": "pending_review",
            "extracted_data": enhanced_data,
            "suggested_entries": entries,
            "processing_time": round(processing_time, 2),
            "message": f"Invoice {i+1}/{len(groups)} processed in {processing_time:.1f}s"
        }
        results.append(result)
        logger.info(f"Invoice {invoice_id} ({i+1}/{len(groups)}) processed in {processing_time:.1f}s")
    return results


def extract_text_from_image(file_path: str) -> str:
    """Extract text from image using OCR (Tesseract)"""
    try:
        import pytesseract
        from PIL import Image
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image)
        logger.info(f"🖼️ OCR extracted {len(text)} chars from image")
        return text
    except Exception as e:
        logger.error(f"OCR extraction error: {e}")
        return ""


def extract_text_from_csv(file_path: str) -> str:
    """Read CSV/Excel files as text"""
    try:
        import pandas as pd
        ext = Path(file_path).suffix.lower()
        if ext in ('.csv', '.tsv'):
            df = pd.read_csv(file_path)
        elif ext in ('.xlsx', '.xls'):
            df = pd.read_excel(file_path)
        else:
            return ""
        return df.to_string()
    except Exception as e:
        logger.error(f"Spreadsheet extraction error: {e}")
        return ""


def extract_text(file_path: str) -> str:
    """Route extraction based on file type"""
    ext = Path(file_path).suffix.lower()
    if ext == '.pdf':
        return extract_text_from_pdf(file_path)
    elif ext in ('.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp'):
        return extract_text_from_image(file_path)
    elif ext in ('.csv', '.tsv', '.xlsx', '.xls'):
        return extract_text_from_csv(file_path)
    elif ext in ('.txt', '.doc', '.docx'):
        try:
            with open(file_path, 'r', errors='ignore') as f:
                return f.read()
        except:
            return ""
    return ""


# ─── Regex-Based Invoice Parsing ─────────────────────────

def parse_invoice_with_regex(text: str) -> Dict[str, Any]:
    """
    First-pass extraction using regex patterns.
    Handles common Mauritian invoice formats.
    """
    extracted = {
        "vendor_name": None,
        "vendor_brn": None,
        "vendor_vat": None,
        "invoice_number": None,
        "invoice_date": None,
        "due_date": None,
        "purchase_order": None,
        "currency": "MUR",
        "subtotal": None,
        "tax_total": None,
        "total_amount": None,
        "line_items": [],
        "payment_terms": None,
        "confidence_score": 0.0,
    }
    
    if not text:
        return extracted
    
    # Vendor name - look for common patterns at top of invoice
    # Try "Company Name" before address lines
    lines = [l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 3]
    for line in lines[:8]:
        # Skip common headers and the client/buyer name
        skip_words = ["invoice", "facture", "bill", "date", "order", "ref", "vat registration", 
                       "business registration", "tel:", "email:", "page ", "tax invoice"]
        if any(sw in line.lower() for sw in skip_words):
            continue
        # Skip lines that are mostly numbers or addresses
        if re.match(r"^[\d\s/\-\.]+$", line):
            continue
        # Skip short lines or lines starting with numbers
        if len(line) < 4 or re.match(r"^\d", line):
            continue
        # This is likely the vendor name (first substantial text line)
        extracted["vendor_name"] = line
        break
    
    # Invoice Number patterns
    inv_patterns = [
        r'(?:Invoice|Inv|Bill)\s*(?:No|Number|#|Ref)[\s.:]*([A-Za-z0-9\-/]+)',
        r'(?:Facture)\s*(?:No|Numéro)[\s.:]*([A-Za-z0-9\-/]+)',
        r'INV[\-/]?\d{3,}',
    ]
    for pattern in inv_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            extracted["invoice_number"] = match.group(1) if match.lastindex else match.group(0)
            break
    
    # Date patterns (DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD)
    date_patterns = [
        r'(?:Invoice\s*Date|Date)[\s.:]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})',
        r'(?:Date)[\s.:]*(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})',
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            extracted["invoice_date"] = match.group(1)
            break
    
    # Due date
    due_match = re.search(r'(?:Due\s*Date|Payment\s*Due|Échéance)[\s.:]*(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})', text, re.IGNORECASE)
    if due_match:
        extracted["due_date"] = due_match.group(1)
    
    # BRN (Business Registration Number - Mauritius)
    brn_match = re.search(r'(?:BRN|Business\s*Reg)[\s.:]*([A-Z]?\d{6,})', text, re.IGNORECASE)
    if brn_match:
        extracted["vendor_brn"] = brn_match.group(1)
    
    # VAT Registration
    vat_match = re.search(r'(?:VAT|TIN|Tax\s*ID)[\s.:]*([A-Z]?\d{6,})', text, re.IGNORECASE)
    if vat_match:
        extracted["vendor_vat"] = vat_match.group(1)
    
    # Currency detection (default MUR for Mauritian invoices)
    if re.search(r'(?:USD|\$\s*\d)', text):
        extracted["currency"] = "USD"
    elif re.search(r'(?:EUR|€)', text):
        extracted["currency"] = "EUR"
    elif re.search(r'(?:GBP|£)', text):
        extracted["currency"] = "GBP"
    elif re.search(r'\bZAR\b', text):
        extracted["currency"] = "ZAR"
    elif re.search(r'(?:Rs\.?|MUR|TOTAL\s*\(Rs\))', text, re.IGNORECASE):
        extracted["currency"] = "MUR"
    
    # Amount patterns - handles Mauritian formats like "533,600.00"
    amount_patterns = {
        "subtotal": r'(?:Sub\s*total|Sous[\s\-]*total|Net\s*Amount|Total\s*\(?Excl\)?)[\s.:]*(?:Rs\.?|MUR|\$|€|£|R)?\s*([\d,]+\.\d{2})',
        "tax_total": r'(?:VAT\s*\(?\d*%?\)?|Tax|TVA|GST)[\s.:]*(?:Rs\.?|MUR|\$|€|£|R)?\s*([\d,]+\.\d{2})',
        "total_amount": r'(?:TOTAL\s*\(?(?:Rs|MUR)?\)?|Grand\s*Total|Total\s*(?:Amount|Due|Incl))[\s.:]*(?:Rs\.?|MUR|\$|€|£|R)?\s*([\d,]+\.\d{2})',
    }
    
    for field, pattern in amount_patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # Take the last match (usually the final total)
            amount_str = matches[-1].replace(",", "")
            try:
                extracted[field] = float(amount_str)
            except ValueError:
                pass
    
    # Purchase Order
    po_match = re.search(r'(?:PO|Purchase\s*Order|P\.O\.)[\s.:]*([A-Za-z0-9\-/]+)', text, re.IGNORECASE)
    if po_match:
        extracted["purchase_order"] = po_match.group(1)
    
    # Payment terms
    terms_match = re.search(r'(?:Payment\s*Terms?|Terms?)[\s.:]*(.{5,50}?)(?:\n|$)', text, re.IGNORECASE)
    if terms_match:
        extracted["payment_terms"] = terms_match.group(1).strip()
    
    # Calculate confidence based on what we found
    found_fields = sum(1 for v in extracted.values() if v is not None and v != [] and v != 0.0)
    extracted["confidence_score"] = round(min(found_fields / 10.0, 1.0), 2)
    
    return extracted


# ─── AI-Enhanced Extraction ──────────────────────────────

async def enhance_with_ai(raw_text: str, regex_result: Dict[str, Any], company_id: str = None) -> Dict[str, Any]:
    """
    Use Groq LLM to enhance invoice data extraction.
    Mirrors FinnVerify's Groq integration pattern.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("⚠️ GROQ_API_KEY not set - skipping AI enhancement")
        return regex_result
    
    try:
        import httpx
        
        # Get learned classification rules for LLM context
        try:
            from src.accounting_engine import get_learned_rules_for_prompt
            learned_rules = get_learned_rules_for_prompt(company_id=company_id)
        except Exception:
            learned_rules = ""

        # Get TDS rates for LLM context
        try:
            from src.database import SessionLocal, TDSRate
            tds_db = SessionLocal()
            tds_rates = tds_db.query(TDSRate).filter(
                TDSRate.company_id == company_id,
                TDSRate.is_active == True
            ).all() if company_id else []
            tds_db.close()
            tds_context = "\nTDS RATES (determine if tax should be deducted at source):\n" + "\n".join(
                f"  {r.payment_type}: {r.rate}%" for r in tds_rates
            ) if tds_rates else ""
        except Exception:
            tds_context = ""

        prompt = f"""You are an expert invoice processing system for a Mauritian property development group.
Analyze this invoice text and extract structured data. Correct any OCR errors.
{learned_rules}
{tds_context}

IMPORTANT RULES:
- Extract the substantive description of what was billed, not table column headers.
- For DISBURSEMENT items, include what the disbursement was for.
- For legal invoices, FEES description must include full case/matter details (party names, court references, case numbers).
- For EVERY line item, assign the best matching GL account_code from the Chart of Accounts below. Use full context: the vendor name, nature of service, line description, and industry to determine the correct account. For example, a law firm invoice = Professional Fees, an IT vendor = ICT Expenses, a security company = Security Fees, an electricity bill = Electricity, etc.
- Determine if TDS (Tax Deducted at Source) applies to this payment based on the nature of the service and the TDS rates above. Set tds_applicable=true and tds_rate to the matching rate if applicable, otherwise false and 0.

CHART OF ACCOUNTS (assign the best account_code per line item):
01-5100-04  Basic Salary_Admin
01-5102-04  Statutory Contribution(Nps&Twef)_Admin
01-5105-04  Staff Travelling Cost_Admin
01-5108-04  Recruitment Cost_Admin
01-5110-04  Training Staff Cost_Admin
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
01-6021-04  Payroll Processing Fee
01-6022-04  Audit Fee
01-6023-04  Secretarial Fee
01-6025-04  Taxation Fee
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

INVOICE TEXT:
{raw_text[:4000]}

PRELIMINARY EXTRACTION (verify and correct):
{json.dumps({k: v for k, v in regex_result.items() if k != 'line_items'}, indent=2)}

Return a JSON object with these fields (use null for missing data):
{{
    "vendor_name": "Company name on invoice",
    "vendor_brn": "Business Registration Number",
    "vendor_vat": "VAT Registration Number",
    "invoice_number": "Invoice reference number",
    "invoice_date": "YYYY-MM-DD format",
    "due_date": "YYYY-MM-DD format",
    "purchase_order": "PO number if present",
    "currency": "MUR/USD/EUR/GBP/ZAR",
    "subtotal": 0.00,
    "tax_total": 0.00,
    "total_amount": 0.00,
    "line_items": [
        {{"line_number": 1, "description": "...", "quantity": 1, "unit_price": 0.00, "amount": 0.00, "tax_rate": 15.0, "tax_amount": 0.00, "account_code": "01-XXXX-XX"}}
    ],
    "payment_terms": "Net 30 etc",
    "suggested_account_code": "Best GL account code for this expense",
    "suggested_cost_center": "If determinable",
    "tds_applicable": false,
    "tds_rate": 0.0,
    "confidence_score": 0.95,
    "notes": "Any observations about this invoice"
}}

Return ONLY valid JSON, no markdown formatting."""

        async with httpx.AsyncClient(timeout=30.0) as client:
            models = ["openai/gpt-oss-120b", "openai/gpt-oss-20b"]
            response = None
            for model in models:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "You are an invoice data extraction specialist. Return only valid JSON."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1,
                        "max_tokens": 2000
                    }
                )
                if response.status_code == 200:
                    break
                logger.warning(f"⚠️ Groq model {model} returned {response.status_code}, trying fallback...")
            
            if response and response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                # Strip markdown code fences if present
                content = re.sub(r'^```json\s*', '', content)
                content = re.sub(r'\s*```$', '', content)
                ai_data = json.loads(content)
                
                # Merge AI results with regex results (AI takes priority)
                for key, value in ai_data.items():
                    if value is not None and value != "" and value != []:
                        regex_result[key] = value
                
                # Boost confidence if AI succeeded
                regex_result["confidence_score"] = max(
                    regex_result.get("confidence_score", 0),
                    ai_data.get("confidence_score", 0.8)
                )
                
                logger.info(f"🤖 AI enhancement successful - confidence: {regex_result['confidence_score']}")
            else:
                logger.warning(f"⚠️ Groq API returned {response.status_code}")
                
    except json.JSONDecodeError as e:
        logger.warning(f"⚠️ AI returned invalid JSON: {e}")
    except Exception as e:
        logger.error(f"❌ AI enhancement error: {e}")
    
    return regex_result


# ─── Main Processing Pipeline ────────────────────────────

async def process_invoice(file_path: str, invoice_type: str = "supplier", company_id: str = None):
    """
    Full invoice processing pipeline.
    Detects multi-invoice PDFs and processes each separately.
    Returns a single dict OR a list of dicts for multi-invoice PDFs.
    """
    start_time = time.time()
    
    # Check for multi-invoice PDF
    ext = Path(file_path).suffix.lower()
    if ext == '.pdf':
        multi_results = await process_multi_invoice_pdf(file_path, invoice_type, company_id=company_id)
        if multi_results:
            logger.info(f"📋 Multi-invoice PDF: {len(multi_results)} invoices detected")
            return multi_results
    
    # Single invoice processing
    invoice_id = generate_invoice_id()
    logger.info(f"📋 Processing invoice: {invoice_id} from {file_path}")
    
    # Step 1: Extract text
    raw_text = extract_text(file_path)
    if not raw_text:
        return {
            "invoice_id": invoice_id,
            "status": "error",
            "message": "Could not extract text from document",
            "processing_time": time.time() - start_time
        }
    
    # Step 2: Regex parsing
    regex_result = parse_invoice_with_regex(raw_text)
    regex_result["raw_text"] = raw_text
    
    # Step 3: AI enhancement
    enhanced_data = await enhance_with_ai(raw_text, regex_result, company_id=company_id)
    
    # Step 4: Generate accounting entries
    from src.accounting_engine import generate_accounting_entries
    entries = generate_accounting_entries(invoice_id, enhanced_data, invoice_type, company_id=company_id)
    
    processing_time = time.time() - start_time
    
    result = {
        "invoice_id": invoice_id,
        "status": "pending_review",
        "extracted_data": enhanced_data,
        "suggested_entries": entries,
        "processing_time": round(processing_time, 2),
        "message": f"Invoice processed in {processing_time:.1f}s with {enhanced_data.get('confidence_score', 0):.0%} confidence"
    }
    
    logger.info(f"✅ Invoice {invoice_id} processed in {processing_time:.1f}s")
    return result
