#!/usr/bin/env python3
"""
Classification Learning - FinnPayments
=======================================
The system learns from reclassifications so future invoices from the same
vendor or with similar descriptions get the correct GL account automatically.

Adds:
1. Database: classification_rules table
2. accounting_engine: check learned rules before keyword fallback
3. api.py: Save rules on reclassify + management endpoint
4. invoice_engine: Inject learned rules into LLM prompt
5. Frontend: Learned rules indicator + management page
"""

# ============================================================
# PATCH 1: database.py - Add ClassificationRule model
# ============================================================

file = "/home/administrator/finnpayments/src/database.py"
with open(file, "r") as f:
    content = f.read()

rule_model = '''

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


'''

if "ClassificationRule" in content:
    print("✅ ClassificationRule model already exists")
else:
    # Insert before init_db
    content = content.replace("def init_db():", rule_model + "def init_db():")
    print("✅ Added ClassificationRule model")

with open(file, "w") as f:
    f.write(content)
print(f"✅ Saved {file}")


# ============================================================
# PATCH 2: accounting_engine.py - Check learned rules first
# ============================================================

file2 = "/home/administrator/finnpayments/src/accounting_engine.py"
with open(file2, "r") as f:
    content2 = f.read()

# Add check_learned_rules function before suggest_account_code
learned_fn = '''def check_learned_rules(vendor_name, description):
    """Check classification_rules table for a matching vendor/description rule."""
    try:
        from src.database import SessionLocal, ClassificationRule
        db = SessionLocal()
        vendor_lower = (vendor_name or "").lower().strip()
        desc_lower = (description or "").lower().strip()

        # Priority 1: Exact vendor name match
        if vendor_lower:
            rules = db.query(ClassificationRule).filter(
                ClassificationRule.vendor_name.isnot(None)
            ).all()
            for rule in rules:
                if rule.vendor_name and rule.vendor_name.lower().strip() == vendor_lower:
                    # Increment usage counter
                    rule.times_used = (rule.times_used or 0) + 1
                    db.commit()
                    db.close()
                    logger.info(f"📚 Learned rule matched: vendor '{vendor_name}' → {rule.account_code}")
                    return (rule.account_code, rule.account_name or rule.account_code)

        # Priority 2: Description pattern match
        if desc_lower:
            rules = db.query(ClassificationRule).filter(
                ClassificationRule.description_pattern.isnot(None)
            ).all()
            for rule in rules:
                if rule.description_pattern and rule.description_pattern.lower() in desc_lower:
                    rule.times_used = (rule.times_used or 0) + 1
                    db.commit()
                    db.close()
                    logger.info(f"📚 Learned rule matched: pattern '{rule.description_pattern}' → {rule.account_code}")
                    return (rule.account_code, rule.account_name or rule.account_code)

        db.close()
    except Exception as e:
        logger.warning(f"⚠️ Learned rules check failed: {e}")
    return None


def get_learned_rules_for_prompt():
    """Get all learned rules formatted for inclusion in LLM prompt."""
    try:
        from src.database import SessionLocal, ClassificationRule
        db = SessionLocal()
        rules = db.query(ClassificationRule).order_by(ClassificationRule.times_used.desc()).limit(50).all()
        db.close()
        if not rules:
            return ""
        lines = ["\\nLEARNED CLASSIFICATIONS (from previous user corrections - use these as strong hints):"]
        for r in rules:
            vendor = r.vendor_name or "any vendor"
            lines.append(f"  {vendor} → {r.account_code} ({r.account_name}) [context: {r.user_context or r.description_pattern}]")
        return "\\n".join(lines)
    except Exception:
        return ""


'''

if "check_learned_rules" in content2:
    print("✅ check_learned_rules already exists")
else:
    # Insert before suggest_account_code
    content2 = content2.replace(
        "def suggest_account_code(description, invoice_type=\"supplier\"):",
        learned_fn + "def suggest_account_code(description, invoice_type=\"supplier\"):"
    )
    print("✅ Added check_learned_rules and get_learned_rules_for_prompt")

