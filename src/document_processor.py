"""
Document Processing Engine using LandingAI ADE
"""
import os
import json
import time
from pathlib import Path
import pdfplumber
import httpx
import pytesseract
import cv2
import numpy as np
from pdf2image import convert_from_path
from groq import Groq
from typing import Dict, List, Optional, Union
from datetime import datetime
import logging
from src.models import SuspiciousActivityReport, TransactionRecord, KYCDocument, DocumentType
from src.utils import mock_bedrock_extraction, generate_analysis_id
from src.aws_services import aws_manager

logger = logging.getLogger(__name__)


def regex_extract_passport_data(text: str) -> dict:
    """
    Regex-based fallback extraction for passport/KYC documents.
    Used when LLM is unavailable (rate limited, etc.)
    """
    import re
    
    result = {
        "full_name": "",
        "first_name": "",
        "last_name": "",
        "date_of_birth": "",
        "nationality": "",
        "passport_number": "",
        "national_id": "",
        "gender": "",
        "place_of_birth": "",
        "issue_date": "",
        "expiry_date": "",
        "issuing_authority": "",
        "extraction_method": "regex_fallback"
    }
    
    # Normalize text
    text_upper = text.upper()
    
    # Extract Surname/Last Name
    surname_match = re.search(r'SURNAME[S]?\s*[:/]?\s*(?:AT\s*BIRTH)?\s*\n?\s*([A-Za-z][A-Za-z\s\-\'\u00C0-\u017F]+?)(?:\n|FIRST|GIVEN|GENDER|DATE)', text, re.IGNORECASE)
    if surname_match:
        result["last_name"] = surname_match.group(1).strip().title()
    
    # Extract First/Given Name
    first_match = re.search(r'(?:FIRST|GIVEN)\s*NAME[S]?\s*[:/]?\s*\n?\s*([A-Za-z][A-Za-z\s\-\'\u00C0-\u017F]+?)(?:\n|SURNAME|DATE|GENDER|BIRTH)', text, re.IGNORECASE)
    if first_match:
        result["first_name"] = first_match.group(1).strip().title()
    
    # Combine names
    if result["first_name"] and result["last_name"]:
        result["full_name"] = f"{result['first_name']} {result['last_name']}"
    elif result["last_name"]:
        result["full_name"] = result["last_name"]
    elif result["first_name"]:
        result["full_name"] = result["first_name"]
    

    # Try "Name:" format (common in Middle Eastern IDs like Jordan)
    # Look for the actual name on the next line after "Name" label
    name_lines = re.search(r'Name[:\s]*[a-z]*\s*\n\s*([A-Z][A-Z\s]+?)(?:\n|Date|National|ID)', text, re.IGNORECASE | re.MULTILINE)
    if name_lines and not result["full_name"]:
        full_name = name_lines.group(1).strip()
        # Clean up any trailing labels
        full_name = re.sub(r'\s*(Date|Birth|National|ID|No).*', '', full_name, flags=re.IGNORECASE).strip()
        if len(full_name) > 3:  # Minimum valid name length
            result["full_name"] = full_name.title()
            parts = full_name.split()
            if len(parts) >= 2:
                result["last_name"] = parts[-1].title()
                result["first_name"] = " ".join(parts[:-1]).title()
    
    # MRZ parsing for names (e.g., P<JORSALAMEH<<AYA<MOHAMMAD<HASHEM)
    mrz_name = re.search(r'P<[A-Z]{3}([A-Z]+)<<([A-Z<]+)', text_upper)
    if mrz_name and not result["full_name"]:
        last_name = mrz_name.group(1).replace('<', ' ').strip()
        first_names = mrz_name.group(2).replace('<', ' ').strip()
        result["last_name"] = last_name.title()
        result["first_name"] = first_names.title()
        result["full_name"] = f"{first_names} {last_name}".title()
    
    # Fallback MRZ without country code prefix
    if not result["full_name"]:
        mrz_name = re.search(r'([A-Z]{2,})<<([A-Z<]+?)(?:<{2,}|\d)', text_upper)
        if mrz_name:
            last_name = mrz_name.group(1).replace('<', ' ').strip()
            first_names = mrz_name.group(2).replace('<', ' ').strip()
            result["last_name"] = last_name.title()
            result["first_name"] = first_names.title()
            result["full_name"] = f"{first_names} {last_name}".title()
    
    passport_mrz = re.search(r'\n([A-Z]d{6,9})<<', text_upper)
    passport_mrz = re.search(r'\n([A-Z]d{6,9})<<', text_upper)
    passport_mrz = re.search(r'\n([A-Z]d{6,9})<<', text_upper)
    if passport_mrz and not result["passport_number"]:
        result["passport_number"] = passport_mrz.group(1)
    
    # Jordan nationality detection
    if not result["nationality"] and ("JORDAN" in text_upper or "JOR<<" in text_upper or "HASHEMITE" in text_upper):
        result["nationality"] = "Jordan"
    
    # ID number formats (Jordan: HDN29734)
    id_no_match = re.search(r'ID\s*(?:NO|NUMBER)?[:\.\s]+([A-Z0-9]{6,12})', text, re.IGNORECASE)
    if id_no_match and not result["national_id"]:
        result["national_id"] = id_no_match.group(1).upper()
    
    # Expiry date (e.g., "18/11/2027: Expiry")
    expiry_match = re.search(r'(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\s*[:\s]*(?:Expiry|EXP)', text, re.IGNORECASE)
    if expiry_match and not result["expiry_date"]:
        result["expiry_date"] = expiry_match.group(1)

    # Extract Date of Birth from Jordanian passport format (e.g., "07 MAYI JU 1997")
    jordan_dob = re.search(r'(?:Date\s*of\s*Birth|Birth)[^\d]*(\d{1,2})\s*([A-Z]{3})[A-Z/\s]*(\d{4})', text, re.IGNORECASE)
    if jordan_dob and not result["date_of_birth"]:
        day = jordan_dob.group(1)
        month = jordan_dob.group(2)[:3].title()
        year = jordan_dob.group(3)
        result["date_of_birth"] = f"{day} {month} {year}"
    
    # Extract Date of Birth - various formats
    dob_patterns = [
        r'(?:DATE\s*OF\s*BIRTH|DOB|D\.O\.B)[:\s/]*([0-9]{1,2}[\s/\-\.][A-Za-z]{3}[\s/\-\.][0-9]{4})',
        r'(?:DATE\s*OF\s*BIRTH|DOB)[:\s/]*([0-9]{1,2}[\s/\-\.][0-9]{1,2}[\s/\-\.][0-9]{4})',
        r'([0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})(?=\s|$|\n)',
        r'\bF\s+([0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})',  # After gender F
        r'\bM\s+([0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4})',  # After gender M
    ]
    for pattern in dob_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["date_of_birth"] = match.group(1).strip()
            break
    
    # Extract Nationality
    nat_patterns = [
        r'CITIZEN\s*OF\s*([A-Z]+)',
        r'NATIONALITY[:\s/]*([A-Z]+)',
        r'REPUBLIC\s*OF\s*([A-Z]+)',
    ]
    for pattern in nat_patterns:
        match = re.search(pattern, text_upper)
        if match:
            result["nationality"] = match.group(1).strip().title()
            break
    
    # If nationality not found but "MAURITIUS" appears, use it
    if not result["nationality"] and "MAURITIUS" in text_upper:
        result["nationality"] = "Mauritius"
    
    # Extract National ID (Mauritius format: A + 13 digits)
    id_match = re.search(r'(?:ID\s*(?:NUMBER|NO)?[:\s/]*)?([A-Z][0-9]{13})', text_upper)
    if id_match:
        result["national_id"] = id_match.group(1)
    
    # Extract Passport Number
    passport_match = re.search(r'PASSPORT\s*(?:NO|NUMBER|N°)?[:\s/]*([A-Z0-9]{6,12})', text_upper)
    if passport_match:
        result["passport_number"] = passport_match.group(1)
    
    # Extract Gender
    gender_match = re.search(r'GENDER[:\s/]*([MF])\b|\b([MF])\s+[0-9]{1,2}\s+[A-Za-z]{3}\s+[0-9]{4}', text, re.IGNORECASE)
    if gender_match:
        g = (gender_match.group(1) or gender_match.group(2)).upper()
        result["gender"] = "Male" if g == "M" else "Female"
    
    # Extract Issue Date
    issue_match = re.search(r'(?:DATE\s*OF\s*ISSUE|ISSUE\s*DATE|ISSUED)[:\s/]*([0-9]{1,2}[\s/\-\.][A-Za-z]{3}[\s/\-\.][0-9]{4})', text, re.IGNORECASE)
    if issue_match:
        result["issue_date"] = issue_match.group(1).strip()
    
    # Extract from MRZ if present
    mrz_match = re.search(r'P<([A-Z]{3})([A-Z]+)<+([A-Z]+)', text_upper)
    if mrz_match:
        country_code = mrz_match.group(1)
        surname_mrz = mrz_match.group(2).replace('<', ' ').strip()
        given_mrz = mrz_match.group(3).replace('<', ' ').strip()
        
        if not result["last_name"]:
            result["last_name"] = surname_mrz.title()
        if not result["first_name"]:
            result["first_name"] = given_mrz.title()
        if not result["full_name"]:
            result["full_name"] = f"{given_mrz.title()} {surname_mrz.title()}"
        
        country_map = {"MUS": "Mauritius", "USA": "United States", "GBR": "United Kingdom", "ZAF": "South Africa", "IND": "India"}
        if not result["nationality"] and country_code in country_map:
            result["nationality"] = country_map[country_code]
    
    # Handle driving licence format: "Surname Name" followed by actual values
    # Pattern: "Surname Name\n... ESMAEL Mohammad. Ashraf"
    if not result["full_name"] or result["full_name"].lower() == "name":
        # Try driving licence pattern
        dl_match = re.search(r'Surname\s+Name\s*\n[^A-Za-z]*([A-Za-z\-]+)\s+([A-Za-z\.]+)\s*([A-Za-z]+)?', text, re.IGNORECASE)
        if dl_match:
            surname = dl_match.group(1).strip()
            first = dl_match.group(2).strip().replace('.', '')
            middle = dl_match.group(3).strip() if dl_match.group(3) else ""
            result["last_name"] = surname.title()
            result["first_name"] = f"{first} {middle}".strip().title()
            result["full_name"] = f"{result['first_name']} {result['last_name']}"
    
    # Extract DOB from driving licence format: "Date of Birth" followed by date
    if not result["date_of_birth"]:
        dl_dob = re.search(r'Date\s*of\s*Birth\s*[\n\s]*([0-9]{1,2}[\./][0-9]{1,2}[\./][0-9]{2,4})', text, re.IGNORECASE)
        if dl_dob:
            result["date_of_birth"] = dl_dob.group(1)
        else:
            # Try pattern with dots: 19.8.67
            dl_dob2 = re.search(r'([0-9]{1,2}\.[0-9]{1,2}\.[0-9]{2,4})\s+[A-Z]+\s+[A-Za-z]', text)
            if dl_dob2:
                result["date_of_birth"] = dl_dob2.group(1)
    
    # Extract licence number
    if not result["passport_number"]:
        licence_match = re.search(r'Licence\s*No\.?\s*[:\s]*([0-9]{5,10})', text, re.IGNORECASE)
        if licence_match:
            result["passport_number"] = licence_match.group(1)  # Use passport_number field for licence
    
    # Add required fields with defaults for KYCDocument compatibility
    result["customer_id"] = result.get("customer_id") or f"CUST-{result.get('national_id', 'UNKNOWN')[-6:]}"
    result["document_type"] = result.get("document_type") or "ID Document"
    result["document_number"] = result.get("document_number") or result.get("national_id") or result.get("passport_number") or "Unknown"
    result["address"] = result.get("address") or "Not provided"
    result["expiry_date"] = result.get("expiry_date") or "Not provided"
    result["issue_date"] = result.get("issue_date") or "Not provided"
    result["politically_exposed_person"] = False
    result["confidence_scores"] = {"full_name": 0.7, "document_number": 0.7}
    
    logger.info(f"📋 Regex extraction: Name={result['full_name']}, DOB={result['date_of_birth']}, Nationality={result['nationality']}, ID={result.get('document_number')}")
    
    return result



