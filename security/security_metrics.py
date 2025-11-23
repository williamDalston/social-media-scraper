"""
Security metrics collection and dashboard data.
"""
from sqlalchemy.orm import sessionmaker
from sqlalchemy import func
from scraper.schema import init_db
from models.audit_log import AuditLog, AuditEventType
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

db_path = os.getenv('DATABASE_PATH', 'social_media.db')

def get_db_session():
    """Get database session."""
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    return Session()

def get_security_metrics(days: int = 7) -> dict:
    """
    Get comprehensive security metrics.
    
    Args:
        days: Number of days to analyze
    
    Returns:
        Dictionary with security metrics
    """
    session = get_db_session()
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Total security events
        total_events = session.query(AuditLog).filter(
            AuditLog.timestamp >= start_date
        ).count()
        
        # Failed login attempts
        failed_logins = session.query(AuditLog).filter(
            AuditLog.event_type == AuditEventType.LOGIN_FAILURE.value,
            AuditLog.timestamp >= start_date
        ).count()
        
        # Successful logins
        successful_logins = session.query(AuditLog).filter(
            AuditLog.event_type == AuditEventType.LOGIN_SUCCESS.value,
            AuditLog.timestamp >= start_date
        ).count()
        
        # Account lockouts
        account_locked = session.query(AuditLog).filter(
            AuditLog.event_type == AuditEventType.ACCOUNT_LOCKED.value,
            AuditLog.timestamp >= start_date
        ).count()
        
        # Bot detections
        bot_detections = session.query(AuditLog).filter(
            AuditLog.event_type == 'bot_detected',
            AuditLog.timestamp >= start_date
        ).count()
        
        # Fraud detections
        fraud_detections = session.query(AuditLog).filter(
            AuditLog.event_type.in_(['fraud_detected', 'fraud_alert']),
            AuditLog.timestamp >= start_date
        ).count()
        
        # Honeypot accesses
        honeypot_accesses = session.query(AuditLog).filter(
            AuditLog.event_type == 'honeypot_accessed',
            AuditLog.timestamp >= start_date
        ).count()
        
        # Account takeover risks
        account_takeover_risks = session.query(AuditLog).filter(
            AuditLog.event_type == 'account_takeover_risk',
            AuditLog.timestamp >= start_date
        ).count()
        
        # Data access events
        data_access = session.query(AuditLog).filter(
            AuditLog.event_type == AuditEventType.DATA_ACCESS.value,
            AuditLog.timestamp >= start_date
        ).count()
        
        # Top IPs with failed logins
        top_failed_ips = session.query(
            AuditLog.ip_address,
            func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.event_type == AuditEventType.LOGIN_FAILURE.value,
            AuditLog.timestamp >= start_date,
            AuditLog.ip_address.isnot(None)
        ).group_by(AuditLog.ip_address).order_by(func.count(AuditLog.id).desc()).limit(10).all()
        
        # Security events by type
        events_by_type = session.query(
            AuditLog.event_type,
            func.count(AuditLog.id).label('count')
        ).filter(
            AuditLog.timestamp >= start_date
        ).group_by(AuditLog.event_type).all()
        
        # Calculate success rate
        login_success_rate = 0
        if (successful_logins + failed_logins) > 0:
            login_success_rate = (successful_logins / (successful_logins + failed_logins)) * 100
        
        return {
            'period': {
                'days': days,
                'start_date': start_date.isoformat(),
                'end_date': datetime.utcnow().isoformat()
            },
            'summary': {
                'total_security_events': total_events,
                'failed_logins': failed_logins,
                'successful_logins': successful_logins,
                'login_success_rate': round(login_success_rate, 2),
                'account_locked': account_locked,
                'bot_detections': bot_detections,
                'fraud_detections': fraud_detections,
                'honeypot_accesses': honeypot_accesses,
                'account_takeover_risks': account_takeover_risks,
                'data_access_events': data_access
            },
            'threats': {
                'top_failed_login_ips': [{'ip': ip, 'attempts': count} for ip, count in top_failed_ips],
                'events_by_type': {event_type: count for event_type, count in events_by_type}
            },
            'risk_assessment': {
                'overall_risk': calculate_overall_risk(failed_logins, bot_detections, fraud_detections, account_takeover_risks),
                'recommendations': generate_recommendations(failed_logins, bot_detections, fraud_detections)
            }
        }
    finally:
        session.close()

def calculate_overall_risk(failed_logins: int, bot_detections: int, fraud_detections: int, account_takeover_risks: int) -> str:
    """
    Calculate overall security risk level.
    
    Args:
        failed_logins: Number of failed logins
        bot_detections: Number of bot detections
        fraud_detections: Number of fraud detections
        account_takeover_risks: Number of account takeover risks
    
    Returns:
        Risk level: 'low', 'medium', 'high', 'critical'
    """
    risk_score = 0
    
    if failed_logins > 100:
        risk_score += 3
    elif failed_logins > 50:
        risk_score += 2
    elif failed_logins > 20:
        risk_score += 1
    
    if bot_detections > 50:
        risk_score += 3
    elif bot_detections > 20:
        risk_score += 2
    elif bot_detections > 5:
        risk_score += 1
    
    if fraud_detections > 10:
        risk_score += 4
    elif fraud_detections > 5:
        risk_score += 2
    elif fraud_detections > 0:
        risk_score += 1
    
    if account_takeover_risks > 5:
        risk_score += 4
    elif account_takeover_risks > 2:
        risk_score += 2
    elif account_takeover_risks > 0:
        risk_score += 1
    
    if risk_score >= 8:
        return 'critical'
    elif risk_score >= 5:
        return 'high'
    elif risk_score >= 3:
        return 'medium'
    else:
        return 'low'

def generate_recommendations(failed_logins: int, bot_detections: int, fraud_detections: int) -> list:
    """
    Generate security recommendations based on metrics.
    
    Args:
        failed_logins: Number of failed logins
        bot_detections: Number of bot detections
        fraud_detections: Number of fraud detections
    
    Returns:
        List of recommendations
    """
    recommendations = []
    
    if failed_logins > 50:
        recommendations.append('High number of failed login attempts detected. Consider implementing CAPTCHA or additional rate limiting.')
    
    if bot_detections > 20:
        recommendations.append('Multiple bot detections. Consider enhancing bot detection rules or implementing stricter IP filtering.')
    
    if fraud_detections > 5:
        recommendations.append('Fraud patterns detected. Review and potentially block suspicious IPs or accounts.')
    
    if not recommendations:
        recommendations.append('Security metrics are within normal ranges. Continue monitoring.')
    
    return recommendations

