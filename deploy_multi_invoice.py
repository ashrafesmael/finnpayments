#!/usr/bin/env python3
"""
Multi-Invoice PDF Support for FinnPayments
==========================================
Detects when a PDF contains multiple invoices and processes each separately.

Changes:
1. invoice_engine.py - Add per-page extraction, invoice boundary detection, multi-invoice processing
2. api.py - Upload endpoint handles multiple results
"""

import re

# ============================================================
# PATCH 1: invoice_engine.py - Add multi-invoice functions
# ============================================================

file = "/home/administrator/finnpayments/src/invoice_engine.py"
with open(file, "r") as f:
    content = f.read()

# 1a. Add extract_pages_from_pdf function after extract_text_from_pdf
old_extract = '''def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using pdfplumber. Only reads first 3 pages for invoices."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            max_pages = min(len(pdf.pages), 3)  # Invoice data is on first pages
            logger.info(f"📄 PDF has {len(pdf.pages)} pages, reading first {max_pages}")
            for page in pdf.pages[:max_pages]:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
                # Also try extracting tables
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row:
                            text_parts.append(" | ".join([str(cell) if cell else "" for cell in row]))
        
        full_text = "\\n".join(text_parts)
        logger.info(f"📄 Extracted {len(full_text)} chars from PDF")
        return full_text
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        return ""'''

new_extract = '''def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using pdfplumber. Reads ALL pages."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(file_path) as pdf:
            logger.info(f"📄 PDF has {len(pdf.pages)} pages, reading all")
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row:
                            text_parts.append(" | ".join([str(cell) if cell else "" for cell in row]))
        
        full_text = "\\n".join(text_parts)
        logger.info(f"📄 Extracted {len(full_text)} chars from PDF")
        return full_text
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
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
                pages.append("\\n".join(parts))
    except Exception as e:
        logger.error(f"PDF page extraction error: {e}")
    return pages


def detect_invoice_groups(pages: list) -> list:
    """
    Detect individual invoices in a multi-page PDF.
    Returns list of text strings, one per invoice.
    If only 1 invoice detected, returns empty list (use normal flow).
    """
    if len(pages) <= 1:
        return []
    
    # Find invoice numbers on each page
    invoice_pattern = re.compile(
        r'(?:INVOICE\s*(?:No\.?|Number|#|Num))\s*[:\-]?\s*([A-Z0-9][\w\-/]{2,20})',
        re.IGNORECASE
    )
    
    page_invoices = []
    for i, page_text in enumerate(pages):
        matches = invoice_pattern.findall(page_text)
        # Deduplicate (same invoice number may appear multiple times on same page)
        unique_numbers = list(dict.fromkeys(matches))
        page_invoices.append(unique_numbers)
    
    # Count total unique invoice numbers across all pages
    all_numbers = set()
    for nums in page_invoices:
        all_numbers.update(nums)
    
    logger.info(f"📄 Found {len(all_numbers)} unique invoice number(s) across {len(pages)} pages: {all_numbers}")
    
    if len(all_numbers) <= 1:
        return []  # Single invoice, use normal flow
    
    # Group pages by invoice - each page with a new invoice number starts a new group
    groups = []
    current_group = []
    current_inv_num = None
    
    for i, page_text in enumerate(pages):
        nums = page_invoices[i]
        if nums:
            primary_num = nums[0]
            if primary_num != current_inv_num:
                # New invoice detected
                if current_group:
                    groups.append("\\n\\n--- PAGE BREAK ---\\n\\n".join(current_group))
                current_group = [page_text]
                current_inv_num = primary_num
            else:
                # Continuation of same invoice
                current_group.append(page_text)
        else:
            # No invoice number on this page - continuation of previous
            if current_group:
                current_group.append(page_text)
            else:
                current_group = [page_text]
    
    if current_group:
        groups.append("\\n\\n--- PAGE BREAK ---\\n\\n".join(current_group))
    
    logger.info(f"📄 Split into {len(groups)} invoice groups")
    return groups if len(groups) > 1 else []


async def process_multi_invoice_pdf(file_path: str, invoice_type: str = "supplier") -> list:
    """
    Process a PDF containing multiple invoices.
    Returns list of processing results, one per invoice.
    """
    pages = extract_pages_from_pdf(file_path)
    groups = detect_invoice_groups(pages)
    
    if not groups:
        return []  # Not a multi-invoice PDF
    
    logger.info(f"📋 Processing {len(groups)} invoices from multi-invoice PDF")
    
    results = []
    for i, invoice_text in enumerate(groups):
        start_time = time.time()
        invoice_id = generate_invoice_id()
        
        logger.info(f"📋 Processing invoice {i+1}/{len(groups)}: {invoice_id}")
        
        # Step 2: Regex parsing
        regex_result = parse_invoice_with_regex(invoice_text)
        regex_result["raw_text"] = invoice_text
        
        # Step 3: AI enhancement
        enhanced_data = await enhance_with_ai(invoice_text, regex_result)
        
        # Step 4: Generate accounting entries
        from src.accounting_engine import generate_accounting_entries
        entries = generate_accounting_entries(invoice_id, enhanced_data, invoice_type)
        
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
        logger.info(f"✅ Invoice {invoice_id} ({i+1}/{len(groups)}) processed in {processing_time:.1f}s")
    
    return results'''

