"""
Audit log model for tracking security events and data access.
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from scraper.schema import Base
from datetime import datetime
import enum

class AuditEventType(enum.Enum):
    """Types of audit events."""
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_RESET_REQUEST = "password_reset_request"
    PASSWORD_RESET_COMPLETE = "password_reset_complete"
    PASSWORD_CHANGE = "password_change"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_UNLOCKED = "account_unlocked"
    DATA_ACCESS = "data_access"
    DATA_MODIFICATION = "data_modification"
    FILE_UPLOAD = "file_upload"
    SCRAPER_RUN = "scraper_run"
    API_KEY_CREATED = "api_key_created"
    API_KEY_REVOKED = "api_key_revoked"
    ROLE_CHANGE = "role_change"
    USER_CREATED = "user_created"
    USER_DELETED = "user_deleted"

class AuditLog(Base):
    """Audit log entry for security and compliance tracking."""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    event_type = Column(String(50), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True, index=True)
    username = Column(String(80), nullable=True)  # Store username for deleted users
    ip_address = Column(String(45), nullable=True, index=True)  # IPv6 compatible
    user_agent = Column(String(255), nullable=True)
    resource_type = Column(String(50), nullable=True)  # e.g., 'account', 'file', 'scraper'
    resource_id = Column(String(100), nullable=True)  # ID of accessed resource
    action = Column(String(100), nullable=True)  # e.g., 'view', 'edit', 'delete'
    details = Column(Text, nullable=True)  # JSON string with additional details
    success = Column(String(10), nullable=False, default='true')  # 'true' or 'false'
    error_message = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    def to_dict(self):
        """Convert audit log to dictionary."""
        return {
            'id': self.id,
            'event_type': self.event_type,
            'user_id': self.user_id,
            'username': self.username,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'action': self.action,
            'details': self.details,
            'success': self.success,
            'error_message': self.error_message,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    def __repr__(self):
        return f"<AuditLog(event_type='{self.event_type}', user_id={self.user_id}, timestamp='{self.timestamp}')>"

