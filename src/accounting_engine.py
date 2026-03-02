"""
FinnPayments - Accounting Engine
Updated for Mont Choisy Golf Chart of Accounts.
"""
import os, json, logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger("FinnPayments.AccountingEngine")

ACCOUNT_MAPPINGS = {
    "supplier": {
        "payable": ("01-3000-01", "Trade Creditors Control"),
        "vat_input": ("01-3006-01", "Vat Input"),
        "default_expense": ("01-6000-04", "Licences"),
    },
    "client": {
        "receivable": ("01-2100-01", "Trade Debtors Control"),
        "vat_output": ("01-3005-01", "Vat Output"),
        "default_revenue": ("01-4005-01", "Other Income"),
    },
    "credit_note": {
        "payable": ("01-3000-01", "Trade Creditors Control"),
        "vat_input": ("01-3006-01", "Vat Input"),
        "default_expense": ("01-6000-04", "Licences"),
    },
}

EXPENSE_KEYWORDS = {
    "salary": ("01-5100-04", "Basic Salary_Admin"),
    "wages": ("01-5112-05", "Workers Wages"),
    "bonus": ("01-5101-04", "Statutory Bonus EOY_Administration"),
    "overtime": ("01-5104-04", "Overtimes_Admin"),
    "nps": ("01-5102-04", "Statutory Contribution(Nps&Twef)_Admin"),
    "pension": ("01-6001-05", "Insurance_Pension Scheme (SWAN)"),
    "medical": ("01-5133-04", "Medical Scheme"),
    "uniform": ("01-5109-04", "Uniform Staff_Admin"),
    "training": ("01-5110-04", "Training Staff Cost_Admin"),
    "recruitment": ("01-5108-04", "Recruitment Cost_Admin"),
    "canteen": ("01-5106-04", "Canteen Meals & Water Dispense_Admin"),
    "travelling": ("01-5105-04", "Staff Travelling Cost_Admin"),
    "travel": ("01-5105-04", "Staff Travelling Cost_Admin"),
    "payroll": ("01-6021-04", "Payroll processing fee"),
    "fertilizer": ("01-6050-05", "R&M - Golf course Fertilizers"),
    "fertiliser": ("01-6050-05", "R&M - Golf course Fertilizers"),
    "chemical": ("01-6057-05", "R&M- Golf Course- Chemicals"),
    "seed": ("01-6058-05", "R&M -Golf course (Plant, Seed,sand)"),
    "irrigation": ("01-6080-05", "R&M- Irrigation Pumping Station"),
    "golf cart": ("01-5002-01", "Golf Cart Maintenance & General"),
    "range ball": ("01-5003-01", "Range Balls Cost"),
    "pro shop": ("01-5000-03", "Pro Shop Cos"),
    "fuel": ("01-6051-05", "R&M - Fuel and Diesel Maintenance"),
    "diesel": ("01-6051-05", "R&M - Fuel and Diesel Maintenance"),
    "petrol": ("01-6051-05", "R&M - Fuel and Diesel Maintenance"),
    "lubricant": ("01-6052-05", "R&M - Oils and Lubricants"),
    "vehicle": ("01-6090-05", "Vehicle Running Expenses Maintenance"),
    "maintenance": ("01-6059-05", "R&M -Golf course Maintenance Others"),
    "repair": ("01-6053-05", "R&M - Equipment Repairs"),
    "building maintenance": ("01-6070-05", "Building Maintenance"),
    "painting": ("01-6070-05", "Building Maintenance"),
    "plumbing": ("01-6070-05", "Building Maintenance"),
    "electrical": ("01-6070-05", "Building Maintenance"),
    "contractor": ("01-6075-05", "External Maintenance contractor"),
    "software": ("01-6003-04", "ICT Expenses (Incl Clubmaster)"),
    "computer": ("01-6003-04", "ICT Expenses (Incl Clubmaster)"),
    "ict": ("01-6003-04", "ICT Expenses (Incl Clubmaster)"),
    "sage": ("01-6003-04", "ICT Expenses (Incl Clubmaster)"),
    "hosting": ("01-6003-04", "ICT Expenses (Incl Clubmaster)"),
    "subscription": ("01-6003-04", "ICT Expenses (Incl Clubmaster)"),
    "internet": ("01-6002-04", "Telephone,Mobiles and Internet"),
    "telephone": ("01-6002-04", "Telephone,Mobiles and Internet"),
    "mobile": ("01-6002-04", "Telephone,Mobiles and Internet"),
    "audit": ("01-6022-04", "Audit fee"),
    "legal": ("01-6006-04", "Professional Fees ADM"),
    "professional": ("01-6006-04", "Professional Fees ADM"),
    "consultancy": ("01-6006-04", "Professional Fees ADM"),
    "consulting": ("01-6006-04", "Professional Fees ADM"),
    "secretarial": ("01-6023-04", "Secretarial fee"),
    "taxation": ("01-6025-04", "Taxation fee"),
    "accounting": ("01-6006-04", "Professional Fees ADM"),
    "insurance": ("01-6001-04", "Insurance_General"),
    "electricity": ("01-6250-04", "Electricity AG"),
    "ceb": ("01-6250-04", "Electricity AG"),
    "water": ("01-6251-04", "Water AG"),
    "cwa": ("01-6251-04", "Water AG"),
    "marketing": ("01-6008-06", "Marketing Cost_Others"),
    "advertising": ("01-6008-06", "Marketing Cost_Others"),
    "sponsorship": ("01-6002-06", "Marketing_Sponsorship and Gifts"),
    "brochure": ("01-6010-06", "General Marketing Materials"),
    "security": ("01-6008-04", "Security Fees"),
    "pest control": ("01-6009-04", "Pest Control"),
    "waste": ("01-6010-04", "Waste Removal"),
    "cleaning": ("01-5201-01", "Operating Supplies_Golf Course"),
    "laundry": ("01-5202-01", "Laundry Cost Clubhouse"),
    "stationery": ("01-6005-04", "Printing,Postage & Stationary AG"),
    "printing": ("01-6005-04", "Printing,Postage & Stationary AG"),
    "postage": ("01-6005-04", "Printing,Postage & Stationary AG"),
    "bank charge": ("01-6301-07", "Credit Card Commission and Bk Charges"),
    "bank interest": ("01-8001-08", "Bank interest on Loan"),
    "interest": ("01-8001-08", "Bank interest on Loan"),
    "surcharge": ("01-6302-07", "Surcharge & Penalties"),
    "penalty": ("01-6302-07", "Surcharge & Penalties"),
    "management fee": ("01-6401-07", "Corporate Management fee"),
    "estate": ("01-6403-07", "Estate Shared Cost"),
    "health": ("01-6007-04", "Health & Safety Expenses"),
    "safety": ("01-6007-04", "Health & Safety Expenses"),
    "licence": ("01-6000-04", "Licences"),
    "license": ("01-6000-04", "Licences"),
    "gas": ("01-6076-05", "Gas Clubhouse"),
    "depreciation": ("01-6407-07", "Depreciation-Golf Course Equipment"),
    "rent": ("01-6300-07", "Rental of land"),
    "lease": ("01-6300-07", "Rental of land"),
    "event": ("01-5007-02", "Event Cost"),
    "furniture": ("01-1006-01", "PPE-Cost-Furniture and Fittings"),
    "equipment": ("01-1005-01", "PPE-Cost-Other Equipment"),
}