# Modify suggest_account_code to check learned rules first
old_suggest = '''def suggest_account_code(description, invoice_type="supplier"):
    desc_lower = description.lower() if description else ""
    keywords = EXPENSE_KEYWORDS if invoice_type in ("supplier", "credit_note") else REVENUE_KEYWORDS
    sorted_keywords = sorted(keywords.keys(), key=len, reverse=True)
    for keyword in sorted_keywords:
        if keyword in desc_lower:
            return keywords[keyword]
    defaults = ACCOUNT_MAPPINGS.get(invoice_type, ACCOUNT_MAPPINGS["supplier"])
    return defaults["default_expense"] if invoice_type in ("supplier", "credit_note") else defaults["default_revenue"]'''

new_suggest = '''def suggest_account_code(description, invoice_type="supplier", vendor_name=None):
    # Priority 1: Check learned classification rules
    learned = check_learned_rules(vendor_name, description)
    if learned:
        return learned

    # Priority 2: Keyword matching
    desc_lower = description.lower() if description else ""
    keywords = EXPENSE_KEYWORDS if invoice_type in ("supplier", "credit_note") else REVENUE_KEYWORDS
    sorted_keywords = sorted(keywords.keys(), key=len, reverse=True)
    for keyword in sorted_keywords:
        if keyword in desc_lower:
            return keywords[keyword]

    # Priority 3: Check learned rules by vendor alone (if description didn't match)
    if vendor_name:
        learned_vendor = check_learned_rules(vendor_name, "")
        if learned_vendor:
            return learned_vendor

    defaults = ACCOUNT_MAPPINGS.get(invoice_type, ACCOUNT_MAPPINGS["supplier"])
    return defaults["default_expense"] if invoice_type in ("supplier", "credit_note") else defaults["default_revenue"]'''

if "vendor_name=None" in content2 and "check_learned_rules" in content2 and "Priority 1: Check learned" in content2:
    print("✅ suggest_account_code already uses learned rules")
else:
    if old_suggest in content2:
        content2 = content2.replace(old_suggest, new_suggest)
        print("✅ Modified suggest_account_code to check learned rules first")
    else:
        print("⚠️ Could not find exact suggest_account_code pattern - check manually")

# Also update the call in generate_accounting_entries to pass vendor_name
old_suggest_call = "acct_code, acct_name = suggest_account_code(desc, invoice_type)"
new_suggest_call = "acct_code, acct_name = suggest_account_code(desc, invoice_type, vendor_name=vendor_name)"

if "vendor_name=vendor_name)" in content2:
    print("✅ suggest_account_code call already passes vendor_name")
else:
    content2 = content2.replace(old_suggest_call, new_suggest_call)
    print("✅ Updated suggest_account_code call to pass vendor_name")

# Update the search_text call too
old_search_call = "acct_code, acct_name = suggest_account_code(search_text, invoice_type)"
new_search_call = "acct_code, acct_name = suggest_account_code(search_text, invoice_type, vendor_name=vendor_name)"

if old_search_call in content2:
    content2 = content2.replace(old_search_call, new_search_call)
    print("✅ Updated search_text suggest call too")

with open(file2, "w") as f:
    f.write(content2)
print(f"✅ Saved {file2}")


# ============================================================
# PATCH 3: api.py - Save rules on reclassify + management endpoint
# ============================================================

file3 = "/home/administrator/finnpayments/src/api.py"
with open(file3, "r") as f:
    content3 = f.read()

# 3a. Add ClassificationRule import
if "ClassificationRule" not in content3:
    content3 = content3.replace(
        "JournalEntryDB, JournalEntryLineDB, ChartOfAccountsDB",
        "JournalEntryDB, JournalEntryLineDB, ChartOfAccountsDB, ClassificationRule"
    )
    print("✅ Added ClassificationRule import")

