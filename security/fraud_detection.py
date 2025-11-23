"""
Fraud detection mechanisms.
"""
from sqlalchemy.orm import sessionmaker
from scraper.schema import init_db
from models.audit_log import AuditLog, AuditEventType
from datetime import datetime, timedelta
from flask import request
import os
from dotenv import load_dotenv

load_dotenv()

db_path = os.getenv('DATABASE_PATH', 'social_media.db')

def get_db_session():
    """Get database session."""
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    return Session()

def detect_fraud_patterns(user_id: int = None, ip_address: str = None) -> dict:
    """
    Detect fraud patterns in user behavior.
    
    Args:
        user_id: User ID (optional)
        ip_address: IP address (optional)
    
    Returns:
        Dictionary with fraud detection results
    """
    session = get_db_session()
    try:
        fraud_score = 0
        fraud_factors = []
        
        # Time-based analysis
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)
        
        # Check for unusual activity patterns
        if user_id:
            # Check for rapid successive actions
            recent_actions = session.query(AuditLog).filter(
                AuditLog.user_id == user_id,
                AuditLog.timestamp >= one_hour_ago
            ).count()
            
            if recent_actions > 1000:
                fraud_score += 50
                fraud_factors.append('excessive_activity')
            elif recent_actions > 500:
                fraud_score += 25
                fraud_factors.append('high_activity')
        
        if ip_address:
            # Check for multiple accounts from same IP
            unique_users = session.query(AuditLog.user_id).filter(
                AuditLog.ip_address == ip_address,
                AuditLog.timestamp >= one_day_ago,
                AuditLog.user_id.isnot(None)
            ).distinct().count()
            
            if unique_users > 10:
                fraud_score += 40
                fraud_factors.append('multiple_accounts_same_ip')
            elif unique_users > 5:
                fraud_score += 20
                fraud_factors.append('several_accounts_same_ip')
            
            # Check for rapid registration attempts
            registrations = session.query(AuditLog).filter(
                AuditLog.ip_address == ip_address,
                AuditLog.event_type == 'user_created',
                AuditLog.timestamp >= one_hour_ago
            ).count()
            
            if registrations > 5:
                fraud_score += 60
                fraud_factors.append('rapid_registrations')
            elif registrations > 2:
                fraud_score += 30
                fraud_factors.append('multiple_registrations')
        
        # Check for data exfiltration patterns
        if user_id:
            # Check for bulk data downloads
            downloads = session.query(AuditLog).filter(
                AuditLog.user_id == user_id,
                AuditLog.action == 'download',
                AuditLog.timestamp >= one_hour_ago
            ).count()
            
            if downloads > 10:
                fraud_score += 35
                fraud_factors.append('excessive_downloads')
        
        # Determine fraud level
        if fraud_score >= 70:
            fraud_level = 'high'
        elif fraud_score >= 40:
            fraud_level = 'medium'
        else:
            fraud_level = 'low'
        
        return {
            'fraud_level': fraud_level,
            'fraud_score': fraud_score,
            'factors': fraud_factors,
            'should_block': fraud_level == 'high',
            'should_alert': fraud_level in ['high', 'medium']
        }
    finally:
        session.close()

def check_fraud_and_block(user_id: int = None, ip_address: str = None) -> tuple[bool, str]:
    """
    Check for fraud and determine if request should be blocked.
    
    Args:
        user_id: User ID (optional)
        ip_address: IP address (optional, defaults to request IP)
    
    Returns:
        Tuple of (should_block, reason)
    """
    if ip_address is None and request:
        ip_address = request.remote_addr
    
    detection = detect_fraud_patterns(user_id=user_id, ip_address=ip_address)
    
    if detection['should_block']:
        # Log the fraud detection
        session = get_db_session()
        try:
            audit_entry = AuditLog(
                event_type='fraud_detected',
                user_id=user_id,
                ip_address=ip_address,
                resource_type='fraud_detection',
                action='block',
                details=f"Fraud level: {detection['fraud_level']}, Score: {detection['fraud_score']}, Factors: {', '.join(detection['factors'])}",
                success='false',
                error_message=f"Fraud detected: {detection['fraud_level']} level",
                timestamp=datetime.utcnow()
            )
            session.add(audit_entry)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()
        
        return True, f"Request blocked: {detection['fraud_level']} fraud level detected"
    
    if detection['should_alert']:
        # Log alert (but don't block)
        session = get_db_session()
        try:
            audit_entry = AuditLog(
                event_type='fraud_alert',
                user_id=user_id,
                ip_address=ip_address,
                resource_type='fraud_detection',
                action='alert',
                details=f"Fraud level: {detection['fraud_level']}, Score: {detection['fraud_score']}, Factors: {', '.join(detection['factors'])}",
                success='true',
                timestamp=datetime.utcnow()
            )
            session.add(audit_entry)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()
    
    return False, None