if "extract_pages_from_pdf" in content:
    print("✅ extract_pages_from_pdf already exists")
else:
    content = content.replace(old_extract, new_extract)
    print("✅ Added extract_pages_from_pdf, detect_invoice_groups, process_multi_invoice_pdf")


# 1b. Modify process_invoice to detect multi-invoice PDFs
old_process = '''async def process_invoice(file_path: str, invoice_type: str = "supplier") -> Dict[str, Any]:
    """
    Full invoice processing pipeline:
    1. Extract text from document
    2. Parse with regex
    3. Enhance with AI
    4. Generate accounting entries
    """
    start_time = time.time()
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
    enhanced_data = await enhance_with_ai(raw_text, regex_result)
    
    # Step 4: Generate accounting entries
    from src.accounting_engine import generate_accounting_entries
    entries = generate_accounting_entries(invoice_id, enhanced_data, invoice_type)
    
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
    return result'''

new_process = '''async def process_invoice(file_path: str, invoice_type: str = "supplier"):
    """
    Full invoice processing pipeline.
    Detects multi-invoice PDFs and processes each separately.
    Returns a single dict OR a list of dicts for multi-invoice PDFs.
    """
    start_time = time.time()
    
    # Check for multi-invoice PDF
    ext = Path(file_path).suffix.lower()
    if ext == '.pdf':
        multi_results = await process_multi_invoice_pdf(file_path, invoice_type)
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
    enhanced_data = await enhance_with_ai(raw_text, regex_result)
    
    # Step 4: Generate accounting entries
    from src.accounting_engine import generate_accounting_entries
    entries = generate_accounting_entries(invoice_id, enhanced_data, invoice_type)
    
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
    return result'''

if "multi_results = await process_multi_invoice_pdf" in content:
    print("✅ process_invoice multi-invoice detection already exists")
else:
    content = content.replace(old_process, new_process)
    print("✅ Modified process_invoice to detect multi-invoice PDFs")

with open(file, "w") as f:
    f.write(content)
print(f"✅ Saved {file}")


# ============================================================
# PATCH 2: api.py - Upload endpoint handles multiple results
# ============================================================

file2 = "/home/administrator/finnpayments/src/api.py"
with open(file2, "r") as f:
    content2 = f.read()

old_upload = '''    # Process the invoice
    try:
        result = await process_invoice(str(file_path), invoice_type)
    except Exception as e:
        logger.error(f"❌ Processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    
    # Save to database
    try:
        _save_invoice_to_db(result, invoice_type, str(file_path), project_code, cost_center)
    except Exception as e:
        logger.error(f"❌ Database save error: {e}")
    
    # Store in memory
    results_store[result["invoice_id"]] = result
    
    processing_time = time.time() - start_time
    result["processing_time"] = round(processing_time, 2)
    
    return result'''

new_upload = '''    # Process the invoice
    try:
        result = await process_invoice(str(file_path), invoice_type)
    except Exception as e:
        logger.error(f"❌ Processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")
    
    # Handle multi-invoice PDF (result is a list)
    if isinstance(result, list):
        logger.info(f"📋 Multi-invoice upload: {len(result)} invoices detected")
        for r in result:
            try:
                _save_invoice_to_db(r, invoice_type, str(file_path), project_code, cost_center)
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
        _save_invoice_to_db(result, invoice_type, str(file_path), project_code, cost_center)
    except Exception as e:
        logger.error(f"❌ Database save error: {e}")
    
    results_store[result["invoice_id"]] = result
    
    processing_time = time.time() - start_time
    result["processing_time"] = round(processing_time, 2)
    
    return result'''

if "multi_invoice" in content2:
    print("✅ Upload endpoint multi-invoice handling already exists")
