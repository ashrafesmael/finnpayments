"""
Email Service for finnpayments Authentication
"""
import smtplib
import os
import logging
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
        self.enabled = bool(self.smtp_user and self.smtp_password)
        
        if not self.enabled:
            logger.warning("⚠️ Email service not configured. Set SMTP_USER and SMTP_PASSWORD in .env")
    
    def _send_email(self, to_email: str, subject: str, html_content: str) -> bool:
        """Send an email"""
        if not self.enabled:
            logger.info(f"📧 Email not sent (not configured): {subject} -> {to_email}")
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
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

# Global email service instance
email_service = EmailService()
