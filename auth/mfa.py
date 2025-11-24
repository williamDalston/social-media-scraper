"""
Multi-Factor Authentication (MFA) using TOTP (Time-based One-Time Password).
"""
import pyotp
import qrcode
import io
import base64
import json
import secrets
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.orm import sessionmaker
from scraper.schema import init_db
from models.user import User
from auth.decorators import require_auth
from auth.jwt_utils import get_current_user, get_db_session

mfa_bp = Blueprint("mfa", __name__, url_prefix="/api/auth/mfa")


def generate_backup_codes(count=10):
    """Generate backup codes for MFA."""
    return [secrets.token_urlsafe(8) for _ in range(count)]


def verify_totp(secret, token):
    """Verify a TOTP token."""
    totp = pyotp.TOTP(secret)
    return totp.verify(token, valid_window=1)  # Allow 1 time step tolerance


@mfa_bp.route("/setup", methods=["POST"])
@require_auth
def setup_mfa():
    """Set up MFA for the current user."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404

    if user.mfa_enabled:
        return jsonify({"error": "MFA is already enabled for this account"}), 400

    session = get_db_session()
    db_user = session.query(User).filter_by(id=user.id).first()

    if not db_user:
        session.close()
        return jsonify({"error": "User not found"}), 404

    # Generate TOTP secret
    secret = pyotp.random_base32()
    db_user.mfa_secret = secret

    # Generate backup codes
    backup_codes = generate_backup_codes()
    db_user.backup_codes = json.dumps(backup_codes)

    session.commit()
    session.close()

    # Generate QR code
    totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=user.email, issuer_name="HHS Social Media Scraper"
    )

    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    img_buffer.seek(0)

    qr_code_base64 = base64.b64encode(img_buffer.read()).decode("utf-8")

    return (
        jsonify(
            {
                "secret": secret,  # For manual entry
                "qr_code": f"data:image/png;base64,{qr_code_base64}",
                "backup_codes": backup_codes,  # Show only once!
                "message": "Save these backup codes in a secure location. They will not be shown again.",
            }
        ),
        200,
    )


@mfa_bp.route("/enable", methods=["POST"])
@require_auth
def enable_mfa():
    """Enable MFA after verifying the initial token."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    token = data.get("token", "").strip()
    if not token:
        return jsonify({"error": "TOTP token is required"}), 400

    session = get_db_session()
    db_user = session.query(User).filter_by(id=user.id).first()

    if not db_user or not db_user.mfa_secret:
        session.close()
        return jsonify({"error": "MFA not set up. Please set up MFA first."}), 400

    if db_user.mfa_enabled:
        session.close()
        return jsonify({"error": "MFA is already enabled"}), 400

    # Verify the token
    if not verify_totp(db_user.mfa_secret, token):
        session.close()
        return jsonify({"error": "Invalid TOTP token"}), 400

    # Enable MFA
    db_user.mfa_enabled = True
    session.commit()
    session.close()

    return (
        jsonify({"message": "MFA has been enabled successfully", "mfa_enabled": True}),
        200,
    )


@mfa_bp.route("/disable", methods=["POST"])
@require_auth
def disable_mfa():
    """Disable MFA for the current user."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Require password or backup code to disable
    password = data.get("password", "")
    backup_code = data.get("backup_code", "")

    session = get_db_session()
    db_user = session.query(User).filter_by(id=user.id).first()

    if not db_user:
        session.close()
        return jsonify({"error": "User not found"}), 404

    if not db_user.mfa_enabled:
        session.close()
        return jsonify({"error": "MFA is not enabled"}), 400

    # Verify password or backup code
    verified = False
    if password and db_user.check_password(password):
        verified = True
    elif backup_code:
        backup_codes = json.loads(db_user.backup_codes or "[]")
        if backup_code in backup_codes:
            backup_codes.remove(backup_code)
            db_user.backup_codes = json.dumps(backup_codes)
            verified = True

    if not verified:
        session.close()
        return jsonify({"error": "Invalid password or backup code"}), 401

    # Disable MFA
    db_user.mfa_enabled = False
    db_user.mfa_secret = None
    db_user.backup_codes = None
    session.commit()
    session.close()

    return (
        jsonify(
            {"message": "MFA has been disabled successfully", "mfa_enabled": False}
        ),
        200,
    )


@mfa_bp.route("/status", methods=["GET"])
@require_auth
def mfa_status():
    """Get MFA status for the current user."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "User not found"}), 404

    return (
        jsonify(
            {
                "mfa_enabled": user.mfa_enabled,
                "mfa_setup": bool(user.mfa_secret) if user.mfa_secret else False,
            }
        ),
        200,
    )


@mfa_bp.route("/verify", methods=["POST"])
def verify_mfa():
    """Verify MFA token during login."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    user_id = data.get("user_id")
    token = data.get("token", "").strip()
    backup_code = data.get("backup_code", "")

    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    if not token and not backup_code:
        return jsonify({"error": "TOTP token or backup code is required"}), 400

    session = get_db_session()
    user = session.query(User).filter_by(id=user_id).first()

    if not user:
        session.close()
        return jsonify({"error": "User not found"}), 404

    if not user.mfa_enabled:
        session.close()
        return jsonify({"error": "MFA is not enabled for this account"}), 400

    verified = False

    # Try TOTP token first
    if token and user.mfa_secret:
        verified = verify_totp(user.mfa_secret, token)

    # Try backup code if TOTP failed
    if not verified and backup_code and user.backup_codes:
        backup_codes = json.loads(user.backup_codes)
        if backup_code in backup_codes:
            backup_codes.remove(backup_code)
            user.backup_codes = json.dumps(backup_codes)
            session.commit()
            verified = True

    session.close()

    if verified:
        return (
            jsonify({"verified": True, "message": "MFA verification successful"}),
            200,
        )
    else:
        return (
            jsonify({"verified": False, "error": "Invalid TOTP token or backup code"}),
            401,
        )
