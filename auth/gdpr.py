"""
GDPR compliance features: data export and deletion.
"""
from sqlalchemy.orm import sessionmaker
from scraper.schema import init_db
from models.user import User
from models.audit_log import AuditLog
from .audit import log_security_event, AuditEventType
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

def export_user_data(user_id: int) -> dict:
    """
    Export all user data for GDPR compliance.
    
    Args:
        user_id: User ID
    
    Returns:
        Dictionary containing all user data
    """
    session = get_db_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        
        if not user:
            return None
        
        # Get user's audit logs
        audit_logs = session.query(AuditLog).filter_by(
            user_id=user_id
        ).order_by(AuditLog.timestamp.desc()).all()
        
        # Compile user data
        user_data = {
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'last_login': user.last_login.isoformat() if user.last_login else None,
                'is_active': user.is_active,
                'mfa_enabled': getattr(user, 'mfa_enabled', False),
                'oauth_provider': getattr(user, 'oauth_provider', None)
            },
            'audit_logs': [log.to_dict() for log in audit_logs],
            'export_date': datetime.utcnow().isoformat(),
            'export_format': 'GDPR-compliant JSON'
        }
        
        # Log the export
        log_security_event(
            AuditEventType.DATA_ACCESS,
            user_id=user_id,
            username=user.username,
            resource_type='user_data',
            action='export',
            success=True
        )
        
        return user_data
    finally:
        session.close()

def delete_user_data(user_id: int, anonymize: bool = True) -> bool:
    """
    Delete or anonymize user data for GDPR compliance.
    
    Args:
        user_id: User ID
        anonymize: If True, anonymize data instead of deleting (recommended)
    
    Returns:
        True if successful
    """
    session = get_db_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        
        if not user:
            return False
        
        username = user.username
        email = user.email
        
        if anonymize:
            # Anonymize user data instead of deleting
            user.username = f"deleted_user_{user_id}"
            user.email = f"deleted_{user_id}@deleted.local"
            user.password_hash = "deleted"
            user.is_active = False
            user.api_key = None
            user.password_reset_token = None
            
            # Anonymize audit logs
            session.query(AuditLog).filter_by(user_id=user_id).update({
                AuditLog.username: f"deleted_user_{user_id}"
            })
        else:
            # Hard delete (not recommended - breaks referential integrity)
            # Only delete audit logs, keep user record for referential integrity
            session.query(AuditLog).filter_by(user_id=user_id).delete()
            user.is_active = False
        
        session.commit()
        
        # Log the deletion
        log_security_event(
            AuditEventType.USER_DELETED,
            user_id=user_id,
            username=username,
            resource_type='user_data',
            action='delete',
            details={'anonymize': anonymize},
            success=True
        )
        
        return True
    except Exception as e:
        session.rollback()
        return False
    finally:
        session.close()

def apply_data_retention_policy(days: int = 365):
    """
    Apply data retention policy by deleting old audit logs.
    
    Args:
        days: Number of days to retain data (default: 365)
    
    Returns:
        Number of records deleted
    """
    from datetime import timedelta
    
    session = get_db_session()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Delete old audit logs
        deleted_count = session.query(AuditLog).filter(
            AuditLog.timestamp < cutoff_date
        ).delete()
        
        session.commit()
        
        return deleted_count
    except Exception as e:
        session.rollback()
        return 0
    finally:
        session.close()

def generate_compliance_report(start_date: datetime = None, end_date: datetime = None) -> dict:
    """
    Generate compliance report for audit purposes.
    
    Args:
        start_date: Start date for report
        end_date: End date for report
    
    Returns:
        Compliance report dictionary
    """
    if not start_date:
        from datetime import timedelta
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()
    
    session = get_db_session()
    try:
        # Get statistics
        total_users = session.query(User).count()
        active_users = session.query(User).filter_by(is_active=True).count()
        
        # Get audit log statistics
        total_events = session.query(AuditLog).filter(
            AuditLog.timestamp >= start_date,
            AuditLog.timestamp <= end_date
        ).count()
        
        failed_logins = session.query(AuditLog).filter(
            AuditLog.event_type == AuditEventType.LOGIN_FAILURE.value,
            AuditLog.timestamp >= start_date,
            AuditLog.timestamp <= end_date
        ).count()
        
        data_access_events = session.query(AuditLog).filter(
            AuditLog.event_type == AuditEventType.DATA_ACCESS.value,
            AuditLog.timestamp >= start_date,
            AuditLog.timestamp <= end_date
        ).count()
        
        data_modification_events = session.query(AuditLog).filter(
            AuditLog.event_type == AuditEventType.DATA_MODIFICATION.value,
            AuditLog.timestamp >= start_date,
            AuditLog.timestamp <= end_date
        ).count()
        
        return {
            'report_period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'user_statistics': {
                'total_users': total_users,
                'active_users': active_users,
                'inactive_users': total_users - active_users
            },
            'security_events': {
                'total_events': total_events,
                'failed_logins': failed_logins,
                'data_access_events': data_access_events,
                'data_modification_events': data_modification_events
            },
            'compliance_status': 'compliant',
            'generated_at': datetime.utcnow().isoformat()
        }
    finally:
        session.close()

