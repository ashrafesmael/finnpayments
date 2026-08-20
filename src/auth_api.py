"""
Authentication API endpoints for finnpayments
"""
from fastapi import APIRouter, HTTPException, Depends, Header, Request
from typing import Optional, List
from pydantic import BaseModel
from .auth_models import (
    auth_db, UserCreate, UserLogin, UserResponse,
    TokenResponse, UserApproval, UserRole, UserStatus, CompanyResponse
)
from .email_service import email_service
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/auth", tags=["Authentication"])


def _user_response(user: dict) -> dict:
    """Build a user response dict including accessible companies."""
    companies = auth_db.get_user_companies(user['id'])
    return {
        "id": user['id'],
        "email": user['email'],
        "full_name": user['full_name'],
        "role": user['role'],
        "status": user['status'],
        "created_at": user['created_at'],
        "approved_by": user.get('approved_by'),
        "approved_at": user.get('approved_at'),
        "companies": companies,
    }


def get_current_user(authorization: Optional[str] = Header(None)):
    """Dependency to get current authenticated user"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = parts[1]
    user = auth_db.validate_session(token)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if user['status'] != 'approved':
        raise HTTPException(status_code=403, detail="Account not approved")

    return user


def require_admin(user: dict = Depends(get_current_user)):
    """Dependency to require admin role"""
    if user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def get_current_company(
    x_company_id: Optional[str] = Header(None, alias="X-Company-Id"),
    user: dict = Depends(get_current_user),
) -> dict:
    """Dependency that resolves the active company from the X-Company-Id header.
    Validates that the user has access to the requested company."""
    if not x_company_id:
        raise HTTPException(status_code=400, detail="X-Company-Id header is required")

    company = auth_db.get_company_by_id(x_company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if not auth_db.user_has_company_access(user['id'], company['id']):
        raise HTTPException(status_code=403, detail="You do not have access to this company")

    return company


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


def _validate_password_strength(password: str):
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if not any(c.isupper() for c in password):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?/~`" for c in password):
        raise HTTPException(status_code=400, detail="Password must contain at least one special character (!@#$%^&*etc)")


@router.post("/forgot-password", response_model=dict)
@limiter.limit("3/minute")
async def forgot_password(request: Request, data: ForgotPasswordRequest):
    """Request a password reset link. Always returns success (don't leak whether email exists)."""
    user = auth_db.get_user_by_email(data.email)
    if user and user['status'] == 'approved':
        token = auth_db.create_password_reset_token(user['id'])
        email_service.send_password_reset(user['email'], user['full_name'], token)
        logger.info(f"📧 Password reset requested for {user['email']}")
    else:
        logger.info(f"📧 Password reset requested for unknown/disabled email: {request.email}")
    return {"message": "If an account exists for that email, a password reset link has been sent."}


@router.post("/reset-password", response_model=dict)
@limiter.limit("5/minute")
async def reset_password(request: Request, data: ResetPasswordRequest):
    """Reset password using a valid token."""
    _validate_password_strength(data.new_password)
    user_info = auth_db.reset_password(data.token, data.new_password)
    if not user_info:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    return {"message": "Password reset successfully. Please log in with your new password."}


@router.post("/register", response_model=dict)
@limiter.limit("5/minute")
async def register(request: Request, user_data: UserCreate):
    """Register a new user (requires admin approval)"""
    _validate_password_strength(user_data.password)

    user = auth_db.create_user(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name
    )

    if not user:
        raise HTTPException(status_code=400, detail="Email already registered")

    email_service.send_registration_confirmation(user['email'], user['full_name'])

    return {
        "message": "Registration successful. Please check your email and wait for admin approval.",
        "user": {
            "id": user['id'],
            "email": user['email'],
            "full_name": user['full_name'],
            "status": user['status']
        }
    }


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, credentials: UserLogin):
    """Login and get access token"""
    user = auth_db.authenticate_user(credentials.email, credentials.password)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if user['status'] == 'pending':
        raise HTTPException(status_code=403, detail="Account pending approval. Please wait for admin to approve your account.")

    if user['status'] == 'rejected':
        raise HTTPException(status_code=403, detail="Account has been rejected. Please contact administrator.")

    token = auth_db.create_session(user['id'])
    logger.info(f"✅ User logged in: {user['email']}")

    return TokenResponse(
        access_token=token,
        user=UserResponse(**_user_response(user))
    )


@router.post("/logout")
async def logout(authorization: Optional[str] = Header(None)):
    """Logout and invalidate token"""
    if authorization:
        parts = authorization.split()
        if len(parts) == 2:
            auth_db.delete_session(parts[1])
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """Get current user information"""
    return UserResponse(**_user_response(user))


@router.get("/verify")
async def verify_token(user: dict = Depends(get_current_user)):
    """Verify if token is valid"""
    return {
        "valid": True,
        "user": _user_response(user)
    }


# ─── Admin: User Management ──────────────────────────────

@router.get("/admin/users", response_model=list)
async def get_all_users(admin: dict = Depends(require_admin)):
    """Get all users (admin only)"""
    users = auth_db.get_all_users()
    return [_user_response(u) for u in users]