else:
    content2 = content2.replace(old_upload, new_upload)
    print("✅ Modified upload endpoint for multi-invoice support")

with open(file2, "w") as f:
    f.write(content2)
print(f"✅ Saved {file2}")


# ============================================================
# PATCH 3: Frontend - Handle multi-invoice response
# ============================================================

file3 = "/home/administrator/finnpayments/frontend/src/App.jsx"
with open(file3, "r") as f:
    content3 = f.read()

# 3a. Add MultiInvoiceResult component before UploadResult
old_upload_result = 'function UploadResult({ result, onNavigate, onReset }) {'
multi_component = '''function MultiInvoiceResult({ result, onNavigate, onReset }) {
  const invoices = result.invoices || [];
  return (
    <div className="animate-fade-in space-y">
      <div className="page-header-back">
        <button className="back-btn" onClick={onReset}><Icons.ArrowLeft /></button>
        <h2 style={{ fontSize: 24, fontWeight: 600, color: 'var(--text-white)' }}>Multi-Invoice Upload</h2>
      </div>
      <div className="success-banner">
        <div>
          <div className="success-banner-text">{result.message}</div>
          <div className="success-banner-sub">{result.count} invoices detected in uploaded PDF</div>
        </div>
      </div>
      <div className="card">
        <div className="card-header"><h3>Invoices Processed</h3></div>
        <table className="data-table">
          <thead><tr><th>#</th><th>Vendor</th><th>Invoice #</th><th>Date</th><th>Total</th><th>Action</th></tr></thead>
          <tbody>{invoices.map((inv, i) => {
            const d = inv.extracted_data || {};
            return (
              <tr key={i}>
                <td className="text-muted">{i + 1}</td>
                <td style={{ fontWeight: 500, color: 'var(--text-white)' }}>{d.vendor_name || 'Unknown'}</td>
                <td className="mono text-sm">{d.invoice_number || '-'}</td>
                <td className="text-muted text-sm">{d.invoice_date || '-'}</td>
                <td className="mono" style={{ color: 'var(--accent)', fontWeight: 600 }}>{fmtCurrency(d.total_amount, d.currency)}</td>
                <td><button className="btn btn-sm" onClick={() => onNavigate('invoice', inv.invoice_id)}>View</button></td>
              </tr>
            );
          })}</tbody>
        </table>
      </div>
      <div style={{ display: 'flex', gap: 12 }}>
        <button className="btn btn-primary" onClick={() => onNavigate('invoices')}>View All Invoices</button>
        <button className="btn" onClick={onReset}>Upload More</button>
      </div>
    </div>
  );
}

function UploadResult({ result, onNavigate, onReset }) {'''

if "MultiInvoiceResult" in content3:
    print("✅ MultiInvoiceResult component already exists")
else:
    content3 = content3.replace(old_upload_result, multi_component)
    print("✅ Added MultiInvoiceResult component")

# 3b. Add multi-invoice check in InvoiceUpload result rendering
old_result_check = '  if (result) return <UploadResult result={result} onNavigate={onNavigate} onReset={() => { setResult(null); setFile(null); }} />;'
new_result_check = '''  if (result && result.multi_invoice) return <MultiInvoiceResult result={result} onNavigate={onNavigate} onReset={() => { setResult(null); setFile(null); }} />;
  if (result) return <UploadResult result={result} onNavigate={onNavigate} onReset={() => { setResult(null); setFile(null); }} />;'''

if "result.multi_invoice" in content3:
    print("✅ Multi-invoice check already exists in InvoiceUpload")
else:
    content3 = content3.replace(old_result_check, new_result_check)
    print("✅ Added multi-invoice result check in InvoiceUpload")

with open(file3, "w") as f:
    f.write(content3)
print(f"✅ Saved {file3}")


print("\n" + "="*60)
print("MULTI-INVOICE PDF SUPPORT - DEPLOYMENT COMPLETE")
print("="*60)
print("""
Changes:
1. extract_text_from_pdf() - now reads ALL pages (not just first 3)
2. extract_pages_from_pdf() - extracts text per page
3. detect_invoice_groups() - finds unique invoice numbers, groups pages
4. process_multi_invoice_pdf() - processes each invoice independently  
5. process_invoice() - auto-detects multi-invoice PDFs
6. upload endpoint - returns {multi_invoice: true, invoices: [...]}
7. Frontend - displays all invoices from multi-invoice upload

Restart to apply:
   sudo fuser -k 3001/tcp 8001/tcp 2>/dev/null; sleep 2
   cd ~/finnpayments && ./start-all.sh
""")