# 3b. Add rule-saving logic to reclassify endpoint
# Find the success log line in reclassify and insert rule saving before it
old_reclassify_log = '        logger.info(f"🔄 Reclassified invoice {invoice_id}: {len(updates)} line items updated")'

save_rules_code = '''        # Save classification rules for future learning
        for u in updates:
            if u["new_account"] != "01-6000-04":  # Don't learn the default
                # Check if rule already exists for this vendor
                existing = db.query(ClassificationRule).filter(
                    ClassificationRule.vendor_name == invoice.vendor_name,
                    ClassificationRule.account_code == u["new_account"],
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
                    ))
                db.commit()

        logger.info(f"🔄 Reclassified invoice {invoice_id}: {len(updates)} line items updated")
        logger.info(f"📚 Saved {len([u for u in updates if u['new_account'] != '01-6000-04'])} classification rule(s) for future learning")'''

if "classification rule" in content3.lower() and "Save classification rules" in content3:
    print("✅ Rule saving already in reclassify endpoint")
elif old_reclassify_log in content3:
    content3 = content3.replace(old_reclassify_log, save_rules_code)
    print("✅ Added classification rule saving to reclassify endpoint")
else:
    print("⚠️ Could not find reclassify log line - check manually")

# 3c. Add classification rules management endpoint
rules_endpoint = '''

@app.get("/accounting/classification-rules")
async def list_classification_rules():
    """List all learned classification rules"""
    with get_db() as db:
        rules = db.query(ClassificationRule).order_by(
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
async def delete_classification_rule(rule_id: int):
    """Delete a learned classification rule"""
    with get_db() as db:
        rule = db.query(ClassificationRule).filter(ClassificationRule.id == rule_id).first()
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        db.delete(rule)
        db.commit()
        return {"message": f"Rule deleted: {rule.vendor_name} → {rule.account_code}"}

'''

if "classification-rules" in content3:
    print("✅ Classification rules endpoints already exist")
else:
    marker = "@app.get(\"/accounting/chart-of-accounts\")"
    if marker in content3:
        content3 = content3.replace(marker, rules_endpoint + marker)
        print("✅ Added classification rules management endpoints")
    else:
        content3 = content3.replace("def _save_invoice_to_db", rules_endpoint + "\ndef _save_invoice_to_db")
        print("✅ Added rules endpoints (alt location)")

with open(file3, "w") as f:
    f.write(content3)
print(f"✅ Saved {file3}")


# ============================================================
# PATCH 4: invoice_engine.py - Inject learned rules into LLM prompt
# ============================================================

file4 = "/home/administrator/finnpayments/src/invoice_engine.py"
with open(file4, "r") as f:
    content4 = f.read()

# Add learned rules to the AI prompt
old_prompt_start = '''        prompt = f"""You are an expert invoice processing system for a Mauritian property development group.
Analyze this invoice text and extract structured data. Correct any OCR errors.'''

new_prompt_start = '''        # Get learned classification rules for LLM context
        try:
            from src.accounting_engine import get_learned_rules_for_prompt
            learned_rules = get_learned_rules_for_prompt()
        except Exception:
            learned_rules = ""

        prompt = f"""You are an expert invoice processing system for a Mauritian property development group.
Analyze this invoice text and extract structured data. Correct any OCR errors.
{learned_rules}'''

if "get_learned_rules_for_prompt" in content4:
    print("✅ Learned rules already injected into LLM prompt")
elif old_prompt_start in content4:
    content4 = content4.replace(old_prompt_start, new_prompt_start)
    print("✅ Injected learned rules into LLM prompt")
else:
    print("⚠️ Could not find prompt start pattern - check invoice_engine.py manually")

with open(file4, "w") as f:
    f.write(content4)
print(f"✅ Saved {file4}")


# ============================================================
# PATCH 5: Frontend - api.js + App.jsx
# ============================================================

