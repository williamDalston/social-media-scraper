"""
Security middleware for bot detection, fraud detection, and threat protection.
"""
from flask import request, jsonify, g
from security.bot_detection import check_bot_and_block
from security.fraud_detection import check_fraud_and_block
from security.security_policy import check_security_policies


def setup_security_middleware(app):
    """
    Set up security middleware for the Flask app.

    Args:
        app: Flask application instance
    """

    @app.before_request
    def security_checks():
        """Run security checks before each request."""
        # Skip security checks for health endpoints
        if request.path.startswith("/health"):
            return None

        # Security policy enforcement
        violation, message = check_security_policies()
        if violation:
            return (
                jsonify({"error": "Security policy violation", "message": message}),
                403,
            )

        # Bot detection
        try:
            should_block, reason = check_bot_and_block()
            if should_block:
                return jsonify({"error": "Access denied", "message": reason}), 403
        except Exception:
            pass  # Don't fail if bot detection fails

        # Fraud detection (for authenticated users)
        try:
            from auth.jwt_utils import get_current_user

            user = get_current_user()
            if user:
                should_block, reason = check_fraud_and_block(user_id=user.id)
                if should_block:
                    return jsonify({"error": "Access denied", "message": reason}), 403
        except Exception:
            pass  # Don't fail if fraud detection fails

        return None