class MockLandingAIADE:
    """
    Mock LandingAI ADE client for demo purposes
    In production, replace with actual LandingAI ADE client
    """
    
    def __init__(self, apikey: str = None, environment: str = "production"):
        self.apikey = apikey
        self.environment = environment
        pass  # Mock ADE initialized
    
    def parse(self, document: Union[str, Path], model: str = "dpt-2-latest"):
        """Extract text from PDF documents using Datalab API or fallback to local OCR"""
        logger.info(f"📄 Extracting text from document: {document}")
        
        doc_path = str(document)
        extracted_text = ""
        
        # Try OCR.space first (Engine 2 is excellent for passports/MRZ)
        ocrspace_key = os.getenv('OCRSPACE_API_KEY')
        if ocrspace_key and (doc_path.lower().endswith('.pdf') or doc_path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif', '.tif', '.tiff'))):
            try:
                logger.info("🔍 Trying OCR.space API (Engine 2) for extraction...")
                extracted_text = self._extract_with_ocrspace(doc_path, ocrspace_key, use_engine2=True)
                if extracted_text and len(extracted_text.strip()) > 100:
                    logger.info(f"✅ OCR.space successfully extracted {len(extracted_text)} characters")
                    
                    class Response:
                        def __init__(self, text):
                            self.markdown = text
                            self.chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
                    
                    return Response(extracted_text)
                else:
                    logger.info("⚠️ OCR.space returned insufficient text, trying Datalab...")
            except Exception as e:
                logger.warning(f"⚠️ OCR.space failed: {e}, trying Datalab...")
        
        # Try Datalab API as fallback (best accuracy for complex documents)
        datalab_key = os.getenv('DATALAB_API_KEY')
        if datalab_key and (doc_path.lower().endswith('.pdf') or doc_path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))):
            try:
                logger.info("🚀 Using Datalab Marker API for high-accuracy extraction")
                extracted_text = self._extract_with_datalab(doc_path, datalab_key)
                if extracted_text and len(extracted_text.strip()) > 50:
                    logger.info(f"✅ Datalab extracted {len(extracted_text)} characters")
                    
                    class Response:
                        def __init__(self, text):
                            self.markdown = text
                            self.chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
                    
                    return Response(extracted_text)
            except Exception as e:
                logger.warning(f"⚠️ Datalab API failed: {e}, falling back to local OCR")

        extracted_text = ""
        
        try:
            doc_path = str(document)
            if doc_path.lower().endswith('.pdf'):
                # First try pdfplumber for text-based PDFs
                with pdfplumber.open(doc_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            extracted_text += page_text + "\n"
                
                # If very little text found, try OCR for scanned documents
                if len(extracted_text.strip()) < 100:
                    logger.info("📸 Low text content, trying OCR...")
                    try:
                        images = convert_from_path(doc_path, dpi=300)
                        ocr_text = ""
                        for img in images:
                            # Convert to numpy array for processing
                            img_np = np.array(img)
                            
                            # Try to detect and fix orientation using tesseract OSD
                            try:
                                osd = pytesseract.image_to_osd(img, output_type=pytesseract.Output.DICT)
                                rotation = osd.get('rotate', 0)
                                if rotation != 0:
                                    logger.info(f"🔄 Rotating image by {rotation} degrees")
                                    if rotation == 90:
                                        img_np = cv2.rotate(img_np, cv2.ROTATE_90_COUNTERCLOCKWISE)
                                    elif rotation == 180:
                                        img_np = cv2.rotate(img_np, cv2.ROTATE_180)
                                    elif rotation == 270:
                                        img_np = cv2.rotate(img_np, cv2.ROTATE_90_CLOCKWISE)
                            except:
                                pass  # OSD may fail on some images
                            
                            # Use PSM 6 (assume single uniform block) for better results
                            custom_config = r'--oem 3 --psm 6'
                            ocr_text += pytesseract.image_to_string(img_np, config=custom_config) + "\n"
                        if len(ocr_text.strip()) > len(extracted_text.strip()):
                            extracted_text = ocr_text
                            logger.info(f"✅ OCR extracted {len(extracted_text)} characters")
                    except Exception as ocr_error:
                        logger.warning(f"⚠️ OCR failed: {ocr_error}")
                else:
                    logger.info(f"✅ Extracted {len(extracted_text)} characters from PDF")
            elif doc_path.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp')):
                # Handle image files with OCR
                try:
                    from PIL import Image
                    img = Image.open(doc_path)
                    
                    # Try to detect and fix orientation
                    try:
                        img_np = np.array(img)
                        osd = pytesseract.image_to_osd(img, output_type=pytesseract.Output.DICT)
                        rotation = osd.get('rotate', 0)
                        if rotation != 0:
                            logger.info(f"🔄 Rotating image by {rotation} degrees")
                            img = img.rotate(-rotation, expand=True)
                    except:
                        pass
                    
                    custom_config = r'--oem 3 --psm 6'
                    extracted_text = pytesseract.image_to_string(img, config=custom_config)
                    logger.info(f"✅ OCR extracted {len(extracted_text)} characters from image")
                except Exception as img_err:
                    logger.warning(f"⚠️ Image OCR failed: {img_err}")
                    extracted_text = "Unable to extract text from image"
            else:
                try:
                    with open(doc_path, 'r', encoding='utf-8') as f:
                        extracted_text = f.read()
                    logger.info(f"✅ Read {len(extracted_text)} characters from text file")
                except:
                    extracted_text = "Unable to extract text from this file type"
                    logger.warning(f"⚠️ Could not read file: {doc_path}")
        except Exception as e:
            logger.error(f"❌ PDF extraction failed: {e}")
            extracted_text = f"Error extracting document: {str(e)}"

        class Response:
            def __init__(self, text):
                self.markdown = text if text.strip() else "No text could be extracted from document"
                self.chunks = [text[i:i+1000] for i in range(0, len(text), 1000)] if text else []

        return Response(extracted_text)




    def _compress_pdf_for_ocr(self, file_path: str, max_size_kb: int = 900) -> str:
        """Compress PDF or convert to optimized image for OCR if file is too large"""
        import os
        import tempfile
        
        file_size_kb = os.path.getsize(file_path) / 1024
        
        if file_size_kb <= max_size_kb:
            return file_path  # No compression needed
        
        logger.info(f"📦 File size {file_size_kb:.0f}KB exceeds {max_size_kb}KB, compressing...")
        
        try:
            # For PDFs, extract first page as image
            if file_path.lower().endswith('.pdf'):
                from pdf2image import convert_from_path
                from PIL import Image
                
                # Convert first page to image at lower DPI
                images = convert_from_path(file_path, first_page=1, last_page=1, dpi=200)
                
                if images:
                    # Save as compressed JPEG
                    temp_path = tempfile.mktemp(suffix='.jpg')
                    
                    # Convert to RGB if necessary
                    img = images[0]
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    # Start with quality 85 and reduce if needed
                    quality = 85
                    while quality > 20:
                        img.save(temp_path, 'JPEG', quality=quality, optimize=True)
                        new_size_kb = os.path.getsize(temp_path) / 1024
                        
                        if new_size_kb <= max_size_kb:
                            logger.info(f"✅ Compressed PDF to {new_size_kb:.0f}KB JPEG (quality={quality})")
                            return temp_path
                        
                        quality -= 10
                    
                    # If still too large, resize the image
                    width, height = img.size
                    scale = 0.7
                    while scale > 0.3:
                        new_size = (int(width * scale), int(height * scale))
                        resized = img.resize(new_size, Image.LANCZOS)
                        resized.save(temp_path, 'JPEG', quality=70, optimize=True)
                        new_size_kb = os.path.getsize(temp_path) / 1024
                        
                        if new_size_kb <= max_size_kb:
                            logger.info(f"✅ Resized and compressed to {new_size_kb:.0f}KB (scale={scale:.1f})")
                            return temp_path
                        
                        scale -= 0.1
                    
                    logger.warning(f"⚠️ Could not compress below {max_size_kb}KB, using {new_size_kb:.0f}KB")
                    return temp_path
            
            # For images, compress directly
            elif file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.tif', '.tiff')):
                from PIL import Image
                
                img = Image.open(file_path)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                temp_path = tempfile.mktemp(suffix='.jpg')
                
                # Try different quality levels
                quality = 85
                while quality > 20:
                    img.save(temp_path, 'JPEG', quality=quality, optimize=True)
                    new_size_kb = os.path.getsize(temp_path) / 1024
                    
                    if new_size_kb <= max_size_kb:
                        logger.info(f"✅ Compressed image to {new_size_kb:.0f}KB (quality={quality})")
                        return temp_path
                    
                    quality -= 10
                
                # Resize if still too large
                width, height = img.size
                scale = 0.7
                while scale > 0.3:
                    new_size = (int(width * scale), int(height * scale))
                    resized = img.resize(new_size, Image.LANCZOS)
                    resized.save(temp_path, 'JPEG', quality=70, optimize=True)
                    new_size_kb = os.path.getsize(temp_path) / 1024
                    
                    if new_size_kb <= max_size_kb:
                        logger.info(f"✅ Resized image to {new_size_kb:.0f}KB (scale={scale:.1f})")
                        return temp_path
                    
                    scale -= 0.1
                
                return temp_path
                
        except Exception as e:
            logger.warning(f"⚠️ Compression failed: {e}")
        
        return file_path  # Return original if compression fails


    def _extract_with_ocrspace(self, doc_path: str, api_key: str, use_engine2: bool = True) -> str:
        """Extract text using OCR.space API - Engine 2 is better for passports/MRZ"""
        import base64
        import httpx
        import os
        
        try:
            # Check file size and compress if needed (OCR.space free limit is 1024KB)
            file_size_kb = os.path.getsize(doc_path) / 1024
            temp_file = None
            
            if file_size_kb > 900:  # Leave some margin
                logger.info(f"📦 File is {file_size_kb:.0f}KB, compressing for OCR.space...")
                compressed_path = self._compress_pdf_for_ocr(doc_path, max_size_kb=900)
                if compressed_path != doc_path:
                    temp_file = compressed_path
                    doc_path = compressed_path
            
            # Read file and encode to base64
            with open(doc_path, 'rb') as f:
                file_data = f.read()
            
            # Determine content type
            file_ext = os.path.splitext(doc_path)[1].lower()
            content_types = {
                '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                '.png': 'image/png', '.gif': 'image/gif',
                '.pdf': 'application/pdf', '.tif': 'image/tiff', '.tiff': 'image/tiff'
            }
            content_type = content_types.get(file_ext, 'image/jpeg')
            
            base64_image = f"data:{content_type};base64," + base64.b64encode(file_data).decode('utf-8')
            
            # OCR.space API parameters
            payload = {
                'base64Image': base64_image,
                'language': 'eng',
                'isOverlayRequired': 'false',
                'detectOrientation': 'true',
                'scale': 'true',
                'isTable': 'true',
                'OCREngine': '2' if use_engine2 else '1'
            }
            
            headers = {'apikey': api_key}
            
            logger.info(f"🔍 Calling OCR.space API (Engine {'2' if use_engine2 else '1'})...")
            
            response = httpx.post(
                'https://api.ocr.space/parse/image',
                data=payload,
                headers=headers,
                timeout=120.0
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('OCRExitCode') == 1:
                    parsed_results = result.get('ParsedResults', [])
                    extracted_text = ""
                    for pr in parsed_results:
                        if pr.get('FileParseExitCode') == 1:
                            extracted_text += pr.get('ParsedText', '') + "\n"
                    
                    processing_time = result.get('ProcessingTimeInMilliseconds', 0)
                    logger.info(f"✅ OCR.space extracted {len(extracted_text)} chars in {processing_time}ms")
                    
                    # Cleanup temp file if created
                    if temp_file and os.path.exists(temp_file):
                        try:
                            os.remove(temp_file)
                        except:
                            pass
                    
                    return extracted_text.strip()
                elif result.get('OCRExitCode') == 2:
                    # Partial success
                    parsed_results = result.get('ParsedResults', [])
                    extracted_text = ""
                    for pr in parsed_results:
                        text = pr.get('ParsedText', '')
                        if text:
                            extracted_text += text + "\n"
                    if extracted_text:
                        logger.info(f"⚠️ OCR.space partial extraction: {len(extracted_text)} chars")
                        return extracted_text.strip()
                
                error_msg = result.get('ErrorMessage', ['Unknown error'])
                logger.error(f"❌ OCR.space error: {error_msg}")
                return None
            else:
                logger.error(f"❌ OCR.space HTTP error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ OCR.space extraction failed: {e}")
            # Cleanup temp file if created
            if 'temp_file' in locals() and temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            return None

    def _extract_with_datalab(self, doc_path: str, api_key: str) -> str:
        """Extract text using Datalab Marker API"""
        import time
        import httpx
        
        # Submit the document
        with open(doc_path, 'rb') as f:
            files = {'file': (os.path.basename(doc_path), f, 'application/pdf')}
            headers = {'X-API-Key': api_key}
            
            response = httpx.post(
                'https://www.datalab.to/api/v1/marker',
                files=files,
                headers=headers,
                timeout=60.0
            )
            response.raise_for_status()
            result = response.json()
        
        if not result.get('success'):
            raise Exception(result.get('error', 'Unknown error'))
        
        # Poll for results
        check_url = result.get('request_check_url')
        headers = {'X-API-Key': api_key}
        
        for attempt in range(120):  # Max 120 attempts (2 minutes)
            time.sleep(1)
            check_response = httpx.get(check_url, headers=headers, timeout=30.0)
            check_result = check_response.json()
            
            status = check_result.get('status', '')
            
            # Log progress every 10 seconds
            if attempt % 10 == 0:
                logger.info(f"⏳ Datalab processing... status: {status} (attempt {attempt})")
            
            if status == 'complete':
                markdown = check_result.get('markdown', '')
                if markdown:
                    return markdown
                # Try alternative field names
                return check_result.get('text', '') or check_result.get('output', '') or str(check_result)
            elif status in ['error', 'failed']:
                raise Exception(check_result.get('error', 'Processing failed'))
        
        raise Exception("Timeout waiting for Datalab processing (2 minutes)")


class DocumentProcessor:
    """Main document processor using LandingAI ADE"""
    
    def __init__(self, api_key: Optional[str] = None, use_mock: bool = False):
        """
        Initialize document processor
        
        Args:
            api_key: LandingAI API key
            use_mock: Use mock implementation for demo (default: False - use real services)
        """
        self.use_mock = use_mock
        self.use_real_bedrock = False
        
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        if use_mock:
            self.client = MockLandingAIADE(apikey=api_key)
            logger.info("📝 Using mock LandingAI ADE client")
        else:
            # In production, use actual LandingAI ADE client
            try:
                from landingai_ade import LandingAIADE
                
                # Try multiple API key environment variables
                landing_ai_key = (
                    api_key or 
                    os.getenv("LANDING_AI_API_KEY") or 
                    os.getenv("VISION_AGENT_API_KEY")
                )
                
                if not landing_ai_key:
                    raise ValueError("No LandingAI API key found in environment")
                
                self.client = LandingAIADE(apikey=landing_ai_key)
                logger.info("✅ Real LandingAI ADE client initialized")
            except ImportError:
                pass  # LandingAI not configured
                self.client = MockLandingAIADE(apikey=api_key)
                self.use_mock = True
            except Exception as e:
                logger.warning(f"⚠️ LandingAI ADE initialization failed: {e}, using mock implementation")
                self.client = MockLandingAIADE(apikey=api_key)
                self.use_mock = True
        
        # Check if AWS Bedrock is available
        if self._has_aws_credentials():
            self.use_real_bedrock = True
            logger.info("✅ Groq LLM available for analysis")
        else:
            logger.info("📝 Groq not configured, using mock extraction")
    

    def _validate_and_fix_dates(self, extracted_data: Dict) -> Dict:
        """Validate and fix obviously incorrect dates"""
        from datetime import datetime
        
        current_year = datetime.now().year
        
        # Check date of birth
        dob = extracted_data.get('date_of_birth', '')
        if dob and dob != 'Not provided' and dob != 'NOT PROVIDED':
            try:
                # Parse the date
                if len(dob) >= 4:
                    year = int(dob[:4])
                    
                    # Check if year is reasonable (person should be 0-120 years old)
                    age = current_year - year
                    
                    if age > 120 or age < 0:
                        # Likely OCR error - try to fix common mistakes
                        # 1907 -> 1967, 1908 -> 1968, etc. (0 misread as 6)
                        if year < 1920:
                            fixed_year = year + 60  # Common OCR error: 0 read as 6
                            if 0 <= (current_year - fixed_year) <= 120:
                                fixed_dob = str(fixed_year) + dob[4:]
                                logger.info(f"🔧 Fixed DOB: {dob} → {fixed_dob} (age {current_year - fixed_year})")
                                extracted_data['date_of_birth'] = fixed_dob
                        elif year > current_year:
                            # Future date - probably century error
                            fixed_year = year - 100
                            if 0 <= (current_year - fixed_year) <= 120:
                                fixed_dob = str(fixed_year) + dob[4:]
                                logger.info(f"🔧 Fixed DOB: {dob} → {fixed_dob} (age {current_year - fixed_year})")
                                extracted_data['date_of_birth'] = fixed_dob
            except (ValueError, IndexError) as e:
                logger.debug(f"Could not validate DOB: {e}")
        
        # Check expiry date - should be in the future or recent past (within 10 years)
        expiry = extracted_data.get('expiry_date', '')
        if expiry and expiry != 'Not provided' and expiry != 'NOT PROVIDED':
            try:
                if len(expiry) >= 4:
                    year = int(expiry[:4])
                    # Expiry should be between 10 years ago and 20 years in future
                    if year < current_year - 10 or year > current_year + 20:
                        logger.warning(f"⚠️ Suspicious expiry date: {expiry}")
            except (ValueError, IndexError):
                pass
        
        # Check issue date - should be in the past
        issue = extracted_data.get('issue_date', '')
        if issue and issue != 'Not provided' and issue != 'NOT PROVIDED':
            try:
                if len(issue) >= 4:
                    year = int(issue[:4])
                    if year > current_year:
                        # Future issue date - probably century error
                        fixed_year = year - 100
                        if fixed_year > 1950:
                            fixed_issue = str(fixed_year) + issue[4:]
                            logger.info(f"🔧 Fixed issue date: {issue} → {fixed_issue}")
                            extracted_data['issue_date'] = fixed_issue
            except (ValueError, IndexError):
                pass
        
        return extracted_data


    def process_document(self, document_path: str, document_type: str = None) -> Dict:
        """
        Process any document and return extracted data
        
        Args:
            document_path: Path to document file
            document_type: Type of document (SAR, TRANSACTION, KYC)
        
        Returns:
            Dictionary with extracted data and metadata
        """
        start_time = time.time()
        
        logger.info(f"Processing document: {document_path}")
        
        # Auto-detect document type if not provided
        if not document_type:
            from src.utils import validate_document_type
            document_type = validate_document_type(document_path)
            logger.info(f"📋 Auto-detected document type from filename: {document_type}")
        
        # Check if it's a CSV file for direct processing
        if document_path.lower().endswith('.csv'):
            extracted_data = self._process_csv_file(document_path, document_type)
        else:
            # Parse document using LandingAI ADE (or mock)
            response = self.client.parse(
                document=Path(document_path),
                model="dpt-2-latest"
            )
            
            # Extract structured data using Bedrock (or mock)
            extracted_data = self._extract_structured_data(
                document_type=document_type,
                markdown_content=response.markdown
            )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Create appropriate data model
        if document_type == "SAR":
            document_obj = SuspiciousActivityReport(**extracted_data)
        elif document_type == "TRANSACTION":
            document_obj = TransactionRecord(**extracted_data)
        elif document_type == "KYC":
            document_obj = KYCDocument(**extracted_data)
        else:
            raise ValueError(f"Unsupported document type: {document_type}")
        
        logger.info(f"✓ Successfully processed {document_type} document in {processing_time}ms")
        
        return {
            "document_type": document_type,
            "extracted_data": document_obj.dict(),
            "processing_time_ms": processing_time,
            "analysis_id": generate_analysis_id()
        }
    
    def extract_sar_data(self, document_path: str) -> SuspiciousActivityReport:
        """Extract data from Suspicious Activity Report (SAR) forms"""
        result = self.process_document(document_path, "SAR")
        return SuspiciousActivityReport(**result["extracted_data"])
    
    def extract_transaction_data(self, document_path: str) -> TransactionRecord:
        """Extract data from transaction records"""
        result = self.process_document(document_path, "TRANSACTION")
        return TransactionRecord(**result["extracted_data"])
    
    def extract_kyc_data(self, document_path: str) -> KYCDocument:
        """Extract data from KYC documents"""
        result = self.process_document(document_path, "KYC")
        return KYCDocument(**result["extracted_data"])
    
    def _extract_structured_data(self, document_type: str, markdown_content: str) -> Dict:
        """
        Extract structured data using Groq LLM
        """
        import os
        
        # Check if we have actual content to process
        if not markdown_content or len(markdown_content.strip()) < 50:
            logger.warning("⚠️ No meaningful document content, using defaults")
            return mock_bedrock_extraction(document_type, markdown_content)
        
        # Check if Groq is available
        groq_key = os.getenv('GROQ_API_KEY')
        if groq_key:
            logger.info("🤖 Using Groq LLM for intelligent extraction")
            logger.info(f"📄 Document content preview: {markdown_content[:500]}...")
            try:
                return self._extract_with_groq(document_type, markdown_content)
            except Exception as e:
                logger.error(f"❌ Groq extraction failed: {e}, trying regex fallback")
                # Try regex extraction for passport/KYC documents
                if document_type.upper() in ["KYC", "PASSPORT", "ID"]:
                    regex_result = regex_extract_passport_data(markdown_content)
                    if regex_result.get("full_name") or regex_result.get("last_name"):
                        logger.info(f"✅ Regex extraction successful: {regex_result.get('full_name', 'Unknown')}")
                        return regex_result
                logger.warning("⚠️ Regex extraction failed, falling back to mock")
                return mock_bedrock_extraction(document_type, markdown_content)
        else:
            logger.warning("⚠️ GROQ_API_KEY not set, using mock extraction")
            return mock_bedrock_extraction(document_type, markdown_content)

    def _extract_with_bedrock(self, document_type: str, markdown_content: str) -> Dict:
        """Use Bedrock Claude to intelligently extract structured data"""
        
        try:
            import boto3
            
            bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')
            
            # Create extraction prompt based on document type
            prompts = {
                "SAR": """Extract the following information from the SAR form and return as JSON:
                - report_id: The SAR report ID/number
                - filing_date: Date the SAR was filed
                - filing_institution: Bank/institution filing the SAR
                - subject_name: Name of the suspicious subject
                - subject_account: Account number involved
                - transaction_amount: Amount of suspicious transaction
                - transaction_date: Date of transaction
                - suspicious_activity_type: Type of suspicious activity
                - narrative: Summary of suspicious activity
                
                Document content:
                {content}
                
                Return only valid JSON with these fields and confidence_scores.""",
                
                "TRANSACTION": """Extract transaction details and return as JSON:
                - transaction_id: Unique transaction ID
                - transaction_date: Date of transaction
                - originator_name: Name of sender
                - originator_account: Sender account number
                - beneficiary_name: Name of receiver
                - beneficiary_account: Receiver account number
                - amount: Transaction amount
                - currency: Currency (USD, EUR, etc.)
                - purpose: Purpose of transaction
                
                Document content:
                {content}
                
                Return only valid JSON with these fields and confidence_scores.""",
                
                "KYC": """Extract KYC document information and return as JSON:
                - customer_id: Customer ID if available
                - full_name: Full legal name
                - date_of_birth: DOB in YYYY-MM-DD format
                - nationality: Country of citizenship
                - document_type: Type of ID document
                - document_number: ID document number
                - issue_date: Date issued
                - expiry_date: Date expires
                - address: Current address
                - politically_exposed_person: boolean
                
                Document content:
                {content}
                
                Return only valid JSON with these fields and confidence_scores."""
            }
            
            prompt = prompts.get(document_type, "")
            
            # Call Bedrock Claude with updated model
            response = bedrock_client.invoke_model(
                modelId="anthropic.claude-sonnet-4-5-20250929-v1:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-06-01",
                    "max_tokens": 1024,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt.format(content=markdown_content)
                        }
                    ]
                })
            )
            
            response_body = json.loads(response['body'].read())
            response_text = response_body['content'][0]['text']
            
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            json_str = response_text[json_start:json_end]
            extracted_data = json.loads(json_str)
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Bedrock extraction failed: {e}")
            # Fall back to mock extraction
            return mock_bedrock_extraction(document_type, markdown_content)
    
    def _process_csv_file(self, csv_path: str, document_type: str) -> Dict:
        """Process CSV file directly without LandingAI"""
        try:
            import pandas as pd
            
            # Read CSV file
            df = pd.read_csv(csv_path)
            logger.info(f"CSV loaded: {len(df)} rows, {len(df.columns)} columns")
            
            # Get first row as sample (or aggregate if multiple rows)
            if len(df) == 0:
                raise ValueError("CSV file is empty")
            
            # Take first row for single transaction analysis
            first_row = df.iloc[0].to_dict()
            
            # Map CSV columns to expected transaction fields
            extracted_data = self._map_csv_to_transaction(first_row, df)
            
            # Add confidence scores
            extracted_data["confidence_scores"] = {
                key: 0.95 for key in extracted_data.keys() 
                if key != "confidence_scores"
            }
            
            logger.info(f"✓ CSV processed: {len(df)} transactions found")
            return extracted_data
            
        except Exception as e:
            logger.error(f"CSV processing failed: {e}")
            # Fall back to mock data
            return mock_bedrock_extraction(document_type, f"CSV file with error: {e}")
    
    def _map_csv_to_transaction(self, first_row: Dict, df) -> Dict:
        """Map CSV columns to transaction record format"""
        
        # Common CSV column mappings (flexible)
        column_mappings = {
            'transaction_id': ['id', 'transaction_id', 'txn_id', 'reference', 'ref'],
            'transaction_date': ['date', 'transaction_date', 'txn_date', 'timestamp'],
            'originator_name': ['from', 'sender', 'originator', 'from_name', 'sender_name'],
            'originator_account': ['from_account', 'sender_account', 'orig_account'],
            'beneficiary_name': ['to', 'receiver', 'beneficiary', 'to_name', 'receiver_name'],
            'beneficiary_account': ['to_account', 'receiver_account', 'ben_account'],
            'amount': ['amount', 'value', 'sum', 'transaction_amount'],
            'currency': ['currency', 'curr', 'ccy'],
            'purpose': ['purpose', 'description', 'memo', 'reference', 'details']
        }
        
        # Map columns
        mapped_data = {}
        csv_columns = [col.lower().replace(' ', '_') for col in first_row.keys()]
        
        for field, possible_columns in column_mappings.items():
            value = None
            
            # Try to find matching column
            for possible_col in possible_columns:
                for csv_col, csv_value in first_row.items():
                    if possible_col in csv_col.lower().replace(' ', '_'):
                        value = csv_value
                        break
                if value is not None:
                    break
            
            # Set default values if not found
            if value is None:
                if field == 'transaction_id':
                    value = f"CSV-{hash(str(first_row)) % 100000}"
                elif field == 'transaction_date':
                    value = datetime.utcnow().strftime('%Y-%m-%d')
                elif field == 'currency':
                    value = "USD"
                elif field in ['originator_name', 'beneficiary_name']:
                    value = "Unknown Entity"
                elif field in ['originator_account', 'beneficiary_account']:
                    value = "Unknown Account"
                elif field == 'amount':
                    # Try to find any numeric column
                    for csv_value in first_row.values():
                        try:
                            value = float(str(csv_value).replace('$', '').replace(',', ''))
                            break
                        except:
                            continue
                    if value is None:
                        value = 0.0
                else:
                    value = "Not specified"
            
            mapped_data[field] = value
        
        # Add CSV metadata
        mapped_data['csv_rows_count'] = len(df)
        mapped_data['csv_columns'] = list(df.columns)
        
        return mapped_data

    def _has_aws_credentials(self) -> bool:
        """Check if Groq API key is available"""
        try:
            api_key = os.getenv('GROQ_API_KEY')
            return api_key is not None and len(api_key) > 0
        except:
            return False


