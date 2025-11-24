from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.orm import sessionmaker
from scraper.schema import init_db
from models.user import User, UserRole
from .jwt_utils import generate_token, verify_token, get_current_user, get_db_session
from .decorators import require_auth, require_any_role
from .validators import validate_email, validate_password, validate_username
from .password_reset import request_password_reset, reset_password
from .audit import log_security_event, AuditEventType
from datetime import datetime
import os

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# Rate limiting will be applied in app.py after blueprint registration


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user.
    Note: In production, this should be admin-only. For now, we'll allow registration
    but the first user will be admin.
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    role = data.get("role", UserRole.VIEWER.value)

    # Validate input
    username_valid, username_error = validate_username(username)
    if not username_valid:
        return jsonify({"error": username_error}), 400

    email_valid, email_error = validate_email(email)
    if not email_valid:
        return jsonify({"error": email_error}), 400

    password_valid, password_error = validate_password(password)
    if not password_valid:
        return jsonify({"error": password_error}), 400

    # Check if role is valid
    valid_roles = [r.value for r in UserRole]
    if role not in valid_roles:
        return (
            jsonify(
                {"error": f'Invalid role. Must be one of: {", ".join(valid_roles)}'}
            ),
            400,
        )

    session = get_db_session()

    # Check if user already exists
    existing_user = (
        session.query(User)
        .filter((User.username == username) | (User.email == email))
        .first()
    )

    if existing_user:
        session.close()
        return jsonify({"error": "Username or email already exists"}), 409

    # Check if this is the first user (make them admin)
    user_count = session.query(User).count()
    if user_count == 0:
        role = UserRole.ADMIN.value

    # Create new user
    user = User(username=username, email=email, role=role, is_active=True)
    user.set_password(password)

    session.add(user)
    session.commit()

    user_id = user.id
    session.close()

    # Generate tokens
    tokens = generate_token(user_id, role)

    return (
        jsonify(
            {
                "message": "User registered successfully",
                "user": {
                    "id": user_id,
                    "username": username,
                    "email": email,
                    "role": role,
                },
                **tokens,
            }
        ),
        201,
    )


@auth_bp.route("/login", methods=["POST"])
def login():
    """Login and return JWT token."""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400

    session = get_db_session()

    # Find user by username or email
    user = (
        session.query(User)
        .filter((User.username == username) | (User.email == username))
        .first()
    )

    # Account takeover detection
    if user:
        from security.account_takeover import (
            detect_account_takeover_risk,
            log_account_takeover_attempt,
            require_additional_verification,
        )
        from flask import request

        ip_address = request.remote_addr if request else None
        user_agent = request.headers.get("User-Agent", "") if request else None

        risk_assessment = detect_account_takeover_risk(user.id, ip_address, user_agent)

        if risk_assessment["risk_level"] in ["high", "medium"]:
            log_account_takeover_attempt(user.id, ip_address, risk_assessment)

            if require_additional_verification(user.id, risk_assessment):
                # In production, require MFA or additional verification
                session.close()
                return (
                    jsonify(
                        {
                            "error": "Additional verification required",
                            "message": "For your security, please verify your identity",
                            "requires_mfa": True,
                        }
                    ),
                    403,
                )

    # Check if user exists and account is not locked
    if not user:
        # Don't reveal if user exists - security best practice
        session.close()
        return jsonify({"error": "Invalid username or password"}), 401

    # Check if account is locked
    if user.is_locked():
        session.close()
        return (
            jsonify(
                {
                    "error": "Account is temporarily locked due to multiple failed login attempts. Please try again later."
                }
            ),
            403,
        )

    # Check if account is active
    if not user.is_active:
        session.close()
        return jsonify({"error": "Account is disabled"}), 403

    # Verify password
    if not user.check_password(password):
        # Record failed login attempt
        user.record_failed_login()
        session.commit()
        session.close()

        # Log failed login
        log_security_event(
            AuditEventType.LOGIN_FAILURE,
            user_id=user.id,
            username=user.username,
            success=False,
            error_message="Invalid password",
        )

        return jsonify({"error": "Invalid username or password"}), 401

    # Check if MFA is enabled
    if user.mfa_enabled:
        # Return a response indicating MFA is required
        user_id = user.id
        session.close()

        return (
            jsonify(
                {
                    "message": "MFA verification required",
                    "mfa_required": True,
                    "user_id": user_id,
                }
            ),
            200,
        )

    # Update last login and reset failed login attempts
    user.last_login = datetime.utcnow()
    user.reset_failed_logins()
    session.commit()

    user_id = user.id
    role = user.role
    session.close()

    # Log successful login
    log_security_event(
        AuditEventType.LOGIN_SUCCESS,
        user_id=user_id,
        username=user.username,
        success=True,
    )

    # Generate tokens
    access_token = generate_token(user_id, role, "access")
    refresh_token = generate_token(user_id, role, "refresh")

    return (
        jsonify(
            {
                "message": "Login successful",
                "user": {
                    "id": user_id,
                    "username": user.username,
                    "email": user.email,
                    "role": role,
                },
                "access_token": access_token["token"],
                "refresh_token": refresh_token["token"],
                "expires_in": access_token["expires_in"],
                "mfa_required": False,
            }
        ),
        200,
    )


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """
    Logout endpoint.
    Note: With JWT, logout is typically handled client-side by removing the token.
    This endpoint can be used for server-side token blacklisting if needed.
    """
    return jsonify({"message": "Logout successful"}), 200