# 5a. api.js - Add rules API functions
file5 = "/home/administrator/finnpayments/frontend/src/services/api.js"
with open(file5, "r") as f:
    content5 = f.read()

if "getClassificationRules" not in content5:
    content5 += '''

// ─── Classification Rules ────────────────────────────────
export const getClassificationRules = async () => {
  const base = import.meta.env.VITE_API_URL || 'http://localhost:8001';
  const response = await fetch(`${base}/accounting/classification-rules`);
  if (!response.ok) throw new Error('Failed to fetch rules');
  return response.json();
};

export const deleteClassificationRule = async (ruleId) => {
  const base = import.meta.env.VITE_API_URL || 'http://localhost:8001';
  const response = await fetch(`${base}/accounting/classification-rules/${ruleId}`, { method: 'DELETE' });
  if (!response.ok) throw new Error('Failed to delete rule');
  return response.json();
};
'''
    print("✅ Added classification rules API functions")
else:
    print("✅ Already exists in api.js")

with open(file5, "w") as f:
    f.write(content5)
print(f"✅ Saved {file5}")

# 5b. App.jsx - Add imports and Learned Rules section in sidebar
file6 = "/home/administrator/finnpayments/frontend/src/App.jsx"
with open(file6, "r") as f:
    content6 = f.read()

# Add imports
if "getClassificationRules" not in content6:
    if "reclassifyInvoice" in content6:
        content6 = content6.replace(
            "reclassifyInvoice",
            "reclassifyInvoice,\n  getClassificationRules, deleteClassificationRule",
            1
        )
    elif "checkHealth" in content6:
        content6 = content6.replace(
            "checkHealth",
            "checkHealth,\n  getClassificationRules, deleteClassificationRule",
            1
        )
    print("✅ Added classification rules imports")

# Add Brain icon
if "Brain:" not in content6:
    if "Upload: () =>" in content6:
        content6 = content6.replace(
            "  Upload: () =>",
            '  Brain: () => <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><path d="M12 2a7 7 0 017 7c0 2.5-1.5 4-3 5s-2 2-2 4h-4c0-2-0.5-3-2-4S5 11.5 5 9a7 7 0 017-7z"/><line x1="10" y1="21" x2="14" y2="21"/></svg>,\n  Upload: () =>'
        )
    print("✅ Added Brain icon")

# Add sidebar entry for Learned Rules
old_sidebar_coa = "    { id: 'accounts', label: 'Chart of Accounts', icon: Icons.List }"
new_sidebar_coa = """    { id: 'accounts', label: 'Chart of Accounts', icon: Icons.List },
    { id: 'rules', label: 'Learned Rules', icon: Icons.Brain }"""

if "'rules'" in content6:
    print("✅ Learned Rules sidebar entry already exists")
elif old_sidebar_coa in content6:
    content6 = content6.replace(old_sidebar_coa, new_sidebar_coa)
    print("✅ Added Learned Rules to sidebar")
else:
    print("⚠️ Could not find sidebar CoA entry")

# Add LearnedRules component
rules_component = '''
function LearnedRules() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try { const r = await getClassificationRules(); setRules(r.rules || []); }
    catch (e) { console.error(e); } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id) => {
    if (!confirm('Delete this learned rule?')) return;
    try { await deleteClassificationRule(id); load(); }
    catch (e) { alert(e.message); }
  };

  return (
    <div className="animate-fade-in space-y">
      <div className="page-header">
        <h2>Learned Classification Rules</h2>
      </div>
      <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>
        These rules were learned from your reclassifications. When a new invoice arrives from a known vendor,
        the system will automatically assign the correct GL account based on these rules.
      </p>
      {loading ? <Loading /> : rules.length === 0 ? (
        <Empty text="No learned rules yet. Rules are created when you reclassify invoices." />
      ) : (
        <div className="card">
          <table className="data-table">
            <thead>
              <tr>
                <th>Vendor</th>
                <th>Account</th>
                <th>User Context</th>
                <th>Used</th>
                <th>Learned</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rules.map(r => (
                <tr key={r.id}>
                  <td style={{ fontWeight: 500, color: 'var(--text-white)' }}>{r.vendor_name || '-'}</td>
                  <td>
                    <span className="mono text-xs text-accent">{r.account_code}</span>
                    <span className="text-muted text-xs" style={{ marginLeft: 4 }}>{r.account_name}</span>
                  </td>
                  <td className="text-muted text-sm" style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.user_context || '-'}</td>
                  <td className="mono text-sm">{r.times_used}x</td>
                  <td className="text-muted text-xs">{r.created_at ? new Date(r.created_at).toLocaleDateString() : '-'}</td>
                  <td><button className="btn btn-danger btn-sm" onClick={() => handleDelete(r.id)}>Delete</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

'''

