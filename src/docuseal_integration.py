"""
DocuSeal integration for finnpayments — e-signature invoice approval.

DocuSeal API docs: https://www.docuseal.com/docs/api
Auth: X-Auth-Token header
Requires DOCUSEAL_API_KEY and DOCUSEAL_TEMPLATE_ID env vars.
"""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DOCUSEAL_URL = os.getenv('DOCUSEAL_URL', 'http://localhost:3002')
DOCUSEAL_API_KEY = os.getenv('DOCUSEAL_API_KEY', '')
DOCUSEAL_TEMPLATE_ID = int(os.getenv('DOCUSEAL_TEMPLATE_ID', '1'))
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
    """Create a DocuSeal submission for invoice approval using the pre-configured template.

    DocuSeal emails the approver with a link to review and sign.
    Returns the submission data or None on failure.
    """
    if not is_configured():
        logger.warning("DocuSeal not configured — skipping e-signature")
        return None

    import httpx

    try:
        response = await httpx.AsyncClient(timeout=30.0).post(
            f"{DOCUSEAL_URL}/api/submissions",
            headers={
                "X-Auth-Token": DOCUSEAL_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "template_id": DOCUSEAL_TEMPLATE_ID,
                "submitters": [
                    {
                        "email": approver_email,
                        "name": approver_name,
                    }
                ],
                "metadata": {
                    "invoice_id": invoice_id,
                    "invoice_number": invoice_number,
                    "vendor_name": vendor_name,
                    "amount": str(amount),
                    "currency": currency,
                },
            },
        )

        if response.status_code in (200, 201):
            data = response.json()
            # DocuSeal returns a list of submitters
            if isinstance(data, list) and len(data) > 0:
                submission_id = data[0].get("submission_id")
                logger.info(f"✅ DocuSeal envelope created for invoice {invoice_number}: submission_id={submission_id}")
                return {"id": submission_id, "submitters": data}
            elif isinstance(data, dict):
                submission_id = data.get("submission_id") or data.get("id")
                logger.info(f"✅ DocuSeal envelope created for invoice {invoice_number}: submission_id={submission_id}")
                return {"id": submission_id, "submitters": [data]}
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
            headers={"X-Auth-Token": DOCUSEAL_API_KEY},
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"❌ DocuSeal status check failed: {e}")
    return None