@auth_bp.route("/me", methods=["GET"])
@require_auth
def get_current_user_info():
    """Get current authenticated user information."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"user": user.to_dict()}), 200


@auth_bp.route("/refresh", methods=["POST"])
def refresh_token():
    """Refresh access token using refresh token."""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    refresh_token_str = data.get("refresh_token", "")

    if not refresh_token_str:
        return jsonify({"error": "Refresh token is required"}), 400

    try:
        payload = verify_token(refresh_token_str)

        if payload.get("type") != "refresh":
            return jsonify({"error": "Invalid token type"}), 401

        user_id = payload.get("user_id")
        role = payload.get("role")
        old_version = payload.get("version", 1)

        session = get_db_session()
        user = session.query(User).filter_by(id=user_id, is_active=True).first()

        if not user:
            session.close()
            return jsonify({"error": "User not found or inactive"}), 401

        # Check token version for rotation
        # If token version doesn't match, increment and rotate
        if old_version < user.token_version:
            # Token has been rotated, old refresh token is invalid
            session.close()
            return (
                jsonify({"error": "Token has been rotated. Please login again."}),
                401,
            )

        # Rotate token: increment version
        user.token_version += 1
        new_version = user.token_version
        session.commit()
        session.close()

        # Generate new tokens with incremented version
        access_token = generate_token(user_id, role, "access", new_version)
        refresh_token = generate_token(user_id, role, "refresh", new_version)

        return (
            jsonify(
                {
                    "access_token": access_token["token"],
                    "refresh_token": refresh_token["token"],
                    "expires_in": access_token["expires_in"],
                }
            ),
            200,
        )

    except ValueError as e:
        return jsonify({"error": str(e)}), 401


@auth_bp.route("/password-reset/request", methods=["POST"])
def request_password_reset():
    """Request a password reset token."""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    email = data.get("email", "").strip().lower()

    if not email:
        return jsonify({"error": "Email is required"}), 400

    # Validate email format
    email_valid, email_error = validate_email(email)
    if not email_valid:
        return jsonify({"error": email_error}), 400

    # Request password reset (uses the password_reset blueprint endpoint)
    # This will handle token creation and return appropriate response
    from .password_reset import request_password_reset

    return request_password_reset()


@auth_bp.route("/password-reset/confirm", methods=["POST"])
def confirm_password_reset():
    """Reset password using a reset token."""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    token = data.get("token", "")
    new_password = data.get("password", "")

    if not token or not new_password:
        return jsonify({"error": "Token and password are required"}), 400

    # Validate password strength
    password_valid, password_error = validate_password(new_password)
    if not password_valid:
        return jsonify({"error": password_error}), 400

    # Reset password
    success = reset_password(token, new_password)

    if success:
        return jsonify({"message": "Password has been reset successfully"}), 200
    else:
        return jsonify({"error": "Invalid or expired reset token"}), 400


@auth_bp.route("/change-password", methods=["POST"])
@require_auth
def change_password():
    """Change password for authenticated user."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    current_password = data.get("current_password", "")
    new_password = data.get("new_password", "")

    if not current_password or not new_password:
        return jsonify({"error": "Current password and new password are required"}), 400

    session = get_db_session()
    try:
        # Verify current password
        if not user.check_password(current_password):
            log_security_event(
                AuditEventType.PASSWORD_CHANGE,
                user_id=user.id,
                username=user.username,
                success=False,
                error_message="Invalid current password",
            )
            return jsonify({"error": "Current password is incorrect"}), 401

        # Validate new password
        password_valid, password_error = validate_password(new_password)
        if not password_valid:
            return jsonify({"error": password_error}), 400

        # Set new password
        user.set_password(new_password)
        user.reset_failed_logins()
        session.commit()

        # Log successful password change
        log_security_event(
            AuditEventType.PASSWORD_CHANGE,
            user_id=user.id,
            username=user.username,
            success=True,
        )

        return jsonify({"message": "Password changed successfully"}), 200
    finally:
        session.close()


@auth_bp.route("/api-key/create", methods=["POST"])
@require_auth
def create_api_key_endpoint():
    """Create an API key for the authenticated user."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404

    from .api_keys import create_api_key

    api_key = create_api_key(user.id)

    if api_key:
        return (
            jsonify(
                {
                    "message": "API key created successfully",
                    "api_key": api_key,
                    "warning": "Store this key securely. It will not be shown again.",
                }
            ),
            201,
        )
    else:
        return jsonify({"error": "Failed to create API key"}), 500


@auth_bp.route("/api-key/revoke", methods=["POST"])
@require_auth
def revoke_api_key_endpoint():
    """Revoke the API key for the authenticated user."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404

    from .api_keys import revoke_api_key

    success = revoke_api_key(user.id)

    if success:
        return jsonify({"message": "API key revoked successfully"}), 200
    else:
        return jsonify({"error": "Failed to revoke API key"}), 500


