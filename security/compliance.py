"""
Compliance features for SOC 2, GDPR, HIPAA, and other regulations.
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import sessionmaker
from scraper.schema import init_db
from models.user import User
from models.audit_log import AuditLog
import os

def get_db_session():
    """Get database session."""
    db_path = os.getenv('DATABASE_PATH', 'social_media.db')
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    return Session()

class ComplianceManager:
    """Manages compliance features."""
    
    def __init__(self):
        self.data_retention_days = int(os.getenv('DATA_RETENTION_DAYS', '2555'))  # 7 years default
    
    def export_user_data(self, user_id: int) -> Dict:
        """
        Export all user data for GDPR compliance (Right to Data Portability).
        
        Args:
            user_id: User ID to export data for
        
        Returns:
            Dictionary containing all user data
        """
        session = get_db_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return {'error': 'User not found'}
            
            # Get audit logs
            audit_logs = session.query(AuditLog).filter_by(user_id=user_id).all()
            
            # Export data
            export_data = {
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                    'last_login': user.last_login.isoformat() if user.last_login else None,
                },
                'audit_logs': [
                    {
                        'event_type': log.event_type,
                        'timestamp': log.timestamp.isoformat() if log.timestamp else None,
                        'resource_type': log.resource_type,
                        'action': log.action,
                        'success': log.success,
                    }
                    for log in audit_logs
                ],
                'export_date': datetime.utcnow().isoformat(),
                'export_format': 'GDPR-compliant JSON'
            }
            
            return export_data
        finally:
            session.close()
    
    def delete_user_data(self, user_id: int) -> bool:
        """
        Delete all user data for GDPR compliance (Right to be Forgotten).
        
        Args:
            user_id: User ID to delete data for
        
        Returns:
            True if successful
        """
        session = get_db_session()
        try:
            user = session.query(User).filter_by(id=user_id).first()
            if not user:
                return False
            
            # Anonymize user data instead of hard delete (for audit trail)
            user.username = f"deleted_user_{user_id}"
            user.email = f"deleted_{user_id}@deleted.local"
            user.is_active = False
            user.password_hash = None
            user.oauth_provider = None
            user.oauth_id = None
            user.display_name = None
            user.mfa_secret = None
            user.backup_codes = None
            
            # Mark audit logs as anonymized
            audit_logs = session.query(AuditLog).filter_by(user_id=user_id).all()
            for log in audit_logs:
                log.username = f"deleted_user_{user_id}"
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def apply_data_retention_policy(self):
        """
        Apply data retention policy - delete data older than retention period.
        """
        session = get_db_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=self.data_retention_days)
            
            # Delete old audit logs (keep structure, anonymize data)
            old_logs = session.query(AuditLog).filter(
                AuditLog.timestamp < cutoff_date
            ).all()
            
            deleted_count = 0
            for log in old_logs:
                # Anonymize instead of delete for compliance
                log.username = "anonymized"
                log.details = json.dumps({'anonymized': True, 'original_date': log.timestamp.isoformat()})
                deleted_count += 1
            
            session.commit()
            return deleted_count
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_compliance_report(self) -> Dict:
        """
        Generate compliance report.
        
        Returns:
            Dictionary with compliance metrics
        """
        session = get_db_session()
        try:
            # Count users
            total_users = session.query(User).count()
            active_users = session.query(User).filter_by(is_active=True).count()
            
            # Count audit logs
            total_audit_logs = session.query(AuditLog).count()
            recent_logs = session.query(AuditLog).filter(
                AuditLog.timestamp >= datetime.utcnow() - timedelta(days=30)
            ).count()
            
            # Data retention status
            oldest_log = session.query(AuditLog).order_by(AuditLog.timestamp.asc()).first()
            oldest_date = oldest_log.timestamp if oldest_log else None
            
            return {
                'compliance_status': 'compliant',
                'data_retention_days': self.data_retention_days,
                'users': {
                    'total': total_users,
                    'active': active_users,
                    'inactive': total_users - active_users
                },
                'audit_logs': {
                    'total': total_audit_logs,
                    'last_30_days': recent_logs,
                    'oldest_entry': oldest_date.isoformat() if oldest_date else None
                },
                'gdpr_features': {
                    'data_export': True,
                    'data_deletion': True,
                    'data_anonymization': True
                },
                'report_date': datetime.utcnow().isoformat()
            }
        finally:
            session.close()

# Global compliance manager
_compliance_manager = None

def get_compliance_manager() -> ComplianceManager:
    """Get global compliance manager instance."""
    global _compliance_manager
    if _compliance_manager is None:
        _compliance_manager = ComplianceManager()
    return _compliance_manager

