#!/usr/bin/env python3
"""
Interactive Account Reclassification - FinnPayments
====================================================
When the system can't determine the correct GL account and defaults to
01-6000-04 (Licences), prompt the user to describe the expense nature,
then use LLM to assign the correct account.

Adds:
1. Backend: POST /invoices/{id}/reclassify endpoint
2. Frontend: Warning banner + context input on invoice detail page
"""

# ============================================================
# PATCH 1: api.py - Add reclassify endpoint
# ============================================================

file = "/home/administrator/finnpayments/src/api.py"
with open(file, "r") as f:
    content = f.read()

# Add BaseModel for request if not imported
if "from pydantic import BaseModel" not in content:
    content = content.replace(
        "from typing import Optional, List, Dict, Any",
        "from typing import Optional, List, Dict, Any\nfrom pydantic import BaseModel as PydanticBaseModel"
    )
    print("✅ Added PydanticBaseModel import")

reclassify_endpoint = '''

class ReclassifyRequest(PydanticBaseModel):
    user_context: str


@app.post("/invoices/{invoice_id}/reclassify")
async def reclassify_invoice(invoice_id: str, request: ReclassifyRequest):
    """
    Reclassify invoice line items using user-provided context.
    Called when the system defaulted to Licences (01-6000-04) and the user
    provides additional context about the nature of the expense.
    """
    import httpx

    with get_db() as db:
        invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")

        line_items = db.query(InvoiceLineItemDB).filter(
            InvoiceLineItemDB.invoice_id == invoice_id
        ).order_by(InvoiceLineItemDB.line_number).all()

        if not line_items:
            raise HTTPException(status_code=400, detail="No line items found")

        # Build context for LLM
        items_text = "\\n".join([
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
                ai_content = re_mod.sub(r'^```json\\s*', '', ai_content)
                ai_content = re_mod.sub(r'\\s*```$', '', ai_content)
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
        logger.info(f"🔄 Reclassified invoice {invoice_id}: {len(updates)} line items updated")

        return {
            "invoice_id": invoice_id,
            "updates": updates,
            "message": f"{len(updates)} line item(s) reclassified based on your context",
            "user_context": request.user_context,
        }

'''

if "reclassify_invoice" in content:
    print("✅ Reclassify endpoint already exists")
else:
    marker = '@app.delete("/invoices/{invoice_id}")'
    if marker in content:
        content = content.replace(marker, reclassify_endpoint + marker)
        print("✅ Added POST /invoices/{id}/reclassify endpoint")
    else:
        content = content.replace("def _save_invoice_to_db", reclassify_endpoint + "\ndef _save_invoice_to_db")
        print("✅ Added reclassify endpoint (alt location)")

with open(file, "w") as f:
    f.write(content)
print(f"✅ Saved {file}")


# ============================================================
# PATCH 2: api.js - Add reclassify function
# ============================================================

file2 = "/home/administrator/finnpayments/frontend/src/services/api.js"
with open(file2, "r") as f:
    content2 = f.read()

if "reclassifyInvoice" not in content2:
    content2 += '''

// ─── Reclassify ──────────────────────────────────────────
export const reclassifyInvoice = async (invoiceId, userContext) => {
  const base = import.meta.env.VITE_API_URL || 'http://localhost:8001';
  const response = await fetch(`${base}/invoices/${invoiceId}/reclassify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_context: userContext }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Reclassification failed');
  }
  return response.json();
};
'''
    print("✅ Added reclassifyInvoice to api.js")
else:
    print("✅ Already exists in api.js")

with open(file2, "w") as f:
    f.write(content2)
print(f"✅ Saved {file2}")


# ============================================================
# PATCH 3: App.jsx - Add import + reclassification UI
# ============================================================

file3 = "/home/administrator/finnpayments/frontend/src/App.jsx"
with open(file3, "r") as f:
    content3 = f.read()

# 3a. Add import
if "reclassifyInvoice" not in content3:
    # Find the last import in the import block and add after it
    if "getInvoiceDocumentPreview" in content3:
        content3 = content3.replace(
            "getInvoiceDocumentPreview",
            "getInvoiceDocumentPreview,\n  reclassifyInvoice",
            1
        )
    elif "getInvoiceDocumentUrl" in content3:
        content3 = content3.replace(
            "getInvoiceDocumentUrl",
            "getInvoiceDocumentUrl,\n  reclassifyInvoice",
            1
        )
    elif "exportJournalEntriesExcel" in content3:
        content3 = content3.replace(
            "exportJournalEntriesExcel",
            "exportJournalEntriesExcel,\n  reclassifyInvoice",
            1
        )
    else:
        content3 = content3.replace(
            "checkHealth",
            "checkHealth,\n  reclassifyInvoice",
            1
        )
    print("✅ Added reclassifyInvoice import")
else:
    print("✅ Import already exists")