# Example usage

    def _extract_with_groq(self, document_type: str, content: str) -> Dict:
        """Use Groq LLM to intelligently extract structured data from documents"""
        from dotenv import load_dotenv
        from groq import Groq
        load_dotenv()
        
        client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        
        prompts = {
            "SAR": """Extract the following from this Suspicious Activity Report. Return ONLY valid JSON:
{
    "report_id": "extracted or generated SAR-XXXXX",
    "filing_date": "YYYY-MM-DD",
    "filing_institution": "institution name",
    "subject_name": "person/entity name",
    "subject_account": "account number",
    "transaction_amount": 0.00,
    "transaction_date": "YYYY-MM-DD",
    "suspicious_activity_type": "activity type",
    "narrative": "brief summary",
    "confidence_scores": {"subject_name": 0.95}
}""",
            "TRANSACTION": """Extract transaction details. Return ONLY valid JSON:
{
    "transaction_id": "TXN-XXXXX",
    "transaction_date": "YYYY-MM-DD",
    "originator_name": "sender",
    "originator_account": "account",
    "beneficiary_name": "receiver",
    "beneficiary_account": "account",
    "amount": 0.00,
    "currency": "USD",
    "purpose": "purpose",
    "confidence_scores": {"amount": 0.95}
}""",
            "KYC": """Extract identity document information from this document. Return ONLY valid JSON.

IMPORTANT PARSING RULES:
1. For FULL NAME: Extract ONLY the person's actual name (Given Names + Surname). 
   - DO NOT include country codes like "MUS", "GBR", "USA" in the name
   - DO NOT include "P<" or other MRZ codes in the name
   - The name is usually in format "SURNAME, GIVEN NAMES" or "GIVEN NAMES SURNAME"
   - Example: If you see "MUS ESMAEL NIGAAR" the country is MUS (Mauritius), name is "ESMAEL NIGAAR"

2. For DATE OF BIRTH: Look for fields labeled "Date of Birth", "DOB", "Date de naissance", "Né(e) le"
   - Convert to YYYY-MM-DD format
   - Common formats: "19 AUG 1967" -> "1967-08-19", "19/08/1967" -> "1967-08-19"

3. For DOCUMENT NUMBER: This is the passport/ID number, NOT the MRZ line
   - Usually 6-9 alphanumeric characters
   - NOT the long MRZ code at the bottom of the passport

4. For NATIONALITY: Extract the country name, not the code
   - "MUS" = "Mauritius", "GBR" = "United Kingdom", "USA" = "United States"

Return this JSON structure:
{
    "customer_id": "CUST-XXXXX",
    "full_name": "GIVEN_NAME FATHER_NAME SURNAME",
    "date_of_birth": "YYYY-MM-DD",
    "nationality": "Full country name",
    "document_type": "Passport/ID Card/License",
    "document_number": "actual document number",
    "issue_date": "YYYY-MM-DD",
    "expiry_date": "YYYY-MM-DD",
    "address": "address if available or Not provided",
    "politically_exposed_person": false,
    "confidence_scores": {"full_name": 0.95, "document_number": 0.98}
}

CRITICAL: Always set "politically_exposed_person" to false. PEP status will be checked separately."""
        }
        
        prompt = f"""{prompts.get(document_type, prompts['KYC'])}

DOCUMENT CONTENT:
{content[:4000]}

IMPORTANT: Extract REAL data from the document. Return ONLY valid JSON."""

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1024
        )
        
        response_text = response.choices[0].message.content
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            extracted = json.loads(response_text[json_start:json_end])
            logger.info(f"✅ Groq extracted: {list(extracted.keys())}")
            
            # Ensure all required fields have valid default values (not None)
            defaults = {
                "customer_id": "CUST-" + str(hash(content))[:6].upper(),
                "full_name": "Unknown",
                "date_of_birth": "1990-01-01",
                "nationality": "Unknown",
                "document_type": "Unknown",
                "document_number": "Unknown",
                "issue_date": "2020-01-01",
                "expiry_date": "2030-01-01",
                "address": "Not provided",
                "politically_exposed_person": False,
                "confidence_scores": {"extraction": 0.5},
                "report_id": "SAR-" + str(hash(content))[:6].upper(),
                "filing_date": "2024-01-01",
                "filing_institution": "Unknown",
                "subject_name": "Unknown",
                "subject_account": "Unknown",
                "transaction_amount": 0.0,
                "transaction_date": "2024-01-01",
                "suspicious_activity_type": "Unknown",
                "narrative": "Extracted from document",
                "transaction_id": "TXN-" + str(hash(content))[:6].upper(),
                "originator_name": "Unknown",
                "originator_account": "Unknown",
                "beneficiary_name": "Unknown",
                "beneficiary_account": "Unknown",
                "amount": 0.0,
                "currency": "USD",
                "purpose": "Unknown"
            }
            
            # Replace None values with defaults
            for key, default_value in defaults.items():
                if key in extracted and extracted[key] is None:
                    extracted[key] = default_value
                elif key not in extracted:
                    extracted[key] = default_value
            
            # Fix confidence_scores - ensure no None values inside
            if "confidence_scores" in extracted and isinstance(extracted["confidence_scores"], dict):
                for k, v in extracted["confidence_scores"].items():
                    if v is None:
                        extracted["confidence_scores"][k] = 0.5
            else:
                extracted["confidence_scores"] = {"extraction": 0.5}
            
            logger.info(f"📋 Final extracted data: {extracted}")
            return extracted
        else:
            raise ValueError("Could not extract JSON from Groq response")



if __name__ == "__main__":
    processor = DocumentProcessor(use_mock=False)
    print("Document processor initialized successfully")
