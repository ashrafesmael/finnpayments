#!/bin/bash
# Fix: Add OCR fallback for scanned PDF invoices
# Run: bash fix_ocr_fallback.sh

FILE="/home/administrator/finnpayments/src/invoice_engine.py"

python3 << 'PYEOF'
file = "/home/administrator/finnpayments/src/invoice_engine.py"
with open(file, "r") as f:
    content = f.read()

# Find and replace the extract_text_from_pdf function
old_func = '''def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from PDF using pdfplumber"""
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
        
        full_text = "\\n".join(text_parts)
        logger.info(f"📄 Extracted {len(full_text)} chars from PDF")
        return full_text
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        return ""'''

new_func = '''def extract_text_from_pdf(file_path: str) -> str:
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
        
        full_text = "\\n".join(text_parts)
        
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
        
        return "\\n".join(text_parts)
    except Exception as e:
        logger.error(f"OCR fallback error: {e}")
        return ""'''

if old_func in content:
    content = content.replace(old_func, new_func)
    with open(file, "w") as f:
        f.write(content)
    print("✅ Added OCR fallback for scanned PDFs")
else:
    print("⚠️  Could not find exact function. Trying to patch...")
    # Try inserting ocr_pdf function after the existing extract_text_from_pdf
    if "def ocr_pdf" not in content:
        # Add OCR fallback call inside extract_text_from_pdf
        old_log = '        logger.info(f"📄 Extracted {len(full_text)} chars from PDF")\n        return full_text\n    except Exception as e:\n        logger.error(f"PDF extraction error: {e}")\n        return ""'
        new_log = '''        # OCR fallback: if pdfplumber got nothing, the PDF is likely a scanned image
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
        
        return "\\n".join(text_parts)
    except Exception as e:
        logger.error(f"OCR fallback error: {e}")
        return ""'''
        if old_log in content:
            content = content.replace(old_log, new_log)
            with open(file, "w") as f:
                f.write(content)
            print("✅ Patched: Added OCR fallback")
        else:
            print("❌ Could not patch automatically. Manual edit needed.")
    else:
        print("ℹ️  ocr_pdf already exists in file")
PYEOF

echo ""
echo "Now restart FinnPayments:"
echo "  sudo fuser -k 3001/tcp 8001/tcp 2>/dev/null"
echo "  sleep 2"
echo "  cd ~/finnpayments && ./start-all.sh"
