"""
Authentication API endpoints for finnverify
"""
from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional
from .auth_models import (
    auth_db, UserCreate, UserLogin, UserResponse, 
    TokenResponse, UserApproval, UserRole, UserStatus
)
from .email_service import email_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

def get_current_user(authorization: Optional[str] = Header(None)):
    """Dependency to get current authenticated user"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Extract token from "Bearer <token>"
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

@router.post("/register", response_model=dict)
async def register(user_data: UserCreate):
    """Register a new user (requires admin approval)"""
    # Validate password strength
    password = user_data.password
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if not any(c.isupper() for c in password):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?/~`" for c in password):
        raise HTTPException(status_code=400, detail="Password must contain at least one special character (!@#$%^&*etc)")
    
    user = auth_db.create_user(
        email=user_data.email,
        password=user_data.password,
        full_name=user_data.full_name
    )
    
    if not user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Send registration confirmation email
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
async def login(credentials: UserLogin):
    """Login and get access token"""
    user = auth_db.authenticate_user(credentials.email, credentials.password)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if user['status'] == 'pending':
        raise HTTPException(status_code=403, detail="Account pending approval. Please wait for admin to approve your account.")
    
    if user['status'] == 'rejected':
        raise HTTPException(status_code=403, detail="Account has been rejected. Please contact administrator.")
    
    # Create session token
    token = auth_db.create_session(user['id'])
    
    logger.info(f"✅ User logged in: {user['email']}")
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user['id'],
            email=user['email'],
            full_name=user['full_name'],
            role=user['role'],
            status=user['status'],
            created_at=user['created_at'],
            approved_by=user.get('approved_by'),
            approved_at=user.get('approved_at')
        )
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
    return UserResponse(
        id=user['id'],
        email=user['email'],
        full_name=user['full_name'],
        role=user['role'],
        status=user['status'],
        created_at=user['created_at'],
        approved_by=user.get('approved_by'),
        approved_at=user.get('approved_at')
    )

@router.get("/verify")
async def verify_token(user: dict = Depends(get_current_user)):
    """Verify if token is valid"""
    return {
        "valid": True,
        "user": {
            "id": user['id'],
            "email": user['email'],
            "role": user['role'],
            "status": user['status']
        }
    }

# Admin endpoints
@router.get("/admin/users", response_model=list)
async def get_all_users(admin: dict = Depends(require_admin)):
    """Get all users (admin only)"""
    users = auth_db.get_all_users()
    return [
        {
            "id": u['id'],
            "email": u['email'],
            "full_name": u['full_name'],
            "role": u['role'],
            "status": u['status'],
            "created_at": u['created_at'],
            "approved_by": u.get('approved_by'),
            "approved_at": u.get('approved_at')
        }
        for u in users
    ]

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
    # Get user info before approval
    user_info = auth_db.get_user_by_id(user_id)
    
    success = auth_db.approve_user(user_id, admin['id'])
    if not success:
        raise HTTPException(status_code=404, detail="User not found or already processed")
    
    # Send approval notification email
    if user_info:
        email_service.send_approval_notification(user_info['email'], user_info['full_name'])
    
    return {"message": "User approved successfully"}

@router.post("/admin/reject/{user_id}")
async def reject_user(user_id: str, admin: dict = Depends(require_admin)):
    """Reject a pending user (admin only)"""
    # Get user info before rejection
    user_info = auth_db.get_user_by_id(user_id)
    
    success = auth_db.reject_user(user_id, admin['id'])
    if not success:
        raise HTTPException(status_code=404, detail="User not found or already processed")
    
    # Send rejection notification email
    if user_info:
        email_service.send_rejection_notification(user_info['email'], user_info['full_name'])
    
    return {"message": "User rejected successfully"}

@router.delete("/admin/users/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(require_admin)):
    """Delete a user (admin only)"""
    # Prevent deleting self
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
    
    # Prevent demoting self
    if user_id == admin['id'] and role != 'admin':
        raise HTTPException(status_code=400, detail="Cannot demote your own account")
    
    success = auth_db.update_user_role(user_id, role)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": f"User role updated to {role}"}
