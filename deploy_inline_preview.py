#!/usr/bin/env python3
"""
Inline Document Preview - FinnPayments
=======================================
Replaces iframe PDF viewer with rendered image previews.
1. Backend: GET /invoices/{id}/document/preview - returns page images as base64
2. Frontend: Renders pages as <img> tags with page navigation
"""

# ============================================================
# PATCH 1: api.py - Add preview endpoint
# ============================================================

file = "/home/administrator/finnpayments/src/api.py"
with open(file, "r") as f:
    content = f.read()

preview_endpoint = '''

@app.get("/invoices/{invoice_id}/document/preview")
async def get_invoice_document_preview(invoice_id: str, page: int = Query(0, ge=0)):
    """Return invoice document pages as base64 images for inline viewing."""
    import base64
    from io import BytesIO

    with get_db() as db:
        invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
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

'''

if "document/preview" in content:
    print("✅ Preview endpoint already exists")
else:
    # Insert after the document endpoint, or before the delete endpoint
    marker = '@app.delete("/invoices/{invoice_id}")'
    if marker in content:
        content = content.replace(marker, preview_endpoint + marker)
        print("✅ Added /invoices/{id}/document/preview endpoint")
    else:
        # Fallback
        marker2 = '@app.get("/accounting/entries")'
        if marker2 in content:
            content = content.replace(marker2, preview_endpoint + marker2)
            print("✅ Added preview endpoint (alt location)")

with open(file, "w") as f:
    f.write(content)
print(f"✅ Saved {file}")


# ============================================================
# PATCH 2: api.js - Add preview fetch function
# ============================================================

file2 = "/home/administrator/finnpayments/frontend/src/services/api.js"
with open(file2, "r") as f:
    content2 = f.read()

if "getInvoiceDocumentPreview" not in content2:
    content2 += '''

// ─── Document Preview ────────────────────────────────────
export const getInvoiceDocumentPreview = async (invoiceId, page = 0) => {
  const base = import.meta.env.VITE_API_URL || 'http://localhost:8001';
  const response = await fetch(`${base}/invoices/${invoiceId}/document/preview?page=${page}`);
  if (!response.ok) throw new Error('Preview not available');
  return response.json();
};
'''
    print("✅ Added getInvoiceDocumentPreview to api.js")
else:
    print("✅ Already exists in api.js")

with open(file2, "w") as f:
    f.write(content2)
print(f"✅ Saved {file2}")


# ============================================================
# PATCH 3: App.jsx - Replace iframe with image viewer
# ============================================================

file3 = "/home/administrator/finnpayments/frontend/src/App.jsx"
with open(file3, "r") as f:
    content3 = f.read()

# 3a. Add import
if "getInvoiceDocumentPreview" not in content3:
    if "getInvoiceDocumentUrl" in content3:
        content3 = content3.replace(
            "getInvoiceDocumentUrl",
            "getInvoiceDocumentUrl,\n  getInvoiceDocumentPreview",
            1
        )
    elif "exportJournalEntriesExcel" in content3:
        content3 = content3.replace(
            "exportJournalEntriesExcel",
            "exportJournalEntriesExcel,\n  getInvoiceDocumentPreview",
            1
        )
    else:
        content3 = content3.replace(
            "checkHealth",
            "checkHealth,\n  getInvoiceDocumentPreview",
            1
        )
    print("✅ Added getInvoiceDocumentPreview import")

# 3b. Replace the iframe-based Source Document section with image viewer
old_viewer = '''      {inv.has_document && (
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
      )}'''

new_viewer = '''      {inv.has_document && <DocumentPreview invoiceId={invoiceId} />}'''

if "DocumentPreview invoiceId" in content3:
    print("✅ DocumentPreview component reference already exists")
elif old_viewer in content3:
    content3 = content3.replace(old_viewer, new_viewer)
    print("✅ Replaced iframe viewer with DocumentPreview component")
