"""
Email Service for finnpayments Authentication
"""
import smtplib
import os
import time
import base64
import logging
import httpx
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('SMTP_FROM_EMAIL', self.smtp_user)
        self.from_name = os.getenv('SMTP_FROM_NAME', 'finnpayments')

        # Microsoft Graph sending (preferred when configured): app-only OAuth,
        # sends as MS_GRAPH_SENDER (e.g. no-reply@finnpact.com). No passwords, no
        # SMTP AUTH, HTTPS only, DKIM-signed by M365 -> inbox. Falls back to SMTP.
        self.graph_tenant = os.getenv('MS_GRAPH_TENANT_ID', '').strip()
        self.graph_client = os.getenv('MS_GRAPH_CLIENT_ID', '').strip()
        self.graph_secret = os.getenv('MS_GRAPH_CLIENT_SECRET', '').strip()
        self.graph_sender = (os.getenv('MS_GRAPH_SENDER', '') or self.from_email or '').strip()
        self.use_graph = bool(self.graph_tenant and self.graph_client and self.graph_secret and self.graph_sender)
        self._graph_tok = None
        self._graph_tok_exp = 0

        self.enabled = self.use_graph or bool(self.smtp_user and self.smtp_password)

        if self.use_graph:
            logger.info(f"📧 Email via Microsoft Graph as {self.graph_sender}")
        elif not self.enabled:
            logger.warning("⚠️ Email service not configured. Set MS_GRAPH_* or SMTP_USER/SMTP_PASSWORD in .env")

    def _graph_token(self) -> str:
        """App-only OAuth token for Microsoft Graph (cached until ~1 min before expiry)."""
        if self._graph_tok and time.time() < self._graph_tok_exp - 60:
            return self._graph_tok
        r = httpx.post(
            f"https://login.microsoftonline.com/{self.graph_tenant}/oauth2/v2.0/token",
            data={
                "client_id": self.graph_client,
                "client_secret": self.graph_secret,
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            },
            timeout=20.0,
        )
        r.raise_for_status()
        j = r.json()
        self._graph_tok = j["access_token"]
        self._graph_tok_exp = time.time() + int(j.get("expires_in", 3600))
        return self._graph_tok

    def _graph_send(self, to_email: str, subject: str, html_content: str,
                    from_name: str = None, attachment_bytes: bytes = None,
                    attachment_name: str = None, attachment_mime: str = "application/pdf") -> bool:
        """Send via Microsoft Graph /sendMail as self.graph_sender. Optional attachment."""
        try:
            token = self._graph_token()
            message = {
                "subject": subject,
                "body": {"contentType": "HTML", "content": html_content},
                "toRecipients": [{"emailAddress": {"address": to_email}}],
            }
            if from_name:
                message["from"] = {"emailAddress": {"name": from_name, "address": self.graph_sender}}
            if attachment_bytes and attachment_name:
                message["attachments"] = [{
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "name": attachment_name,
                    "contentType": attachment_mime,
                    "contentBytes": base64.b64encode(attachment_bytes).decode("ascii"),
                }]
            r = httpx.post(
                f"https://graph.microsoft.com/v1.0/users/{self.graph_sender}/sendMail",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"message": message, "saveToSentItems": False},
                timeout=30.0,
            )
            if r.status_code in (200, 202):
                logger.info(f"✅ Email sent (Graph): {subject} -> {to_email}")
                return True
            logger.error(f"❌ Graph sendMail failed [{r.status_code}]: {r.text[:400]}")
            return False
        except Exception as e:
            logger.error(f"❌ Graph send error: {e}")
            return False

    def _send_email(self, to_email: str, subject: str, html_content: str, from_name: str = None,
                    attachment_bytes: bytes = None, attachment_name: str = None,
                    attachment_mime: str = "application/pdf") -> bool:
        """Send an email. Optional from_name and attachment."""
        if not self.enabled:
            logger.info(f"📧 Email not sent (not configured): {subject} -> {to_email}")
            return False

        if self.use_graph:
            return self._graph_send(to_email, subject, html_content, from_name=from_name,
                                   attachment_bytes=attachment_bytes, attachment_name=attachment_name,
                                   attachment_mime=attachment_mime)

        try:
            if attachment_bytes and attachment_name:
                msg = MIMEMultipart('mixed')
                html_part = MIMEMultipart('alternative')
                html_part.attach(MIMEText(html_content, 'html'))
                msg.attach(html_part)
                from email.mime.base import MIMEBase
                from email import encoders
                maintype, subtype = attachment_mime.split('/', 1)
                part = MIMEBase(maintype, subtype)
                part.set_payload(attachment_bytes)
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{attachment_name}"')
                msg.attach(part)
            else:
                msg = MIMEMultipart('alternative')
                msg.attach(MIMEText(html_content, 'html'))

            msg['Subject'] = subject
            msg['From'] = f"{from_name or self.from_name} <{self.from_email}>"
            msg['To'] = to_email

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, to_email, msg.as_string())

            logger.info(f"✅ Email sent: {subject} -> {to_email}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to send email: {e}")
            return False
    
    def send_registration_confirmation(self, to_email: str, full_name: str) -> bool:
        """Send registration confirmation email"""
        subject = "finnpayments - Registration Received"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #64748b; font-size: 12px; }}
                .status {{ background: #fef3c7; border: 1px solid #f59e0b; color: #92400e; padding: 15px; border-radius: 8px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>finnpayments</h1>
                    <p>AI Invoice Processing & Accounting</p>
                </div>
                <div class="content">
                    <h2>Welcome, {full_name}!</h2>
                    <p>Thank you for registering with finnpayments. Your registration has been received successfully.</p>
                    
                    <div class="status">
                        <strong>⏳ Account Status: Pending Approval</strong>
                        <p>Your account is currently awaiting administrator approval. You will receive another email once your account has been reviewed.</p>
                    </div>
                    
                    <p>This process typically takes 1-2 business days. If you have any questions, please contact your system administrator.</p>
                    
                    <p>Best regards,<br>finnpayments Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from finnpayments. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return self._send_email(to_email, subject, html_content)
    
    def send_approval_notification(self, to_email: str, full_name: str, login_url: str = "") -> bool:
        """Send account approved notification"""
        subject = "finnpayments - Account Approved ✓"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #64748b; font-size: 12px; }}
                .status {{ background: #dcfce7; border: 1px solid #22c55e; color: #166534; padding: 15px; border-radius: 8px; margin: 20px 0; }}
                .button {{ display: inline-block; background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 12px 30px; text-decoration: none; border-radius: 8px; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>finnpayments</h1>
                    <p>AI Invoice Processing & Accounting</p>
                </div>
                <div class="content">
                    <h2>Good news, {full_name}!</h2>
                    
                    <div class="status">
                        <strong>✅ Account Status: Approved</strong>
                        <p>Your account has been approved by an administrator. You can now log in to access the finnpayments system.</p>
                    </div>
                    
                    <p>You can now:</p>
                    <ul>
                        <li>Upload and process invoices with AI-powered extraction</li>
                        <li>Generate double-entry accounting journal entries automatically</li>
                        <li>Review and post journal entries to the general ledger</li>
                        <li>Export entries to Sage 200 Evolution</li>
                    </ul>
                    
                    {f'<p><a href="{login_url}" class="button">Login to finnpayments</a></p>' if login_url else ''}
                    
                    <p>Best regards,<br>finnpayments Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from finnpayments. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return self._send_email(to_email, subject, html_content)
    
    def send_rejection_notification(self, to_email: str, full_name: str, reason: str = "") -> bool:
        """Send account rejected notification"""
        subject = "finnpayments - Account Registration Update"
        reason_text = f"<p><strong>Reason:</strong> {reason}</p>" if reason else ""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #64748b; font-size: 12px; }}
                .status {{ background: #fee2e2; border: 1px solid #ef4444; color: #991b1b; padding: 15px; border-radius: 8px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>finnpayments</h1>
                    <p>AI Invoice Processing & Accounting</p>
                </div>
                <div class="content">
                    <h2>Dear {full_name},</h2>
                    
                    <div class="status">
                        <strong>❌ Account Status: Not Approved</strong>
                        <p>Unfortunately, your account registration could not be approved at this time.</p>
                        {reason_text}
                    </div>
                    
                    <p>If you believe this decision was made in error, or if you have additional information to provide, please contact your system administrator.</p>
                    
                    <p>Best regards,<br>finnpayments Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from finnpayments. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return self._send_email(to_email, subject, html_content)

    def send_password_reset(self, to_email: str, full_name: str, reset_token: str, base_url: str = "") -> bool:
        """Send password reset email with link."""
        if not base_url:
            base_url = os.getenv('SITE_BASE_URL', 'https://payments.finnverify.com')
        reset_link = f"{base_url}/reset-password?token={reset_token}"
        subject = "finnpayments - Password Reset"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #64748b; font-size: 12px; }}
                .btn {{ display: inline-block; background: #10b981; color: white; padding: 12px 30px; border-radius: 6px; text-decoration: none; font-weight: 600; margin: 20px 0; }}
                .note {{ background: #fef3c7; border: 1px solid #f59e0b; color: #92400e; padding: 12px; border-radius: 8px; margin: 20px 0; font-size: 14px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>finnpayments</h1>
                    <p>AI Invoice Processing & Accounting</p>
                </div>
                <div class="content">
                    <h2>Dear {full_name},</h2>
                    <p>A password reset was requested for your account. Click the button below to set a new password:</p>
                    <div style="text-align: center;">
                        <a href="{reset_link}" class="btn">Reset Password</a>
                    </div>
                    <div class="note">
                        <strong>This link expires in 1 hour.</strong> If you did not request a password reset, you can safely ignore this email.
                    </div>
                    <p>If the button doesn't work, copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #10b981; font-size: 13px;">{reset_link}</p>
                    <p>Best regards,<br>finnpayments Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from finnpayments. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return self._send_email(to_email, subject, html_content)

    def send_invoice_approved(self, to_email: str, full_name: str, invoice_number: str,
                              vendor_name: str, amount: float, currency: str, login_url: str = "") -> bool:
        """Notify that an invoice is approved and needs posting (maker/checker context)."""
        subject = "finnpayments - Invoice Approved, Ready for Posting"
        reset_link = f'<p><a href="{login_url}" class="btn">View & Post Invoice</a></p>' if login_url else ''
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #64748b; font-size: 12px; }}
                .btn {{ display: inline-block; background: #10b981; color: white; padding: 12px 30px; border-radius: 6px; text-decoration: none; font-weight: 600; margin: 20px 0; }}
                .status {{ background: #dcfce7; border: 1px solid #22c55e; color: #166534; padding: 15px; border-radius: 8px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>finnpayments</h1>
                    <p>AI Invoice Processing & Accounting</p>
                </div>
                <div class="content">
                    <h2>Dear {full_name},</h2>
                    <div class="status">
                        <strong>Invoice Approved &mdash; Ready for Posting</strong>
                        <p>Invoice <strong>{invoice_number}</strong> from <strong>{vendor_name}</strong> for <strong>{currency} {amount:,.2f}</strong> has been approved and is now ready to be posted to the General Ledger.</p>
                    </div>
                    <p>Please review and post this invoice at your earliest convenience.</p>
                    {reset_link}
                    <p>Best regards,<br>finnpayments Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from finnpayments. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return self._send_email(to_email, subject, html_content)

    def send_invoice_rejected(self, to_email: str, full_name: str, invoice_number: str,
                               vendor_name: str, amount: float, currency: str, reason: str = "") -> bool:
        """Notify that an invoice was rejected."""
        reason_text = f"<p><strong>Reason:</strong> {reason}</p>" if reason else ""
        subject = "finnpayments - Invoice Rejected"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #64748b; font-size: 12px; }}
                .status {{ background: #fee2e2; border: 1px solid #ef4444; color: #991b1b; padding: 15px; border-radius: 8px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>finnpayments</h1>
                    <p>AI Invoice Processing & Accounting</p>
                </div>
                <div class="content">
                    <h2>Dear {full_name},</h2>
                    <div class="status">
                        <strong>Invoice Rejected</strong>
                        <p>Invoice <strong>{invoice_number}</strong> from <strong>{vendor_name}</strong> for <strong>{currency} {amount:,.2f}</strong> has been rejected.</p>
                        {reason_text}
                    </div>
                    <p>If you believe this was done in error, please contact your system administrator.</p>
                    <p>Best regards,<br>finnpayments Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from finnpayments. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return self._send_email(to_email, subject, html_content)

    def send_invoice_posted(self, to_email: str, full_name: str, invoice_number: str,
                            vendor_name: str, amount: float, currency: str, login_url: str = "") -> bool:
        """Notify that an invoice has been posted to the GL and is ready for payment."""
        reset_link = f'<p><a href="{login_url}" class="btn">View Invoice</a></p>' if login_url else ''
        subject = "finnpayments - Invoice Posted to GL, Ready for Payment"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #64748b; font-size: 12px; }}
                .btn {{ display: inline-block; background: #10b981; color: white; padding: 12px 30px; border-radius: 6px; text-decoration: none; font-weight: 600; margin: 20px 0; }}
                .status {{ background: #dcfce7; border: 1px solid #22c55e; color: #166534; padding: 15px; border-radius: 8px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>finnpayments</h1>
                    <p>AI Invoice Processing & Accounting</p>
                </div>
                <div class="content">
                    <h2>Dear {full_name},</h2>
                    <div class="status">
                        <strong>Invoice Posted &mdash; Ready for Payment</strong>
                        <p>Invoice <strong>{invoice_number}</strong> from <strong>{vendor_name}</strong> for <strong>{currency} {amount:,.2f}</strong> has been posted to the General Ledger and is now ready for payment.</p>
                    </div>
                    {reset_link}
                    <p>Best regards,<br>finnpayments Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from finnpayments. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        return self._send_email(to_email, subject, html_content)

    def send_new_invoice_uploaded(self, to_email: str, full_name: str, invoice_number: str,
                                   vendor_name: str, amount: float, currency: str, login_url: str = "",
                                   attachment_path: str = None, approve_url: str = None, decline_url: str = None) -> bool:
        """Notify approvers that a new invoice has been uploaded and needs review.
        Optionally attaches the invoice PDF and includes approve/decline buttons."""
        subject = f"finnpayments - New Invoice Needs Review: {invoice_number}"

        # Build action buttons if URLs are provided
        action_buttons = ""
        if approve_url and decline_url:
            action_buttons = f"""
            <div style="text-align: center; margin: 28px 0;">
                <a href="{approve_url}" style="display: inline-block; background: #10b981; color: white; padding: 14px 36px; border-radius: 8px; text-decoration: none; font-weight: 700; font-size: 16px; margin: 0 8px;">✓ Approve</a>
                <a href="{decline_url}" style="display: inline-block; background: #ef4444; color: white; padding: 14px 36px; border-radius: 8px; text-decoration: none; font-weight: 700; font-size: 16px; margin: 0 8px;">✕ Decline</a>
            </div>
            <p style="color: #64748b; font-size: 12px; text-align: center; margin: 8px 0;">Or click the buttons above to approve or decline this invoice directly from this email. These links expire in 3 days.</p>
            """

        reset_link = f'<p><a href="{login_url}" class="btn">Review in finnpayments</a></p>' if login_url else ''
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
                .content {{ background: #f8fafc; padding: 30px; border-radius: 0 0 10px 10px; }}
                .footer {{ text-align: center; margin-top: 20px; color: #64748b; font-size: 12px; }}
                .btn {{ display: inline-block; background: #10b981; color: white; padding: 12px 30px; border-radius: 6px; text-decoration: none; font-weight: 600; margin: 20px 0; }}
                .status {{ background: #fef3c7; border: 1px solid #f59e0b; color: #92400e; padding: 15px; border-radius: 8px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>finnpayments</h1>
                    <p>AI Invoice Processing & Accounting</p>
                </div>
                <div class="content">
                    <h2>Dear {full_name},</h2>
                    <div class="status">
                        <strong>New Invoice Uploaded &mdash; Pending Review</strong>
                        <p>Invoice <strong>{invoice_number}</strong> from <strong>{vendor_name}</strong> for <strong>{currency} {amount:,.2f}</strong> has been uploaded and needs your review.</p>
                    </div>
                    <p>A copy of the invoice is attached to this email for your convenience.</p>
                    {action_buttons}
                    <p style="color: #64748b; font-size: 13px;">Prefer to review the full details? Log in to finnpayments:</p>
                    {reset_link}
                    <p>Best regards,<br>finnpayments Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from finnpayments. Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """
        # Read attachment file if provided
        attachment_bytes = None
        attachment_name = None
        if attachment_path and os.path.exists(attachment_path):
            try:
                with open(attachment_path, 'rb') as f:
                    attachment_bytes = f.read()
                attachment_name = os.path.basename(attachment_path)
            except Exception as e:
                logger.error(f"Failed to read attachment {attachment_path}: {e}")

        return self._send_email(to_email, subject, html_content, attachment_bytes=attachment_bytes,
                               attachment_name=attachment_name)

# Global email service instance
email_service = EmailService()
