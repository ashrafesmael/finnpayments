#!/usr/bin/env python3
"""
Invoice Document Viewer - FinnPayments
=======================================
Adds:
1. Backend: GET /invoices/{id}/document endpoint to serve original files
2. Backend: Move uploads to persistent 'uploads/' directory
3. Backend: Add has_document flag to invoice API response
4. Frontend: Document viewer panel in InvoiceDetail page
"""

# ============================================================
# PATCH 1: api.py - Add document serving endpoint + persistent uploads
# ============================================================

file = "/home/administrator/finnpayments/src/api.py"
with open(file, "r") as f:
    content = f.read()

# 1a. Ensure FileResponse import exists
if "FileResponse" not in content:
    content = content.replace(
        "from fastapi.responses import JSONResponse",
        "from fastapi.responses import JSONResponse, FileResponse"
    )
    print("✅ Added FileResponse import")

# 1b. Create persistent uploads directory and update upload path
old_upload_dir = '''upload_directory = Path("temp_uploads")
upload_directory.mkdir(exist_ok=True)'''

new_upload_dir = '''upload_directory = Path("uploads")
upload_directory.mkdir(exist_ok=True)
# Keep temp_uploads for backward compatibility
Path("temp_uploads").mkdir(exist_ok=True)'''

if 'Path("uploads")' in content and "upload_directory" in content:
    print("✅ Upload directory already set to 'uploads/'")
elif old_upload_dir in content:
    content = content.replace(old_upload_dir, new_upload_dir)
    print("✅ Changed upload directory to persistent 'uploads/'")
else:
    print("⚠️ Could not find upload_directory pattern - check manually")

# 1c. Add has_document to _invoice_to_dict
old_dict_end = '''        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        "updated_at": invoice.updated_at.isoformat() if invoice.updated_at else None,
    }'''

new_dict_end = '''        "created_at": invoice.created_at.isoformat() if invoice.created_at else None,
        "updated_at": invoice.updated_at.isoformat() if invoice.updated_at else None,
        "has_document": bool(invoice.source_file and Path(invoice.source_file).exists()),
    }'''

if "has_document" in content:
    print("✅ has_document already in _invoice_to_dict")
else:
    content = content.replace(old_dict_end, new_dict_end)
    print("✅ Added has_document to _invoice_to_dict")

# 1d. Add document serving endpoint after get_invoice
document_endpoint = '''

@app.get("/invoices/{invoice_id}/document")
async def get_invoice_document(invoice_id: str):
    """Serve the original uploaded document for an invoice"""
    with get_db() as db:
        invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
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

'''

if "get_invoice_document" in content:
    print("✅ Document endpoint already exists")
else:
    # Insert after update_invoice_status endpoint
    marker = '@app.delete("/invoices/{invoice_id}")'
    if marker in content:
        content = content.replace(marker, document_endpoint + marker)
        print("✅ Added GET /invoices/{id}/document endpoint")
    else:
        # Fallback: insert before list_journal_entries
        marker2 = '@app.get("/accounting/entries")'
        if marker2 in content:
            content = content.replace(marker2, document_endpoint + marker2)
            print("✅ Added document endpoint (alt location)")
        else:
            print("⚠️ Could not find insertion point for document endpoint")

with open(file, "w") as f:
    f.write(content)
print(f"✅ Saved {file}")


# ============================================================
# PATCH 2: api.js - Add document URL helper
# ============================================================

file2 = "/home/administrator/finnpayments/frontend/src/services/api.js"
with open(file2, "r") as f:
    content2 = f.read()

doc_fn = '''

// ─── Document Viewer ─────────────────────────────────────
export const getInvoiceDocumentUrl = (invoiceId) => {
  const base = import.meta.env.VITE_API_URL || 'http://localhost:8001';
  return `${base}/invoices/${invoiceId}/document`;
};
'''

if "getInvoiceDocumentUrl" in content2:
    print("✅ getInvoiceDocumentUrl already exists in api.js")
else:
    content2 = content2.replace(
        "// ─── Health",
        doc_fn + "// ─── Health"
    )
    print("✅ Added getInvoiceDocumentUrl to api.js")

with open(file2, "w") as f:
    f.write(content2)
print(f"✅ Saved {file2}")


# ============================================================
# PATCH 3: App.jsx - Add import + document viewer in detail
# ============================================================