if "function LearnedRules" in content6:
    print("✅ LearnedRules component already exists")
else:
    # Insert before the main App function
    if "function ChartOfAccounts()" in content6:
        content6 = content6.replace(
            "function ChartOfAccounts()",
            rules_component + "function ChartOfAccounts()"
        )
    else:
        # Fallback: before the app container
        content6 = content6.replace(
            "/* ═══════════════════════════════════════════════════════\n   CHART OF ACCOUNTS",
            rules_component + "/* ═══════════════════════════════════════════════════════\n   CHART OF ACCOUNTS"
        )
    print("✅ Added LearnedRules component")

# Add routing for rules view
old_coa_view = "view === 'accounts' && <ChartOfAccounts />"
new_coa_view = "view === 'accounts' && <ChartOfAccounts />}\n        {view === 'rules' && <LearnedRules />"

if "'rules' && <LearnedRules" in content6:
    print("✅ Rules view routing already exists")
elif old_coa_view in content6:
    content6 = content6.replace(old_coa_view, new_coa_view)
    print("✅ Added rules view routing")
else:
    print("⚠️ Could not find accounts view routing")

# Add "Learned" badge to ReclassifyBanner result
if "📚 Learned for future" not in content6 and "result.message}" in content6 and "ReclassifyBanner" in content6:
    content6 = content6.replace(
        '''<div style={{ color: '#27ae60', fontWeight: 600, marginBottom: 8 }}>✓ {result.message}</div>''',
        '''<div style={{ color: '#27ae60', fontWeight: 600, marginBottom: 8 }}>✓ {result.message}</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>📚 Learned for future invoices from this vendor</div>'''
    )
    print("✅ Added learning confirmation to ReclassifyBanner")

with open(file6, "w") as f:
    f.write(content6)
print(f"✅ Saved {file6}")


print("\n" + "="*60)
print("CLASSIFICATION LEARNING - DEPLOYMENT COMPLETE")
print("="*60)
print("""
How it works:

  LEARNING:
  1. User reclassifies an invoice (e.g. Vendor X → Security Fees)
  2. System saves rule: vendor_name + account_code + user_context
  3. Confirmation shows "📚 Learned for future invoices from this vendor"

  APPLYING RULES:
  1. New invoice arrives from Vendor X
  2. suggest_account_code() checks classification_rules table FIRST
  3. If vendor match found → use learned account (skip keywords & default)
  4. LLM prompt also includes learned rules for better AI classification
  5. Rule usage counter increments each time it's applied

  MANAGEMENT:
  - New "Learned Rules" page in sidebar shows all rules
  - Each rule shows: vendor, account, context, times used, date learned
  - Rules can be deleted if no longer applicable

  PRIORITY ORDER:
  1. LLM assignment (from invoice_engine AI prompt with learned rules context)
  2. Learned classification rules (from reclassifications)
  3. Keyword matching (EXPENSE_KEYWORDS)
  4. Default (01-6000-04 Licences) → triggers reclassify prompt

Restart:
  sudo fuser -k 3001/tcp 8001/tcp 2>/dev/null; sleep 2
  cd ~/finnpayments && ./start-all.sh
""")
