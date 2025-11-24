"""
IP whitelisting and blacklisting functionality.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from scraper.schema import Base
from datetime import datetime
from flask import request
import ipaddress


class IPFilter(Base):
    """IP whitelist/blacklist entries."""

    __tablename__ = "ip_filters"

    id = Column(Integer, primary_key=True)
    ip_address = Column(String(45), nullable=False, index=True)  # IPv6 compatible
    ip_range = Column(String(50), nullable=True)  # CIDR notation
    is_whitelist = Column(Boolean, default=False, nullable=False, index=True)
    is_blacklist = Column(Boolean, default=False, nullable=False, index=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    def is_expired(self) -> bool:
        """Check if the filter entry has expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at

    def matches_ip(self, ip: str) -> bool:
        """
        Check if an IP address matches this filter entry.

        Args:
            ip: IP address to check

        Returns:
            True if IP matches, False otherwise
        """
        try:
            if self.ip_range:
                # Check if IP is in CIDR range
                network = ipaddress.ip_network(self.ip_range, strict=False)
                ip_obj = ipaddress.ip_address(ip)
                return ip_obj in network
            else:
                # Exact match
                return self.ip_address == ip
        except (ValueError, ipaddress.AddressValueError):
            return False


def get_client_ip() -> str:
    """
    Get the client IP address from the request.

    Returns:
        IP address string
    """
    if request:
        # Check for forwarded IP (from proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP in the chain
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.remote_addr or "0.0.0.0"
    return "0.0.0.0"


def is_ip_allowed(ip: str = None) -> tuple[bool, str]:
    """
    Check if an IP address is allowed (not blacklisted, or whitelisted).

    Args:
        ip: IP address to check (defaults to request IP)

    Returns:
        Tuple of (is_allowed, reason)
    """
    from sqlalchemy.orm import sessionmaker
    from scraper.schema import init_db
    import os
    from dotenv import load_dotenv

    load_dotenv()

    if ip is None:
        ip = get_client_ip()

    db_path = os.getenv("DATABASE_PATH", "social_media.db")
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Check blacklist first
        blacklist_entries = (
            session.query(IPFilter).filter_by(is_blacklist=True, is_active=True).all()
        )

        for entry in blacklist_entries:
            if entry.is_expired():
                continue
            if entry.matches_ip(ip):
                return (
                    False,
                    f"IP is blacklisted: {entry.reason or 'No reason provided'}",
                )

        # Check whitelist
        whitelist_entries = (
            session.query(IPFilter).filter_by(is_whitelist=True, is_active=True).all()
        )

        # If whitelist exists and is not empty, IP must be whitelisted
        if whitelist_entries:
            for entry in whitelist_entries:
                if entry.is_expired():
                    continue
                if entry.matches_ip(ip):
                    return True, "IP is whitelisted"
            return False, "IP is not whitelisted"

        # No restrictions, allow
        return True, "IP is allowed"
    finally:
        session.close()


def add_ip_to_blacklist(
    ip: str, reason: str = None, expires_at: datetime = None
) -> bool:
    """
    Add an IP address to the blacklist.

    Args:
        ip: IP address or CIDR range
        reason: Reason for blacklisting
        expires_at: Expiration date (None for permanent)

    Returns:
        True if added successfully
    """
    from sqlalchemy.orm import sessionmaker
    from scraper.schema import init_db
    import os
    from dotenv import load_dotenv

    load_dotenv()

    db_path = os.getenv("DATABASE_PATH", "social_media.db")
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Validate IP or CIDR
        try:
            if "/" in ip:
                ipaddress.ip_network(ip, strict=False)
                ip_range = ip
                ip_address = None
            else:
                ipaddress.ip_address(ip)
                ip_address = ip
                ip_range = None
        except (ValueError, ipaddress.AddressValueError):
            return False

        # Check if already exists
        existing = (
            session.query(IPFilter)
            .filter_by(ip_address=ip_address, ip_range=ip_range, is_blacklist=True)
            .first()
        )

        if existing:
            existing.is_active = True
            existing.reason = reason
            existing.expires_at = expires_at
        else:
            entry = IPFilter(
                ip_address=ip_address,
                ip_range=ip_range,
                is_blacklist=True,
                is_whitelist=False,
                reason=reason,
                expires_at=expires_at,
                is_active=True,
            )
            session.add(entry)

        session.commit()
        return True
    except Exception:
        session.rollback()
        return False
    finally:
        session.close()


def add_ip_to_whitelist(
    ip: str, reason: str = None, expires_at: datetime = None
) -> bool:
    """
    Add an IP address to the whitelist.

    Args:
        ip: IP address or CIDR range
        reason: Reason for whitelisting
        expires_at: Expiration date (None for permanent)

    Returns:
        True if added successfully
    """
    from sqlalchemy.orm import sessionmaker
    from scraper.schema import init_db
    import os
    from dotenv import load_dotenv

    load_dotenv()

    db_path = os.getenv("DATABASE_PATH", "social_media.db")
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Validate IP or CIDR
        try:
            if "/" in ip:
                ipaddress.ip_network(ip, strict=False)
                ip_range = ip
                ip_address = None
            else:
                ipaddress.ip_address(ip)
                ip_address = ip
                ip_range = None
        except (ValueError, ipaddress.AddressValueError):
            return False

        # Check if already exists
        existing = (
            session.query(IPFilter)
            .filter_by(ip_address=ip_address, ip_range=ip_range, is_whitelist=True)
            .first()
        )

        if existing:
            existing.is_active = True
            existing.reason = reason
            existing.expires_at = expires_at
        else:
            entry = IPFilter(
                ip_address=ip_address,
                ip_range=ip_range,
                is_whitelist=True,
                is_blacklist=False,
                reason=reason,
                expires_at=expires_at,
                is_active=True,
            )
            session.add(entry)

        session.commit()
        return True
    except Exception:
        session.rollback()
        return False
    finally:
        session.close()