file3 = "/home/administrator/finnpayments/frontend/src/App.jsx"
with open(file3, "r") as f:
    content3 = f.read()

# 3a. Add import
if "getInvoiceDocumentUrl" not in content3:
    # Try with exportJournalEntriesExcel present
    if "exportJournalEntriesExcel" in content3:
        content3 = content3.replace(
            "exportJournalEntriesExcel",
            "exportJournalEntriesExcel,\n  getInvoiceDocumentUrl",
            1  # only first occurrence
        )
        print("✅ Added getInvoiceDocumentUrl import (after export)")
    else:
        content3 = content3.replace(
            "checkHealth",
            "checkHealth,\n  getInvoiceDocumentUrl",
            1
        )
        print("✅ Added getInvoiceDocumentUrl import (after checkHealth)")
else:
    print("✅ Import already exists")

# 3b. Add DocView icon if not present
if "DocView:" not in content3:
    if "Download: () =>" in content3:
        content3 = content3.replace(
            "  Download: () =>",
            '  DocView: () => <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14,2 14,8 20,8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>,\n  Download: () =>'
        )
        print("✅ Added DocView icon (before Download)")
    elif "Upload: () =>" in content3:
        content3 = content3.replace(
            "  Upload: () =>",
            '  DocView: () => <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14,2 14,8 20,8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>,\n  Upload: () =>'
        )
        print("✅ Added DocView icon (before Upload)")
    else:
        print("⚠️ Could not find icon insertion point")

# 3c. Add document viewer panel in InvoiceDetail
# Insert after the btn-group div
old_btn_group_end = '''      <div className="detail-grid">
        <div className="card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>Invoice Details</h3>'''

new_btn_group_end = '''      {inv.has_document && (
        <div className="card">
          <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3>Source Document</h3>
            <a href={getInvoiceDocumentUrl(invoiceId)} target="_blank" rel="noopener noreferrer" className="btn btn-sm">Open in New Tab</a>
          </div>
          <div style={{ padding: 0, background: '#1a1a2e' }}>
            <iframe
              src={getInvoiceDocumentUrl(invoiceId)}
              style={{ width: '100%', height: 600, border: 'none', borderRadius: '0 0 8px 8px' }}
              title="Invoice Document"
            />
          </div>
        </div>
      )}

      <div className="detail-grid">
        <div className="card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 12 }}>Invoice Details</h3>'''

if "Source Document" in content3:
    print("✅ Document viewer already exists in InvoiceDetail")
else:
    if old_btn_group_end in content3:
        content3 = content3.replace(old_btn_group_end, new_btn_group_end)
        print("✅ Added document viewer in InvoiceDetail")
    else:
        print("⚠️ Could not find insertion point for document viewer")

with open(file3, "w") as f:
    f.write(content3)
print(f"✅ Saved {file3}")


# ============================================================
# PATCH 4: Move existing temp_uploads to uploads/
# ============================================================

import shutil, os
temp_dir = "/home/administrator/finnpayments/temp_uploads"
new_dir = "/home/administrator/finnpayments/uploads"
os.makedirs(new_dir, exist_ok=True)

if os.path.isdir(temp_dir):
    moved = 0
    for f in os.listdir(temp_dir):
        src = os.path.join(temp_dir, f)
        dst = os.path.join(new_dir, f)
        if os.path.isfile(src) and not os.path.exists(dst):
            shutil.copy2(src, dst)
            moved += 1
    print(f"✅ Copied {moved} files from temp_uploads/ to uploads/")
else:
    print("ℹ️ No temp_uploads directory found")


print("\n" + "="*60)
print("INVOICE DOCUMENT VIEWER - DEPLOYMENT COMPLETE")
print("="*60)
print("""
Features:
  - GET /invoices/{id}/document - serves original PDF/image inline
  - Embedded PDF viewer in invoice detail page (iframe, 600px tall)
  - "Open in New Tab" button for full-screen viewing
  - has_document flag in API response
  - Uploads now saved to persistent 'uploads/' directory
  - Backward compatible: checks both uploads/ and temp_uploads/

Restart to apply:
  sudo fuser -k 3001/tcp 8001/tcp 2>/dev/null; sleep 2
  cd ~/finnpayments && ./start-all.sh
""")
