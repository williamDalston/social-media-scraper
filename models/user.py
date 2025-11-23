from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import declarative_base
from datetime import datetime
import enum
import bcrypt
from werkzeug.security import generate_password_hash, check_password_hash

# Import Base from schema to ensure same declarative base
from scraper.schema import Base

class UserRole(enum.Enum):
    ADMIN = "Admin"
    EDITOR = "Editor"
    VIEWER = "Viewer"

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default=UserRole.VIEWER.value)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    
    def set_password(self, password: str):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Check if the provided password matches the hash."""
        return check_password_hash(self.password_hash, password)
    
    def is_locked(self) -> bool:
        """Check if the account is currently locked."""
        if not self.locked_until:
            return False
        return datetime.utcnow() < self.locked_until
    
    def lock_account(self, minutes: int = 30):
        """Lock the account for a specified number of minutes."""
        from datetime import timedelta
        self.locked_until = datetime.utcnow() + timedelta(minutes=minutes)
        self.failed_login_attempts = 0  # Reset on lock
    
    def record_failed_login(self):
        """Record a failed login attempt. Locks account after 5 attempts."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.lock_account(minutes=30)
    
    def reset_failed_logins(self):
        """Reset failed login attempts (called on successful login)."""
        self.failed_login_attempts = 0
        self.locked_until = None
    
    def to_dict(self):
        """Convert user to dictionary (excluding sensitive data)."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"

