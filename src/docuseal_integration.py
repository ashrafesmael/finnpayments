"""
DocuSeal integration for finnpayments — e-signature invoice approval.

DocuSeal API docs: https://api.docuseal.com
Requires DOCUSEAL_API_KEY env var (get from DocuSeal → Settings → API).
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DOCUSEAL_URL = os.getenv('DOCUSEAL_URL', 'http://localhost:3002')
DOCUSEAL_API_KEY = os.getenv('DOCUSEAL_API_KEY', '')
DOCUSEAL_WEBHOOK_SECRET = os.getenv('DOCUSEAL_WEBHOOK_SECRET', '')


def is_configured() -> bool:
    return bool(DOCUSEAL_API_KEY)


async def create_approval_envelope(
    invoice_id: str,
    invoice_number: str,
    vendor_name: str,
    amount: float,
    currency: str,
    approver_email: str,
    approver_name: str,
    document_path: Optional[str] = None,
) -> Optional[dict]:
    """Create a DocuSeal envelope for invoice approval.

    Uploads the invoice PDF (if available) and creates a signature request
    with the approver as the signer. Returns the DocuSeal submission data
    or None on failure.
    """
    if not is_configured():
        logger.warning("DocuSeal not configured — skipping e-signature")
        return None

    import httpx
    import json

    try:
        headers = {
            "Authorization": f"Bearer {DOCUSEAL_API_KEY}",
            "Content-Type": "application/json",
        }

        # Step 1: Upload the document if we have a file
        document_url = None
        if document_path and os.path.exists(document_path):
            with open(document_path, "rb") as f:
                upload_response = await httpx.AsyncClient(timeout=30.0).post(
                    f"{DOCUSEAL_URL}/api/documents",
                    headers={"Authorization": f"Bearer {DOCUSEAL_API_KEY}"},
                    files={"file": (os.path.basename(document_path), f, "application/pdf")},
                )
                if upload_response.status_code in (200, 201):
                    document_url = upload_response.json().get("url")
                    logger.info(f"📄 Uploaded invoice to DocuSeal: {document_url}")

        # Step 2: Create the submission (envelope) with approve/reject fields
        submission_data = {
            "submitters": [
                {
                    "email": approver_email,
                    "name": approver_name,
                    "fields": [
                        {
                            "name": "Approval Signature",
                            "type": "signature",
                            "required": True,
                        },
                        {
                            "name": "Approval Decision",
                            "type": "text",
                            "default_value": "Approved",
                            "options": ["Approved", "Rejected"],
                            "required": True,
                        },
                    ],
                }
            ],
            "metadata": {
                "invoice_id": invoice_id,
                "invoice_number": invoice_number,
                "vendor_name": vendor_name,
                "amount": str(amount),
                "currency": currency,
            },
        }

        if document_url:
            submission_data["documents"] = [{"url": document_url}]

        # If no document, create a text-only approval form
        if not document_url:
            submission_data["documents"] = [{
                "name": f"Invoice {invoice_number}",
                "fields": [
                    {
                        "name": "Invoice Details",
                        "type": "heading",
                        "title": f"Invoice {invoice_number}",
                        "description": f"Vendor: {vendor_name}\nAmount: {currency} {amount:,.2f}\n\nPlease review and sign below to approve this invoice for posting to the General Ledger.",
                    },
                    {
                        "name": "Approval Signature",
                        "type": "signature",
                        "required": True,
                    },
                    {
                        "name": "Approval Decision",
                        "type": "text",
                        "default_value": "Approved",
                        "options": ["Approved", "Rejected"],
                        "required": True,
                    },
                ],
            }]

        response = await httpx.AsyncClient(timeout=30.0).post(
            f"{DOCUSEAL_URL}/api/submissions",
            headers=headers,
            json=submission_data,
        )

        if response.status_code in (200, 201):
            result = response.json()
            logger.info(f"✅ DocuSeal envelope created for invoice {invoice_number}: submission_id={result.get('id')}")
            return result
        else:
            logger.error(f"❌ DocuSeal submission failed [{response.status_code}]: {response.text[:500]}")
            return None

    except Exception as e:
        logger.error(f"❌ DocuSeal integration error: {e}")
        return None


def verify_webhook(headers: dict, body: bytes) -> bool:
    """Verify the DocuSeal webhook signature (if secret is configured)."""
    if not DOCUSEAL_WEBHOOK_SECRET:
        return True  # No secret configured, accept all
    received = headers.get("X-Docuseal-Signature", "")
    import hmac
    import hashlib
    expected = hmac.new(
        DOCUSEAL_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(received, expected)


async def get_submission_status(submission_id: int) -> Optional[dict]:
    """Get the status of a DocuSeal submission."""
    if not is_configured():
        return None

    import httpx

    try:
        response = await httpx.AsyncClient(timeout=15.0).get(
            f"{DOCUSEAL_URL}/api/submissions/{submission_id}",
            headers={"Authorization": f"Bearer {DOCUSEAL_API_KEY}"},
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"❌ DocuSeal status check failed: {e}")
    return None