REVENUE_KEYWORDS = {
    "green fee": ("01-4000-01", "Green Fees Revenue"),
    "pro shop": ("01-4000-03", "Pro Shop Revenue"),
    "horse riding": ("01-4000-12", "Horse Riding(Stables) Revenue"),
    "club rental": ("01-4002-01", "Golf Club Rental Revenue"),
    "range ball": ("01-4003-01", "Range Balls Revenue"),
    "lesson": ("01-4004-01", "Academy Lessons Revenue"),
    "entrance fee": ("01-4010-01", "Entrance Fees Revenue"),
    "subscription": ("01-4011-01", "Annual Subscription Fee_Club Member"),
    "membership": ("01-4002-03", "Leisure & Wellness Centre Membership Revenue"),
    "leisure": ("01-4016-01", "Revenue Leisure / Wellness Centre"),
    "wellness": ("01-4016-01", "Revenue Leisure / Wellness Centre"),
    "tennis": ("01-4018-01", "Revenue Leisure / Wellness - Tennis Paddle"),
    "management fee": ("01-4006-04", "Other Income - Management & Professional Fees Recharged"),
    "interest": ("01-7001-07", "Interest income - 8% for Late Payment"),
}


def lookup_account_name(account_code):
    """Look up account name from Chart of Accounts by code."""
    try:
        from src.database import SessionLocal, ChartOfAccountsDB
        db = SessionLocal()
        acct = db.query(ChartOfAccountsDB).filter(ChartOfAccountsDB.code == account_code).first()
        db.close()
        if acct:
            return acct.name
    except Exception:
        pass
    return account_code


