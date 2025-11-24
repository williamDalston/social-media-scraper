"""
Account takeover protection mechanisms.
"""
from sqlalchemy.orm import sessionmaker
from scraper.schema import init_db
from models.user import User
from models.audit_log import AuditLog, AuditEventType
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

db_path = os.getenv("DATABASE_PATH", "social_media.db")


def get_db_session():
    """Get database session."""
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    return Session()


def detect_account_takeover_risk(
    user_id: int, new_ip: str, new_user_agent: str = None
) -> dict:
    """
    Detect potential account takeover attempts.

    Args:
        user_id: User ID
        new_ip: New IP address attempting login
        new_user_agent: New user agent string

    Returns:
        Dictionary with risk assessment
    """
    session = get_db_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return {"risk_level": "unknown", "risk_score": 0, "factors": []}

        # Get recent successful logins
        one_week_ago = datetime.utcnow() - timedelta(days=7)
        recent_logins = (
            session.query(AuditLog)
            .filter(
                AuditLog.user_id == user_id,
                AuditLog.event_type == AuditEventType.LOGIN_SUCCESS.value,
                AuditLog.timestamp >= one_week_ago,
            )
            .order_by(AuditLog.timestamp.desc())
            .limit(10)
            .all()
        )

        # Analyze login patterns
        risk_score = 0
        risk_factors = []

        # Check if IP address changed
        if recent_logins:
            previous_ips = set(
                [log.ip_address for log in recent_logins if log.ip_address]
            )
            if new_ip not in previous_ips and len(previous_ips) > 0:
                risk_score += 30
                risk_factors.append("ip_address_change")

        # Check if user agent changed significantly
        if recent_logins and new_user_agent:
            previous_user_agents = [
                log.user_agent for log in recent_logins if log.user_agent
            ]
            if previous_user_agents:
                # Simple check: if user agent is completely different
                if new_user_agent not in previous_user_agents:
                    risk_score += 20
                    risk_factors.append("user_agent_change")

        # Check for rapid location changes (if geolocation available)
        # This would require IP geolocation service

        # Check for multiple failed login attempts before success
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_failures = (
            session.query(AuditLog)
            .filter(
                AuditLog.user_id == user_id,
                AuditLog.event_type == AuditEventType.LOGIN_FAILURE.value,
                AuditLog.timestamp >= one_hour_ago,
            )
            .count()
        )

        if recent_failures > 3:
            risk_score += 40
            risk_factors.append("multiple_failed_attempts")

        # Determine risk level
        if risk_score >= 60:
            risk_level = "high"
        elif risk_score >= 30:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "factors": risk_factors,
            "should_require_mfa": risk_level in ["high", "medium"],
            "should_notify_user": risk_level == "high",
        }
    finally:
        session.close()


def require_additional_verification(user_id: int, risk_assessment: dict) -> bool:
    """
    Determine if additional verification is required based on risk.

    Args:
        user_id: User ID
        risk_assessment: Risk assessment from detect_account_takeover_risk

    Returns:
        True if additional verification required
    """
    return risk_assessment.get("should_require_mfa", False)


def log_account_takeover_attempt(user_id: int, ip_address: str, risk_assessment: dict):
    """
    Log potential account takeover attempt.

    Args:
        user_id: User ID
        ip_address: IP address of attempt
        risk_assessment: Risk assessment
    """
    session = get_db_session()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return

        audit_entry = AuditLog(
            event_type="account_takeover_risk",
            user_id=user_id,
            username=user.username,
            ip_address=ip_address,
            resource_type="account",
            resource_id=str(user_id),
            action="login_attempt",
            details=f"Risk level: {risk_assessment['risk_level']}, Score: {risk_assessment['risk_score']}, Factors: {', '.join(risk_assessment['factors'])}",
            success="false",
            error_message=f"Potential account takeover detected: {risk_assessment['risk_level']} risk",
            timestamp=datetime.utcnow(),
        )
        session.add(audit_entry)
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()
