"""
Bot detection and mitigation system.
"""
from flask import request, g
from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from scraper.schema import init_db
from models.audit_log import AuditLog, AuditEventType
import os
import re
from dotenv import load_dotenv

load_dotenv()

db_path = os.getenv("DATABASE_PATH", "social_media.db")


def get_db_session():
    """Get database session."""
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    return Session()


# Known bot user agents
BOT_USER_AGENTS = [
    "bot",
    "crawler",
    "spider",
    "scraper",
    "curl",
    "wget",
    "python-requests",
    "go-http-client",
    "java/",
    "apache-httpclient",
    "scrapy",
    "selenium",
    "headless",
    "phantomjs",
    "puppeteer",
]

# Suspicious patterns
SUSPICIOUS_PATTERNS = [
    r"^[0-9]+$",  # Only numbers
    r"^[a-z]+$",  # Only lowercase letters
    r"^[A-Z]+$",  # Only uppercase letters
    r"^.{1,3}$",  # Very short usernames
]


def is_bot_user_agent(user_agent: str) -> bool:
    """
    Check if user agent indicates a bot.

    Args:
        user_agent: User agent string

    Returns:
        True if likely a bot
    """
    if not user_agent:
        return True  # No user agent is suspicious

    user_agent_lower = user_agent.lower()

    for bot_pattern in BOT_USER_AGENTS:
        if bot_pattern in user_agent_lower:
            return True

    return False


def detect_suspicious_activity(ip_address: str, user_agent: str = None) -> dict:
    """
    Detect suspicious activity patterns.

    Args:
        ip_address: Client IP address
        user_agent: User agent string

    Returns:
        Dictionary with detection results
    """
    session = get_db_session()
    try:
        # Check for bot user agent
        is_bot = is_bot_user_agent(user_agent) if user_agent else True

        # Check failed login attempts in last hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        failed_logins = (
            session.query(AuditLog)
            .filter(
                AuditLog.ip_address == ip_address,
                AuditLog.event_type == AuditEventType.LOGIN_FAILURE.value,
                AuditLog.timestamp >= one_hour_ago,
            )
            .count()
        )

        # Check total requests in last hour
        total_requests = (
            session.query(AuditLog)
            .filter(
                AuditLog.ip_address == ip_address, AuditLog.timestamp >= one_hour_ago
            )
            .count()
        )

        # Calculate risk score
        risk_score = 0
        risk_factors = []

        if is_bot:
            risk_score += 30
            risk_factors.append("bot_user_agent")

        if failed_logins > 10:
            risk_score += 40
            risk_factors.append("high_failed_logins")
        elif failed_logins > 5:
            risk_score += 20
            risk_factors.append("moderate_failed_logins")

        if total_requests > 1000:
            risk_score += 30
            risk_factors.append("high_request_volume")
        elif total_requests > 500:
            risk_score += 15
            risk_factors.append("moderate_request_volume")

        # Determine threat level
        if risk_score >= 70:
            threat_level = "high"
        elif risk_score >= 40:
            threat_level = "medium"
        else:
            threat_level = "low"

        return {
            "is_bot": is_bot,
            "risk_score": risk_score,
            "threat_level": threat_level,
            "risk_factors": risk_factors,
            "failed_logins_1h": failed_logins,
            "total_requests_1h": total_requests,
            "should_block": threat_level == "high",
        }
    finally:
        session.close()


def check_bot_and_block():
    """
    Check if request is from a bot and should be blocked.
    Called as middleware.

    Returns:
        Tuple of (should_block, reason)
    """
    if not request:
        return False, None

    ip_address = request.remote_addr
    user_agent = request.headers.get("User-Agent", "")

    detection = detect_suspicious_activity(ip_address, user_agent)

    if detection["should_block"]:
        # Log the block
        session = get_db_session()
        try:
            audit_entry = AuditLog(
                event_type="bot_detected",
                ip_address=ip_address,
                user_agent=user_agent,
                success="false",
                error_message=f"Bot detected: {', '.join(detection['risk_factors'])}",
                timestamp=datetime.utcnow(),
            )
            session.add(audit_entry)
            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

        return True, f"Request blocked: {detection['threat_level']} threat level"

    return False, None