# 3b. Add ReclassifyBanner component before InvoiceDetail (or before DocumentPreview)
reclassify_component = '''
function ReclassifyBanner({ invoiceId, lineItems, onReclassified }) {
  const [context, setContext] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const defaultItems = (lineItems || []).filter(li => li.account_code === '01-6000-04');
  if (defaultItems.length === 0 && !result) return null;

  const handleSubmit = async () => {
    if (!context.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await reclassifyInvoice(invoiceId, context);
      setResult(res);
      setTimeout(() => onReclassified(), 1500);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (result) {
    return (
      <div className="card" style={{ borderColor: '#27ae60', borderWidth: 1, borderStyle: 'solid' }}>
        <div style={{ padding: 16 }}>
          <div style={{ color: '#27ae60', fontWeight: 600, marginBottom: 8 }}>✓ {result.message}</div>
          {(result.updates || []).map((u, i) => (
            <div key={i} style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 4 }}>
              Line {u.line_number}: <span className="mono" style={{ color: '#e74c3c', textDecoration: 'line-through' }}>{u.old_account}</span> → <span className="mono" style={{ color: '#27ae60' }}>{u.new_account}</span> {u.account_name} <span style={{ fontSize: 11, fontStyle: 'italic' }}>({u.reason})</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="card" style={{ borderColor: '#f39c12', borderWidth: 1, borderStyle: 'solid' }}>
      <div style={{ padding: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <span style={{ fontSize: 18 }}>⚠️</span>
          <span style={{ fontWeight: 600, color: '#f39c12' }}>Account classification needs your input</span>
        </div>
        <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>
          {defaultItems.length} line item{defaultItems.length > 1 ? 's were' : ' was'} assigned to a default account (Licences).
          Describe the nature of this expense so the system can assign the correct GL account:
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            type="text"
            value={context}
            onChange={e => setContext(e.target.value)}
            placeholder="e.g. Security guard services for shopping mall, IT hosting fees, golf course fertilizer delivery..."
            style={{
              flex: 1, padding: '10px 14px', borderRadius: 6,
              border: '1px solid var(--border)', background: 'var(--bg-card)',
              color: 'var(--text-white)', fontSize: 13,
            }}
            onKeyDown={e => { if (e.key === 'Enter' && !loading) handleSubmit(); }}
          />
          <button
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={loading || !context.trim()}
            style={{ whiteSpace: 'nowrap' }}
          >
            {loading ? 'Classifying...' : 'Reclassify'}
          </button>
        </div>
        {error && <div style={{ color: '#e74c3c', fontSize: 12, marginTop: 8 }}>{error}</div>}
      </div>
    </div>
  );
}

'''

if "function ReclassifyBanner" in content3:
    print("✅ ReclassifyBanner component already exists")
else:
    # Insert before InvoiceDetail or DocumentPreview
    if "function DocumentPreview" in content3:
        content3 = content3.replace(
            "function DocumentPreview",
            reclassify_component + "function DocumentPreview"
        )
    else:
        content3 = content3.replace(
            "function InvoiceDetail({ invoiceId, onNavigate }) {",
            reclassify_component + "function InvoiceDetail({ invoiceId, onNavigate }) {"
        )
    print("✅ Added ReclassifyBanner component")

# 3c. Insert ReclassifyBanner in InvoiceDetail, after btn-group
old_btn_group = '''      <div className="detail-grid">'''
reclassify_insertion = '''      <ReclassifyBanner
        invoiceId={invoiceId}
        lineItems={inv.line_items || []}
        onReclassified={() => getInvoice(invoiceId).then(setInv)}
      />

      <div className="detail-grid">'''

# Only add if not already present, and only replace the FIRST occurrence
# (which is in InvoiceDetail, not UploadResult)
if "ReclassifyBanner" in content3 and "invoiceId={invoiceId}" in content3 and "<ReclassifyBanner" in content3:
    print("✅ ReclassifyBanner already inserted in InvoiceDetail")
else:
    # Find the first <div className="detail-grid"> that appears AFTER "function InvoiceDetail"
    idx_detail = content3.find("function InvoiceDetail({ invoiceId, onNavigate })")
    if idx_detail >= 0:
        idx_grid = content3.find(old_btn_group, idx_detail)
        if idx_grid >= 0:
            content3 = content3[:idx_grid] + reclassify_insertion + content3[idx_grid + len(old_btn_group):]
            print("✅ Inserted ReclassifyBanner in InvoiceDetail")
        else:
            print("⚠️ Could not find detail-grid in InvoiceDetail")
    else:
        print("⚠️ Could not find InvoiceDetail function")

with open(file3, "w") as f:
    f.write(content3)
print(f"✅ Saved {file3}")


print("\n" + "="*60)
print("INTERACTIVE RECLASSIFICATION - DEPLOYMENT COMPLETE")
print("="*60)
print("""
How it works:
  1. When any line item has account_code 01-6000-04 (Licences default),
     a yellow warning banner appears on the invoice detail page
  2. User types a description of the expense nature, e.g.:
     "This is for security guard services at the shopping promenade"
  3. System sends the context + invoice data to LLM with full Chart of Accounts
  4. LLM returns the correct account per line item with reasoning
  5. Line items and journal entries are updated automatically
  6. Green confirmation shows old→new account mapping with explanation

Restart:
  sudo fuser -k 3001/tcp 8001/tcp 2>/dev/null; sleep 2
  cd ~/finnpayments && ./start-all.sh
""")
