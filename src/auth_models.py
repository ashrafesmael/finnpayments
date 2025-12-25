"""
Authentication models and database for VORTEX-AML
"""
import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from enum import Enum
import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

class UserStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

# Pydantic models for API
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    status: str
    created_at: str
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class UserApproval(BaseModel):
    user_id: str
    action: str  # "approve" or "reject"

# Database manager for auth
class AuthDatabase:
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), '..', 'aml_auth.db')
        self.db_path = db_path
        self._init_db()
    
    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """Initialize the auth database tables"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                status TEXT DEFAULT 'pending',
                created_at TEXT NOT NULL,
                approved_by TEXT,
                approved_at TEXT
            )
        ''')
        
        # Sessions table for token management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Create default admin if not exists
        self._create_default_admin()
    
    def _hash_password(self, password: str) -> str:
        """Hash password with salt"""
        salt = "vortex_aml_salt_2024"  # In production, use per-user salt
        return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    
    def _create_default_admin(self):
        """Create default admin account if no admin exists"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        
        if admin_count == 0:
            admin_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO users (id, email, password_hash, full_name, role, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                admin_id,
                'admin@montchoisy.com',
                self._hash_password('VortexAdmin2024!'),
                'System Administrator',
                'admin',
                'approved',
                datetime.utcnow().isoformat()
            ))
            conn.commit()
            logger.info(f"✅ Default admin account created: admin@montchoisy.com")
        
        conn.close()
    
    def create_user(self, email: str, password: str, full_name: str) -> Optional[dict]:
        """Create a new user (pending approval)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            return None
        
        user_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO users (id, email, password_hash, full_name, role, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            email.lower(),
            self._hash_password(password),
            full_name,
            'user',
            'pending',
            datetime.utcnow().isoformat()
        ))
        conn.commit()
        
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        user = dict(cursor.fetchone())
        conn.close()
        
        logger.info(f"✅ New user registered (pending approval): {email}")
        return user
    
    def authenticate_user(self, email: str, password: str) -> Optional[dict]:
        """Authenticate user and return user data if valid"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM users WHERE email = ? AND password_hash = ?",
            (email.lower(), self._hash_password(password))
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def create_session(self, user_id: str, expires_hours: int = 24) -> str:
        """Create a new session token"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
        
        cursor.execute('''
            INSERT INTO sessions (token, user_id, created_at, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (token, user_id, datetime.utcnow().isoformat(), expires_at.isoformat()))
        conn.commit()
        conn.close()
        
        return token
    
    def validate_session(self, token: str) -> Optional[dict]:
        """Validate session token and return user if valid"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.* FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ? AND s.expires_at > ?
        ''', (token, datetime.utcnow().isoformat()))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def delete_session(self, token: str):
        """Delete a session (logout)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
    
    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """Get user by ID"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def get_all_users(self) -> List[dict]:
        """Get all users (for admin)"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return users
    
    def get_pending_users(self) -> List[dict]:
        """Get all pending users"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE status = 'pending' ORDER BY created_at DESC")
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return users
    
    def approve_user(self, user_id: str, admin_id: str) -> bool:
        """Approve a pending user"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET status = 'approved', approved_by = ?, approved_at = ?
            WHERE id = ? AND status = 'pending'
        ''', (admin_id, datetime.utcnow().isoformat(), user_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if success:
            logger.info(f"✅ User {user_id} approved by {admin_id}")
        return success
    
    def reject_user(self, user_id: str, admin_id: str) -> bool:
        """Reject a pending user"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users SET status = 'rejected', approved_by = ?, approved_at = ?
            WHERE id = ? AND status = 'pending'
        ''', (admin_id, datetime.utcnow().isoformat(), user_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if success:
            logger.info(f"❌ User {user_id} rejected by {admin_id}")
        return success
    
    def delete_user(self, user_id: str) -> bool:
        """Delete a user"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def update_user_role(self, user_id: str, role: str) -> bool:
        """Update user role"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = ? WHERE id = ?", (role, user_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success

# Global auth database instance
auth_db = AuthDatabase()
