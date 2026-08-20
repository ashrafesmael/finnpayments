"""
Authentication models and database for finnpayments
"""
import uuid
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from enum import Enum
import sqlite3
import os
import logging

logger = logging.getLogger(__name__)

PBKDF2_ROUNDS = 600_000
PBKDF2_SALT_BYTES = 16
_LEGACY_GLOBAL_SALT = "vortex_aml_salt_2024"

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

class CompanyResponse(BaseModel):
    id: str
    code: str
    name: str
    currency: str = "MUR"
    maker_checker_enabled: bool = False
    created_at: str

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    status: str
    created_at: str
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    companies: List[CompanyResponse] = []

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
        
        # Companies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS companies (
                id TEXT PRIMARY KEY,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                currency TEXT DEFAULT 'MUR',
                maker_checker_enabled INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        ''')
        
        # User-Company mapping (many-to-many)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_companies (
                user_id TEXT NOT NULL,
                company_id TEXT NOT NULL,
                assigned_at TEXT NOT NULL,
                PRIMARY KEY (user_id, company_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (company_id) REFERENCES companies(id)
            )
        ''')
        
        # Password reset tokens
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                used INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        # Run migrations for existing databases
        self._migrate_schema()
        
        # Create default admin if not exists
        self._create_default_admin()
        
        # Create default company if none exists
        self._create_default_company()
    
    def _hash_password(self, password: str, rounds: int = PBKDF2_ROUNDS) -> str:
        """Hash password with PBKDF2-HMAC-SHA256 and per-user random salt."""
        salt = secrets.token_bytes(PBKDF2_SALT_BYTES)
        derived = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, rounds)
        return f"pbkdf2_sha256${rounds}${salt.hex()}${derived.hex()}"

    def _verify_password(self, password: str, stored: str) -> tuple:
        """Verify a password against a stored hash. Returns (valid, needs_upgrade)."""
        if stored.startswith("pbkdf2_sha256$"):
            _, rounds_s, salt_hex, hash_hex = stored.split("$")
            rounds = int(rounds_s)
            derived = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt_hex), rounds)
            valid = hmac.compare_digest(derived.hex(), hash_hex)
            return valid, valid and rounds < PBKDF2_ROUNDS
        # Legacy bare SHA-256 digest
        legacy_hash = hashlib.sha256(f"{password}{_LEGACY_GLOBAL_SALT}".encode()).hexdigest()
        valid = hmac.compare_digest(legacy_hash, stored)
        return valid, valid
    
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
    
    def _migrate_schema(self):
        """Add missing columns to existing tables (SQLite ALTER TABLE)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        def column_exists(table, column):
            cursor.execute(f"PRAGMA table_info({table})")
            return any(row[1] == column for row in cursor.fetchall())
        
        # Add maker_checker_enabled to companies table for existing DBs
        if not column_exists("companies", "maker_checker_enabled"):
            cursor.execute("ALTER TABLE companies ADD COLUMN maker_checker_enabled INTEGER DEFAULT 0")
            logger.info("✅ Added maker_checker_enabled column to companies")
        
        conn.commit()
        conn.close()
    
    def _create_default_company(self):
        """Create a default company if none exists and assign admin to it."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM companies")
        if cursor.fetchone()[0] == 0:
            company_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO companies (id, code, name, currency, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                company_id,
                'MCG',
                'Mont Choisy Golf',
                'MUR',
                datetime.utcnow().isoformat()
            ))
            conn.commit()
            logger.info(f"✅ Default company created: MCG - Mont Choisy Golf")
        
        # Ensure admin has access to all companies
        cursor.execute("SELECT id FROM users WHERE role = 'admin'")
        for row in cursor.fetchall():
            admin_id = row[0]
            cursor.execute('''
                INSERT OR IGNORE INTO user_companies (user_id, company_id, assigned_at)
                SELECT ?, c.id, ? FROM companies c
            ''', (admin_id, datetime.utcnow().isoformat()))
        
        # Also assign existing approved non-admin users to the default company
        cursor.execute("SELECT id FROM users WHERE role != 'admin' AND status = 'approved'")
        for row in cursor.fetchall():
            user_id = row[0]
            cursor.execute('''
                INSERT OR IGNORE INTO user_companies (user_id, company_id, assigned_at)
                SELECT ?, c.id, ? FROM companies c
            ''', (user_id, datetime.utcnow().isoformat()))
        
        conn.commit()
        conn.close()
    
    # ─── Company methods ──────────────────────────────────
    
    def create_company(self, code: str, name: str, currency: str = 'MUR') -> Optional[dict]:
        """Create a new company."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM companies WHERE code = ?", (code.upper(),))
        if cursor.fetchone():
            conn.close()
            return None
        company_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO companies (id, code, name, currency, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (company_id, code.upper(), name, currency, datetime.utcnow().isoformat()))
        conn.commit()
        company = dict(cursor.execute(
            "SELECT * FROM companies WHERE id = ?", (company_id,)
        ).fetchone())
        conn.close()
        logger.info(f"✅ Company created: {code} - {name}")
        return company
    
    def get_companies(self) -> List[dict]:
        """Get all companies."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM companies ORDER BY name")
        companies = [self._normalize_company(dict(row)) for row in cursor.fetchall()]
        conn.close()
        return companies
    
    def get_company_by_id(self, company_id: str) -> Optional[dict]:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM companies WHERE id = ?", (company_id,))
        row = cursor.fetchone()
        conn.close()
        return self._normalize_company(dict(row)) if row else None
    
    def get_user_companies(self, user_id: str) -> List[dict]:
        """Get companies a user has access to. Admins see all companies."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row and row[0] == 'admin':
            cursor.execute("SELECT * FROM companies ORDER BY name")
        else:
            cursor.execute('''
                SELECT c.* FROM companies c
                JOIN user_companies uc ON c.id = uc.company_id
                WHERE uc.user_id = ?
                ORDER BY c.name
            ''', (user_id,))
        companies = [self._normalize_company(dict(row)) for row in cursor.fetchall()]
        conn.close()
        return companies
    
    @staticmethod
    def _normalize_company(c: dict) -> dict:
        """Normalize maker_checker_enabled from int to bool."""
        if 'maker_checker_enabled' in c:
            c['maker_checker_enabled'] = bool(c['maker_checker_enabled'])
        return c
    
    def assign_user_to_company(self, user_id: str, company_id: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO user_companies (user_id, company_id, assigned_at)
            VALUES (?, ?, ?)
        ''', (user_id, company_id, datetime.utcnow().isoformat()))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def remove_user_from_company(self, user_id: str, company_id: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM user_companies WHERE user_id = ? AND company_id = ?
        ''', (user_id, company_id))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def user_has_company_access(self, user_id: str, company_id: str) -> bool:
        """Check if a user has access to a specific company. Admins have access to all."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return False
        if row[0] == 'admin':
            conn.close()
            return True
        cursor.execute('''
            SELECT 1 FROM user_companies WHERE user_id = ? AND company_id = ?
        ''', (user_id, company_id))
        result = cursor.fetchone() is not None
        conn.close()
        return result
    
    def get_users_for_company(self, company_id: str) -> List[dict]:
        """Get all users assigned to a company."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT u.* FROM users u
            JOIN user_companies uc ON u.id = uc.user_id
            WHERE uc.company_id = ?
            ORDER BY u.full_name
        ''', (company_id,))
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return users
    
    def delete_company(self, company_id: str) -> bool:
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_companies WHERE company_id = ?", (company_id,))
        cursor.execute("DELETE FROM companies WHERE id = ?", (company_id,))
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def update_company_maker_checker(self, company_id: str, enabled: bool) -> bool:
        """Enable or disable maker/checker for a company."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE companies SET maker_checker_enabled = ? WHERE id = ?",
            (1 if enabled else 0, company_id)
        )
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    
    def get_company_user_count(self, company_id: str) -> int:
        """Count users assigned to a company (for maker/checker validation)."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM user_companies WHERE company_id = ?", (company_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
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
        """Authenticate user and return user data if valid. Transparently upgrades legacy hashes."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        user = dict(row)
        stored_hash = user.get('password_hash', '')
        valid, needs_upgrade = self._verify_password(password, stored_hash)
        if not valid:
            conn.close()
            return None
        # Transparently upgrade legacy hash to PBKDF2
        if needs_upgrade:
            new_hash = self._hash_password(password)
            cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user['id']))
            conn.commit()
            logger.info(f"🔄 Upgraded password hash for {email}")
        conn.close()
        return user
    
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

    # ─── Password Reset ───────────────────────────────────
    
    def create_password_reset_token(self, user_id: str) -> str:
        """Create a password reset token (valid for 1 hour)."""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO password_reset_tokens (token, user_id, created_at, expires_at, used)
            VALUES (?, ?, ?, ?, 0)
        ''', (token, user_id, datetime.utcnow().isoformat(), expires_at.isoformat()))
        conn.commit()
        conn.close()
        return token
    
    def validate_password_reset_token(self, token: str) -> Optional[dict]:
        """Validate a password reset token. Returns the user if valid."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT t.user_id, u.email, u.full_name FROM password_reset_tokens t
            JOIN users u ON t.user_id = u.id
            WHERE t.token = ? AND t.used = 0 AND t.expires_at > ?
        ''', (token, datetime.utcnow().isoformat()))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def reset_password(self, token: str, new_password: str) -> Optional[dict]:
        """Reset a user's password using a valid token. Returns user dict on success."""
        user_info = self.validate_password_reset_token(token)
        if not user_info:
            return None
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (self._hash_password(new_password), user_info['user_id'])
        )
        cursor.execute(
            "UPDATE password_reset_tokens SET used = 1 WHERE token = ?",
            (token,)
        )
        # Invalidate all sessions for this user (force re-login)
        cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_info['user_id'],))
        conn.commit()
        conn.close()
        logger.info(f"✅ Password reset for {user_info['email']}")
        return user_info
    
    def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get user by email."""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

# Global auth database instance
auth_db = AuthDatabase()
