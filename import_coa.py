#!/usr/bin/env python3
"""
Import MC Golf Chart of Accounts into FinnPayments.
Run: python3 import_coa.py
"""

import os
import sys
import openpyxl

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.database import engine, SessionLocal, Base, ChartOfAccountsDB

EXCEL_FILE = "MC_Golf_Chart_Of_Account.xlsx"


def categorize_account(code: str, description: str) -> str:
    """
    Determine account category from the MC Golf code structure:
      00/01-1xxx = Asset (PPE, Right of Use)
      00/01-2xxx = Asset (Inventory, Debtors, Bank, Prepayments)
      00/01-3xxx = Liability / Equity
      00/01-4xxx = Revenue
      00/01-5xxx = Expense (COGS, Staff costs)
      00/01-6xxx = Expense (Operating expenses)
      00/01-7xxx = Revenue/Expense (Other income, Disposals)
      00/01-8xxx = Expense (Finance costs)
    """
    desc_lower = description.lower()
    
    # Extract the main account group (middle 4 digits)
    parts = code.split("-")
    if len(parts) >= 2:
        acct_num = parts[1]
        first_digit = acct_num[0] if acct_num else "0"
    else:
        first_digit = "0"
    
    if first_digit == "1":
        return "asset"
    elif first_digit == "2":
        return "asset"  # Current assets (inventory, debtors, bank)
    elif first_digit == "3":
        # Distinguish liability from equity
        if "retained earnings" in desc_lower or "capital" in desc_lower:
            return "equity"
        return "liability"
    elif first_digit == "4":
        return "revenue"
    elif first_digit in ("5", "6"):
        return "expense"
    elif first_digit == "7":
        if "income" in desc_lower or "profit" in desc_lower:
            return "revenue"
        return "expense"
    elif first_digit == "8":
        return "expense"
    
    return "expense"


def determine_parent(code: str) -> str:
    """
    Determine parent account code.
    E.g., 01-5100-04 -> 01-5100 (salary group)
    """
    parts = code.split("-")
    if len(parts) == 3:
        # Parent is entity-mainaccount (without department suffix)
        return f"{parts[0]}-{parts[1]}"
    return None


def import_coa():
    """Import the Excel chart of accounts into the database."""
    
    if not os.path.exists(EXCEL_FILE):
        print(f"❌ File not found: {EXCEL_FILE}")
        print(f"   Place '{EXCEL_FILE}' in the finnpayments directory")
        sys.exit(1)
    
    wb = openpyxl.load_workbook(EXCEL_FILE)
    ws = wb.active  # First sheet
    
    db = SessionLocal()
    
    try:
        # Clear existing accounts
        existing = db.query(ChartOfAccountsDB).count()
        if existing > 0:
            print(f"🗑️  Removing {existing} existing accounts...")
            db.query(ChartOfAccountsDB).delete()
            db.commit()
        
        # Import new accounts
        imported = 0
        skipped = 0
        
        for row in ws.iter_rows(min_row=2, values_only=True):
            code, description, acct_type = row
            
            if not code or not description:
                skipped += 1
                continue
            
            code = str(code).strip()
            description = str(description).strip()
            acct_type = str(acct_type).strip() if acct_type else ""
            
            category = categorize_account(code, description)
            
            # Add entity type (Owner/Operator) to description for clarity
            if acct_type:
                full_desc = f"[{acct_type}] {description}"
            else:
                full_desc = description
            
            account = ChartOfAccountsDB(
                code=code,
                name=description,
                category=category,
                parent_code=determine_parent(code),
                description=full_desc,
                is_active=True,
            )
            db.add(account)
            imported += 1
        
        db.commit()
        
        # Print summary
        print(f"\n✅ Imported {imported} accounts ({skipped} skipped)")
        print()
        
        # Count by category
        for cat in ["asset", "liability", "equity", "revenue", "expense"]:
            count = db.query(ChartOfAccountsDB).filter(
                ChartOfAccountsDB.category == cat
            ).count()
            print(f"   {cat.capitalize():12s}: {count} accounts")
        
        # Count by entity type
        print()
        owner_count = db.query(ChartOfAccountsDB).filter(
            ChartOfAccountsDB.description.like("%[Owner]%")
        ).count()
        operator_count = db.query(ChartOfAccountsDB).filter(
            ChartOfAccountsDB.description.like("%[Operator]%")
        ).count()
        print(f"   Owner:        {owner_count} accounts")
        print(f"   Operator:     {operator_count} accounts")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()
    
    print(f"\n✅ Chart of Accounts import complete!")
    print(f"   Restart FinnPayments to apply changes.")


if __name__ == "__main__":
    import_coa()