def check_learned_rules(vendor_name, description):
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
        lines = ["\nLEARNED CLASSIFICATIONS (from previous user corrections - use these as strong hints):"]
        for r in rules:
            vendor = r.vendor_name or "any vendor"
            lines.append(f"  {vendor} → {r.account_code} ({r.account_name}) [context: {r.user_context or r.description_pattern}]")
        return "\n".join(lines)
    except Exception:
        return ""


def suggest_account_code(description, invoice_type="supplier", vendor_name=None):
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
    return defaults["default_expense"] if invoice_type in ("supplier", "credit_note") else defaults["default_revenue"]


def generate_accounting_entries(invoice_id, invoice_data, invoice_type="supplier"):
    from src.invoice_engine import generate_entry_id
    entries = []
    mapping = ACCOUNT_MAPPINGS.get(invoice_type, ACCOUNT_MAPPINGS["supplier"])
    total_amount = invoice_data.get("total_amount") or 0.0
    tax_total = invoice_data.get("tax_total") or 0.0
    subtotal = invoice_data.get("subtotal") or (total_amount - tax_total)
    line_items = invoice_data.get("line_items", [])
    vendor_name = invoice_data.get("vendor_name", "Unknown")
    invoice_number = invoice_data.get("invoice_number", "N/A")
    invoice_date = invoice_data.get("invoice_date", datetime.now().strftime("%Y-%m-%d"))
    cost_center = invoice_data.get("suggested_cost_center")
    project_code = invoice_data.get("project_code")
    if total_amount == 0 and not line_items:
        logger.warning(f"No amounts found for invoice {invoice_id}")
        return entries
    entry_lines = []
    is_credit_note = invoice_type == "credit_note"
    if invoice_type in ("supplier", "credit_note"):
        if line_items:
            for item in line_items:
                desc = item.get("description", "") if isinstance(item, dict) else getattr(item, "description", "")
                amount = item.get("amount", 0) if isinstance(item, dict) else getattr(item, "amount", 0)
                item_tax = item.get("tax_amount", 0) if isinstance(item, dict) else getattr(item, "tax_amount", 0)
                acct_code = item.get("account_code") if isinstance(item, dict) else getattr(item, "account_code", None)
                if not acct_code:
                    acct_code, acct_name = suggest_account_code(desc, invoice_type, vendor_name=vendor_name)
                else:
                    acct_name = lookup_account_name(acct_code)
                net_amount = amount - item_tax if item_tax else amount
                if is_credit_note:
                    entry_lines.append({"account_code": acct_code, "account_name": acct_name, "description": f"Credit Note - {desc}", "debit": 0.0, "credit": round(abs(net_amount), 2), "cost_center": cost_center, "project_code": project_code})
                else:
                    entry_lines.append({"account_code": acct_code, "account_name": acct_name, "description": desc, "debit": round(abs(net_amount), 2), "credit": 0.0, "cost_center": cost_center, "project_code": project_code})
        else:
            search_text = f"{vendor_name} {invoice_data.get('notes', '')} {invoice_data.get('raw_text', '')[:200]}"
            acct_code, acct_name = suggest_account_code(search_text, invoice_type, vendor_name=vendor_name)
            ai_acct = invoice_data.get("suggested_account_code")
            if ai_acct:
                acct_code = ai_acct
            if is_credit_note:
                entry_lines.append({"account_code": acct_code, "account_name": acct_name, "description": f"Credit Note from {vendor_name} - Inv {invoice_number}", "debit": 0.0, "credit": round(abs(subtotal), 2), "cost_center": cost_center, "project_code": project_code})
            else:
                entry_lines.append({"account_code": acct_code, "account_name": acct_name, "description": f"Invoice from {vendor_name} - Inv {invoice_number}", "debit": round(abs(subtotal), 2), "credit": 0.0, "cost_center": cost_center, "project_code": project_code})
        if tax_total and tax_total > 0:
            vat_code, vat_name = mapping["vat_input"]
            if is_credit_note:
                entry_lines.append({"account_code": vat_code, "account_name": vat_name, "description": f"VAT reversal - Credit Note {invoice_number}", "debit": 0.0, "credit": round(abs(tax_total), 2)})
            else:
                entry_lines.append({"account_code": vat_code, "account_name": vat_name, "description": f"VAT on Invoice {invoice_number}", "debit": round(abs(tax_total), 2), "credit": 0.0})
        ap_code, ap_name = mapping["payable"]
        if is_credit_note:
            entry_lines.append({"account_code": ap_code, "account_name": ap_name, "description": f"Credit Note {invoice_number} - {vendor_name}", "debit": round(abs(total_amount), 2), "credit": 0.0})
        else:
            entry_lines.append({"account_code": ap_code, "account_name": ap_name, "description": f"Payable to {vendor_name} - Inv {invoice_number}", "debit": 0.0, "credit": round(abs(total_amount), 2)})
    elif invoice_type == "client":
        ar_code, ar_name = mapping["receivable"]
        entry_lines.append({"account_code": ar_code, "account_name": ar_name, "description": f"Receivable from {vendor_name} - Inv {invoice_number}", "debit": round(abs(total_amount), 2), "credit": 0.0})
        if line_items:
            for item in line_items:
                desc = item.get("description", "") if isinstance(item, dict) else getattr(item, "description", "")
                amount = item.get("amount", 0) if isinstance(item, dict) else getattr(item, "amount", 0)
                item_tax = item.get("tax_amount", 0) if isinstance(item, dict) else getattr(item, "tax_amount", 0)
                acct_code, acct_name = suggest_account_code(desc, "client")
                net_amount = amount - item_tax if item_tax else amount
                entry_lines.append({"account_code": acct_code, "account_name": acct_name, "description": desc, "debit": 0.0, "credit": round(abs(net_amount), 2), "cost_center": cost_center, "project_code": project_code})
        else:
            acct_code, acct_name = mapping["default_revenue"]
            entry_lines.append({"account_code": acct_code, "account_name": acct_name, "description": f"Revenue from {vendor_name} - Inv {invoice_number}", "debit": 0.0, "credit": round(abs(subtotal), 2), "cost_center": cost_center, "project_code": project_code})
        if tax_total and tax_total > 0:
            vat_code, vat_name = mapping["vat_output"]
            entry_lines.append({"account_code": vat_code, "account_name": vat_name, "description": f"VAT on Invoice {invoice_number}", "debit": 0.0, "credit": round(abs(tax_total), 2)})
    total_debit = round(sum(l.get("debit", 0) for l in entry_lines), 2)
    total_credit = round(sum(l.get("credit", 0) for l in entry_lines), 2)
    if 0 < abs(total_debit - total_credit) < 0.1:
        diff = round(total_debit - total_credit, 2)
        if diff > 0:
            entry_lines.append({"account_code": "01-6302-07", "account_name": "Rounding", "description": "Rounding difference", "debit": 0.0, "credit": abs(diff)})
        else:
            entry_lines.append({"account_code": "01-6302-07", "account_name": "Rounding", "description": "Rounding difference", "debit": abs(diff), "credit": 0.0})
        total_debit = round(sum(l.get("debit", 0) for l in entry_lines), 2)
        total_credit = round(sum(l.get("credit", 0) for l in entry_lines), 2)
    entry = {
        "entry_id": generate_entry_id(), "invoice_id": invoice_id, "entry_date": invoice_date,
        "reference": f"{invoice_type.upper()}-{invoice_number}",
        "description": f"{'Credit Note' if is_credit_note else 'Invoice'} from {vendor_name} ({invoice_number})",
        "lines": entry_lines, "total_debit": total_debit, "total_credit": total_credit,
        "is_balanced": abs(total_debit - total_credit) < 0.01, "status": "draft",
        "created_by": "FinnPayments AI", "created_at": datetime.now().isoformat(),
    }
    entries.append(entry)
    logger.info(f"Generated journal entry for {invoice_id} | Dr: {total_debit:,.2f} Cr: {total_credit:,.2f}")
    return entries


def validate_journal_entry(entry):
    issues = []
    lines = entry.get("lines", [])
    if not lines:
        issues.append("No entry lines")
    total_dr = sum(l.get("debit", 0) for l in lines)
    total_cr = sum(l.get("credit", 0) for l in lines)
    if abs(total_dr - total_cr) >= 0.01:
        issues.append(f"Entry not balanced: Dr {total_dr:,.2f} != Cr {total_cr:,.2f}")
    for i, line in enumerate(lines):
        if not line.get("account_code"):
            issues.append(f"Line {i+1}: Missing account code")
        if line.get("debit", 0) == 0 and line.get("credit", 0) == 0:
            issues.append(f"Line {i+1}: Both debit and credit are zero")
    return {"is_valid": len(issues) == 0, "issues": issues, "total_debit": round(total_dr, 2), "total_credit": round(total_cr, 2)}
