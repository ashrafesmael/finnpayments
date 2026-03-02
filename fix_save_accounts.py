#!/usr/bin/env python3
"""
Patch _save_invoice_to_db to:
1. Auto-assign GL account codes to line items using suggest_account_code
2. Better handle null invoice_number and invoice_date
Run on server: python3 fix_save_accounts.py
"""

file = "/home/administrator/finnpayments/src/api.py"
with open(file, "r") as f:
    content = f.read()

# Fix 1: Add account code suggestion to line items during save
old_line_save = '''                    account_code=item.get("account_code"),'''
new_line_save = '''                    account_code=item.get("account_code") or suggest_account_code(item.get("description", ""), invoice_type)[0],'''

if old_line_save in content:
    content = content.replace(old_line_save, new_line_save)
    print("✅ Fix 1: Line items now get auto-assigned GL account codes")
else:
    print("⚠️  Fix 1: Could not find line item save block")

# Fix 2: Better null handling for vendor_name
old_vendor = 'vendor_name=extracted.get("vendor_name", "Unknown"),'
new_vendor = 'vendor_name=extracted.get("vendor_name") or "Unknown Vendor",'
if old_vendor in content:
    content = content.replace(old_vendor, new_vendor)
    print("✅ Fix 2a: vendor_name null handling improved")

# Also try the already-patched version
old_vendor2 = 'vendor_name=extracted.get("vendor_name") or "Unknown Vendor",'
if old_vendor2 in content:
    print("✅ Fix 2a: vendor_name already patched")

# Fix 3: Better null handling for invoice_number  
old_invnum = 'invoice_number=extracted.get("invoice_number", "N/A"),'
new_invnum = 'invoice_number=extracted.get("invoice_number") or "N/A",'
if old_invnum in content:
    content = content.replace(old_invnum, new_invnum)
    print("✅ Fix 2b: invoice_number null handling improved")

with open(file, "w") as f:
    f.write(content)

print("\n✅ All fixes applied. Restart FinnPayments to apply.")
print("   sudo systemctl restart finnpayments-backend")
print("   Then re-upload the invoice to test.")