@router.get("/admin/pending", response_model=list)
async def get_pending_users(admin: dict = Depends(require_admin)):
    """Get pending users (admin only)"""
    users = auth_db.get_pending_users()
    return [
        {
            "id": u['id'],
            "email": u['email'],
            "full_name": u['full_name'],
            "created_at": u['created_at']
        }
        for u in users
    ]


@router.post("/admin/approve/{user_id}")
async def approve_user(user_id: str, admin: dict = Depends(require_admin)):
    """Approve a pending user (admin only)"""
    user_info = auth_db.get_user_by_id(user_id)
    success = auth_db.approve_user(user_id, admin['id'])
    if not success:
        raise HTTPException(status_code=404, detail="User not found or already processed")
    if user_info:
        email_service.send_approval_notification(user_info['email'], user_info['full_name'])
    return {"message": "User approved successfully"}


@router.post("/admin/reject/{user_id}")
async def reject_user(user_id: str, admin: dict = Depends(require_admin)):
    """Reject a pending user (admin only)"""
    user_info = auth_db.get_user_by_id(user_id)
    success = auth_db.reject_user(user_id, admin['id'])
    if not success:
        raise HTTPException(status_code=404, detail="User not found or already processed")
    if user_info:
        email_service.send_rejection_notification(user_info['email'], user_info['full_name'])
    return {"message": "User rejected successfully"}


@router.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(require_admin)):
    """Delete a user (admin only)"""
    if user_id == admin['id']:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    success = auth_db.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}


@router.put("/admin/users/{user_id}/role")
async def update_user_role(user_id: str, role: str, admin: dict = Depends(require_admin)):
    """Update user role (admin only)"""
    if role not in ['admin', 'user']:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin' or 'user'")
    if user_id == admin['id'] and role != 'admin':
        raise HTTPException(status_code=400, detail="Cannot demote your own account")
    success = auth_db.update_user_role(user_id, role)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": f"User role updated to {role}"}


# ─── Admin: Company Management ───────────────────────────

class CompanyCreate(BaseModel):
    code: str
    name: str
    currency: str = "MUR"


@router.get("/admin/companies", response_model=list)
async def get_all_companies(admin: dict = Depends(require_admin)):
    """Get all companies (admin only)"""
    companies = auth_db.get_companies()
    result = []
    for c in companies:
        # Include user count per company
        user_list = auth_db.get_users_for_company(c['id']) if hasattr(auth_db, 'get_users_for_company') else []
        result.append({
            **c,
            "user_count": len(user_list) if user_list else 0,
        })
    return result


@router.post("/admin/companies", response_model=CompanyResponse)
async def create_company(company_data: CompanyCreate, admin: dict = Depends(require_admin)):
    """Create a new company (admin only)"""
    if len(company_data.code) < 2:
        raise HTTPException(status_code=400, detail="Company code must be at least 2 characters")
    company = auth_db.create_company(
        code=company_data.code,
        name=company_data.name,
        currency=company_data.currency
    )
    if not company:
        raise HTTPException(status_code=400, detail="Company code already exists")
    return CompanyResponse(**company)


@router.delete("/admin/companies/{company_id}")
async def delete_company(company_id: str, admin: dict = Depends(require_admin)):
    """Delete a company (admin only)"""
    success = auth_db.delete_company(company_id)
    if not success:
        raise HTTPException(status_code=404, detail="Company not found")
    return {"message": "Company deleted successfully"}


class MakerCheckerToggle(BaseModel):
    enabled: bool


@router.put("/admin/companies/{company_id}/maker-checker")
async def toggle_maker_checker(
    company_id: str,
    request: MakerCheckerToggle,
    admin: dict = Depends(require_admin),
):
    """Enable or disable maker/checker for a company (admin only)"""
    company = auth_db.get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if request.enabled:
        user_count = auth_db.get_company_user_count(company_id)
        if user_count < 2:
            raise HTTPException(
                status_code=400,
                detail="Maker/checker requires at least 2 users assigned to this company."
            )

    auth_db.update_company_maker_checker(company_id, request.enabled)
    return {
        "message": f"Maker/checker {'enabled' if request.enabled else 'disabled'} for {company['name']}",
        "maker_checker_enabled": request.enabled,
    }


@router.get("/admin/companies/{company_id}/users", response_model=list)
async def get_company_users(company_id: str, admin: dict = Depends(require_admin)):
    """Get users assigned to a company (admin only)"""
    users = auth_db.get_users_for_company(company_id)
    return [
        {
            "id": u['id'],
            "email": u['email'],
            "full_name": u['full_name'],
            "role": u['role'],
        }
        for u in users
    ]


@router.post("/admin/companies/{company_id}/users/{user_id}")
async def assign_user_to_company(company_id: str, user_id: str, admin: dict = Depends(require_admin)):
    """Assign a user to a company (admin only)"""
    user = auth_db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    company = auth_db.get_company_by_id(company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    auth_db.assign_user_to_company(user_id, company_id)
    return {"message": f"User {user['email']} assigned to {company['name']}"}


@router.delete("/admin/companies/{company_id}/users/{user_id}")
async def remove_user_from_company(company_id: str, user_id: str, admin: dict = Depends(require_admin)):
    """Remove a user from a company (admin only)"""
    if user_id == admin['id']:
        raise HTTPException(status_code=400, detail="Cannot remove yourself from a company")
    success = auth_db.remove_user_from_company(user_id, company_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not assigned to this company")
    return {"message": "User removed from company"}
