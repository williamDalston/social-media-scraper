"""
Production security hardening utilities and configurations.
"""
import os
from flask import Flask, request, jsonify
from functools import wraps
import time
from collections import defaultdict
from datetime import datetime, timedelta

# Rate limiting for DDoS protection
request_counts = defaultdict(list)
BLOCKED_IPS = set()


def check_ddos_protection(ip_address, max_requests=100, window_seconds=60):
    """
    Simple DDoS protection using rate limiting per IP.
    In production, use a proper WAF or DDoS protection service.
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=window_seconds)

    # Clean old requests
    request_counts[ip_address] = [
        req_time for req_time in request_counts[ip_address] if req_time > cutoff
    ]

    # Check if IP is blocked
    if ip_address in BLOCKED_IPS:
        return False, "IP address is blocked"

    # Check rate limit
    if len(request_counts[ip_address]) >= max_requests:
        BLOCKED_IPS.add(ip_address)
        return False, "Rate limit exceeded"

    # Record request
    request_counts[ip_address].append(now)
    return True, None


def ddos_protection_middleware(app):
    """Add DDoS protection middleware to Flask app."""

    @app.before_request
    def check_ddos():
        if request.endpoint and request.endpoint.startswith("static"):
            return None

        ip_address = (
            request.remote_addr
            or request.environ.get("HTTP_X_FORWARDED_FOR", "").split(",")[0]
        )

        allowed, error = check_ddos_protection(ip_address)
        if not allowed:
            return jsonify({"error": error}), 429


def security_headers_middleware(app):
    """Add comprehensive security headers."""

    @app.after_request
    def add_security_headers(response):
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://unpkg.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp

        # HSTS (if using HTTPS)
        if request.is_secure:
            response.headers[
                "Strict-Transport-Security"
            ] = "max-age=31536000; includeSubDomains"

        # Permissions policy
        response.headers[
            "Permissions-Policy"
        ] = "geolocation=(), microphone=(), camera=()"

        return response


def bot_detection_middleware(app):
    """Detect and block suspicious bot activity."""

    @app.before_request
    def detect_bots():
        user_agent = request.headers.get("User-Agent", "").lower()
        ip_address = request.remote_addr

        # Block known bad bots
        bad_bot_patterns = [
            "scrapy",
            "curl",
            "wget",
            "python-requests",
            "masscan",
            "nmap",
            "sqlmap",
            "nikto",
        ]

        if any(pattern in user_agent for pattern in bad_bot_patterns):
            # Log suspicious activity
            app.logger.warning(
                f"Suspicious bot detected: {user_agent} from {ip_address}"
            )

            # In production, you might want to block or rate limit
            # For now, just log it
            pass


def honeypot_endpoint(app):
    """Create honeypot endpoints to detect attackers."""

    @app.route("/admin/login", methods=["GET", "POST"])
    @app.route("/wp-admin", methods=["GET", "POST"])
    @app.route("/.env", methods=["GET"])
    @app.route("/config.php", methods=["GET"])
    def honeypot():
        """Honeypot endpoints that should not be accessed."""
        ip_address = request.remote_addr
        app.logger.warning(f"Honeypot accessed from {ip_address}: {request.path}")

        # Log this as a security event
        from auth.audit import log_security_event, AuditEventType

        log_security_event(
            AuditEventType.SECURITY_ALERT,
            details={
                "type": "honeypot_access",
                "path": request.path,
                "ip": ip_address,
                "user_agent": request.headers.get("User-Agent"),
            },
            success=False,
        )

        # Return 404 to not reveal it's a honeypot
        return jsonify({"error": "Not found"}), 404


def setup_production_security(app: Flask):
    """Set up all production security measures."""
    # Add security headers
    security_headers_middleware(app)

    # Add DDoS protection
    ddos_protection_middleware(app)

    # Add bot detection
    bot_detection_middleware(app)

    # Add honeypot endpoints
    honeypot_endpoint(app)

    app.logger.info("Production security hardening enabled")