@auth_bp.route("/audit-logs", methods=["GET"])
@require_any_role(["Admin"])
def get_audit_logs_endpoint():
    """Get audit logs (Admin only)."""
    from datetime import datetime, timedelta
    from .audit import get_audit_logs

    # Get query parameters
    user_id = request.args.get("user_id", type=int)
    event_type = request.args.get("event_type")
    days = request.args.get("days", 7, type=int)
    limit = request.args.get("limit", 100, type=int)
    offset = request.args.get("offset", 0, type=int)

    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    logs = get_audit_logs(
        user_id=user_id,
        event_type=event_type,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )

    return (
        jsonify({"logs": logs, "count": len(logs), "limit": limit, "offset": offset}),
        200,
    )


@auth_bp.route("/gdpr/export", methods=["GET"])
@require_auth
def export_user_data_endpoint():
    """Export user's own data (GDPR compliance)."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404

    from .gdpr import export_user_data

    user_data = export_user_data(user.id)

    if user_data:
        return jsonify(user_data), 200
    else:
        return jsonify({"error": "Failed to export user data"}), 500


@auth_bp.route("/gdpr/delete", methods=["POST"])
@require_auth
def delete_user_data_endpoint():
    """Delete user's own data (GDPR compliance)."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json() or {}
    anonymize = data.get("anonymize", True)  # Default to anonymize

    from .gdpr import delete_user_data

    success = delete_user_data(user.id, anonymize=anonymize)

    if success:
        return (
            jsonify(
                {"message": "User data deleted successfully", "anonymized": anonymize}
            ),
            200,
        )
    else:
        return jsonify({"error": "Failed to delete user data"}), 500


@auth_bp.route("/admin/compliance/report", methods=["GET"])
@require_any_role(["Admin"])
def get_compliance_report():
    """Get compliance report (Admin only)."""
    from datetime import datetime, timedelta
    from .gdpr import generate_compliance_report

    days = request.args.get("days", 30, type=int)
    start_date = datetime.utcnow() - timedelta(days=days)
    end_date = datetime.utcnow()

    report = generate_compliance_report(start_date, end_date)

    return jsonify(report), 200


@auth_bp.route("/admin/compliance/retention", methods=["POST"])
@require_any_role(["Admin"])
def apply_data_retention():
    """Apply data retention policy (Admin only)."""
    data = request.get_json() or {}
    days = data.get("days", 365)  # Default: 1 year

    from .gdpr import apply_data_retention_policy

    deleted_count = apply_data_retention_policy(days)

    user = get_current_user()
    if user:
        log_security_event(
            AuditEventType.DATA_MODIFICATION,
            user_id=user.id,
            username=user.username,
            resource_type="audit_logs",
            action="retention_policy",
            details={"days": days, "deleted_count": deleted_count},
            success=True,
        )

    return (
        jsonify(
            {
                "message": f"Data retention policy applied",
                "days_retained": days,
                "records_deleted": deleted_count,
            }
        ),
        200,
    )


@auth_bp.route("/security/events", methods=["GET"])
@require_any_role(["Admin"])
def get_security_events():
    """Get security events summary (Admin only)."""
    from datetime import datetime, timedelta
    from sqlalchemy import func
    from models.audit_log import AuditLog

    days = request.args.get("days", 7, type=int)
    start_date = datetime.utcnow() - timedelta(days=days)

    session = get_db_session()
    try:
        # Get event counts by type
        event_counts = (
            session.query(AuditLog.event_type, func.count(AuditLog.id).label("count"))
            .filter(AuditLog.timestamp >= start_date)
            .group_by(AuditLog.event_type)
            .all()
        )

        # Get failed login attempts
        failed_logins = (
            session.query(AuditLog)
            .filter(
                AuditLog.event_type == AuditEventType.LOGIN_FAILURE.value,
                AuditLog.timestamp >= start_date,
            )
            .count()
        )

        # Get unique IPs with failed logins
        suspicious_ips = (
            session.query(AuditLog.ip_address, func.count(AuditLog.id).label("count"))
            .filter(
                AuditLog.event_type == AuditEventType.LOGIN_FAILURE.value,
                AuditLog.timestamp >= start_date,
                AuditLog.ip_address.isnot(None),
            )
            .group_by(AuditLog.ip_address)
            .order_by(func.count(AuditLog.id).desc())
            .limit(10)
            .all()
        )

        return (
            jsonify(
                {
                    "event_counts": {
                        event_type: count for event_type, count in event_counts
                    },
                    "failed_logins": failed_logins,
                    "suspicious_ips": [
                        {"ip": ip, "attempts": count} for ip, count in suspicious_ips
                    ],
                    "period_days": days,
                }
            ),
            200,
        )
    finally:
        session.close()