elif "inv.has_document" in content3:
    # Viewer exists but with slightly different formatting
    # Replace any has_document block
    import re
    pattern = r'\{inv\.has_document && \([\s\S]*?<\/iframe>[\s\S]*?\)}'
    if re.search(pattern, content3):
        content3 = re.sub(pattern, '{inv.has_document && <DocumentPreview invoiceId={invoiceId} />}', content3)
        print("✅ Replaced iframe viewer (regex) with DocumentPreview")
    else:
        print("⚠️ has_document block found but couldn't replace - check manually")
else:
    # No viewer at all yet - add it before detail-grid
    detail_grid = '      <div className="detail-grid">'
    if detail_grid in content3:
        content3 = content3.replace(
            detail_grid,
            '      {inv.has_document && <DocumentPreview invoiceId={invoiceId} />}\n\n' + detail_grid,
            1  # only first occurrence in InvoiceDetail
        )
        print("✅ Added DocumentPreview reference (no prior viewer)")
    else:
        print("⚠️ Could not find insertion point")

# 3c. Add DocumentPreview component before InvoiceDetail
doc_preview_component = '''
function DocumentPreview({ invoiceId }) {
  const [preview, setPreview] = useState(null);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadPage = useCallback(async (p) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getInvoiceDocumentPreview(invoiceId, p);
      setPreview(data);
      setPage(data.current_page);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [invoiceId]);

  useEffect(() => { loadPage(0); }, [loadPage]);

  return (
    <div className="card">
      <div className="card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>Source Document</h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {preview && preview.total_pages > 1 && (
            <>
              <button className="btn btn-sm" disabled={page <= 0} onClick={() => loadPage(page - 1)}>← Prev</button>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Page {page + 1} of {preview.total_pages}</span>
              <button className="btn btn-sm" disabled={page >= preview.total_pages - 1} onClick={() => loadPage(page + 1)}>Next →</button>
            </>
          )}
          <a href={getInvoiceDocumentUrl(invoiceId)} download className="btn btn-sm">Download</a>
        </div>
      </div>
      <div style={{ padding: 16, background: '#f5f5f0', minHeight: 200, display: 'flex', justifyContent: 'center', alignItems: 'center', borderRadius: '0 0 8px 8px' }}>
        {loading && <div style={{ color: '#666' }}>Loading preview...</div>}
        {error && <div style={{ color: '#c00' }}>Preview not available</div>}
        {!loading && !error && preview && (
          <img
            src={`data:${preview.mime_type};base64,${preview.image}`}
            alt={`Invoice page ${page + 1}`}
            style={{ maxWidth: '100%', maxHeight: 800, boxShadow: '0 2px 12px rgba(0,0,0,0.15)', borderRadius: 4 }}
          />
        )}
      </div>
    </div>
  );
}

'''

if "function DocumentPreview" in content3:
    print("✅ DocumentPreview component already exists")
else:
    # Insert before InvoiceDetail
    content3 = content3.replace(
        "function InvoiceDetail({ invoiceId, onNavigate }) {",
        doc_preview_component + "function InvoiceDetail({ invoiceId, onNavigate }) {"
    )
    print("✅ Added DocumentPreview component")

with open(file3, "w") as f:
    f.write(content3)
print(f"✅ Saved {file3}")


print("\n" + "="*60)
print("INLINE DOCUMENT PREVIEW - DEPLOYMENT COMPLETE")
print("="*60)
print("""
Changes:
  - GET /invoices/{id}/document/preview?page=0
    → Converts PDF pages to PNG via pdf2image/poppler
    → Returns base64 image + total_pages for pagination
    → Also handles image files (PNG/JPG) directly
  - DocumentPreview component with:
    → Rendered page image (no iframe/cross-origin issues)
    → Page navigation (Prev/Next) for multi-page PDFs
    → Download button for original file
    → Loading state and error handling

Requirements on server:
  pip install pdf2image --break-system-packages
  (poppler-utils should already be installed)

Restart:
  sudo fuser -k 3001/tcp 8001/tcp 2>/dev/null; sleep 2
  cd ~/finnpayments && ./start-all.sh
""")
