"""
Security audit logging functionality.
"""
from sqlalchemy.orm import sessionmaker
from scraper.schema import init_db
from models.audit_log import AuditLog, AuditEventType
from flask import request
import os
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

db_path = os.getenv('DATABASE_PATH', 'social_media.db')

def get_db_session():
    """Get database session."""
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    return Session()

def log_security_event(
    event_type: AuditEventType,
    user_id: int = None,
    username: str = None,
    resource_type: str = None,
    resource_id: str = None,
    action: str = None,
    details: dict = None,
    success: bool = True,
    error_message: str = None
):
    """
    Log a security event to the audit log.
    
    Args:
        event_type: Type of event (from AuditEventType enum)
        user_id: ID of user performing action
        username: Username (for deleted users or when user_id not available)
        resource_type: Type of resource accessed (e.g., 'account', 'file')
        resource_id: ID of resource accessed
        action: Action performed (e.g., 'view', 'edit', 'delete')
        details: Additional details as dictionary
        success: Whether the action was successful
        error_message: Error message if action failed
    """
    session = get_db_session()
    try:
        # Get request information
        ip_address = request.remote_addr if request else None
        user_agent = request.headers.get('User-Agent') if request else None
        
        audit_entry = AuditLog(
            event_type=event_type.value,
            user_id=user_id,
            username=username,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=json.dumps(details) if details else None,
            success='true' if success else 'false',
            error_message=error_message,
            timestamp=datetime.utcnow()
        )
        
        session.add(audit_entry)
        session.commit()
    except Exception as e:
        # Don't fail the main operation if audit logging fails
        # But log the error for debugging
        print(f"Error logging audit event: {e}")
        session.rollback()
    finally:
        session.close()

def get_audit_logs(
    user_id: int = None,
    event_type: str = None,
    start_date: datetime = None,
    end_date: datetime = None,
    limit: int = 100,
    offset: int = 0
):
    """
    Retrieve audit logs with filtering.
    
    Args:
        user_id: Filter by user ID
        event_type: Filter by event type
        start_date: Start date for filtering
        end_date: End date for filtering
        limit: Maximum number of records to return
        offset: Offset for pagination
    
    Returns:
        List of audit log entries
    """
    session = get_db_session()
    try:
        query = session.query(AuditLog)
        
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if event_type:
            query = query.filter(AuditLog.event_type == event_type)
        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        if end_date:
            query = query.filter(AuditLog.timestamp <= end_date)
        
        query = query.order_by(AuditLog.timestamp.desc())
        query = query.offset(offset).limit(limit)
        
        return [log.to_dict() for log in query.all()]
    finally:
        session.close()

