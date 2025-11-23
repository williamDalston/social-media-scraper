"""
Password reset functionality with secure tokens.
"""
import secrets
import hashlib
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.orm import sessionmaker
from scraper.schema import init_db
from models.user import User
from auth.jwt_utils import get_db_session
from auth.validators import validate_email, validate_password

password_reset_bp = Blueprint('password_reset', __name__, url_prefix='/api/auth/password-reset')

def generate_reset_token():
    """Generate a secure password reset token."""
    return secrets.token_urlsafe(32)

def hash_reset_token(token):
    """Hash the reset token for storage."""
    return hashlib.sha256(token.encode()).hexdigest()

def create_reset_token(user):
    """Create and store a password reset token for a user."""
    token = generate_reset_token()
    token_hash = hash_reset_token(token)
    
    # Token expires in 1 hour
    expires_at = datetime.utcnow() + timedelta(hours=1)
    
    user.password_reset_token = token_hash
    user.password_reset_expires = expires_at
    
    return token

def verify_reset_token(user, token):
    """Verify a password reset token."""
    if not user.password_reset_token or not user.password_reset_expires:
        return False
    
    # Check if token has expired
    if datetime.utcnow() > user.password_reset_expires:
        return False
    
    # Verify token hash
    token_hash = hash_reset_token(token)
    return token_hash == user.password_reset_token

@password_reset_bp.route('/request', methods=['POST'])
def request_password_reset():
    """Request a password reset. Sends reset token via email (or returns it for testing)."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    email = data.get('email', '').strip().lower()
    
    # Validate email
    email_valid, email_error = validate_email(email)
    if not email_valid:
        return jsonify({'error': email_error}), 400
    
    session = get_db_session()
    user = session.query(User).filter_by(email=email).first()
    
    if not user:
        # Don't reveal if user exists - security best practice
        session.close()
        # Return success even if user doesn't exist to prevent email enumeration
        return jsonify({
            'message': 'If an account with that email exists, a password reset link has been sent.'
        }), 200
    
    # Check if account is active
    if not user.is_active:
        session.close()
        return jsonify({
            'message': 'If an account with that email exists, a password reset link has been sent.'
        }), 200
    
    # Generate reset token
    reset_token = create_reset_token(user)
    session.commit()
    session.close()
    
    # In production, send email with reset link
    # For now, we'll return the token (in production, this should be sent via email)
    reset_link = f"{request.host_url}reset-password?token={reset_token}"
    
    # TODO: Send email with reset_link
    # send_password_reset_email(user.email, reset_link)
    
    current_app.logger.info(f"Password reset requested for user {user.id} ({user.email})")
    
    # In development/testing, return the token
    # In production, always return the same message
    if current_app.config.get('ENVIRONMENT') == 'development':
        return jsonify({
            'message': 'Password reset token generated',
            'reset_token': reset_token,  # Only in development!
            'reset_link': reset_link
        }), 200
    else:
        return jsonify({
            'message': 'If an account with that email exists, a password reset link has been sent.'
        }), 200

@password_reset_bp.route('/verify', methods=['POST'])
def verify_reset_token_endpoint():
    """Verify a password reset token is valid."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    token = data.get('token', '').strip()
    
    if not token:
        return jsonify({'error': 'Reset token is required'}), 400
    
    session = get_db_session()
    
    # Find user with matching token hash
    token_hash = hash_reset_token(token)
    user = session.query(User).filter_by(password_reset_token=token_hash).first()
    
    if not user:
        session.close()
        return jsonify({'error': 'Invalid or expired reset token'}), 401
    
    # Verify token
    if not verify_reset_token(user, token):
        session.close()
        return jsonify({'error': 'Invalid or expired reset token'}), 401
    
    session.close()
    
    return jsonify({
        'valid': True,
        'message': 'Reset token is valid',
        'email': user.email  # Return email for confirmation
    }), 200

@password_reset_bp.route('/reset', methods=['POST'])
def reset_password():
    """Reset password using a valid reset token."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    token = data.get('token', '').strip()
    new_password = data.get('new_password', '')
    
    if not token:
        return jsonify({'error': 'Reset token is required'}), 400
    
    if not new_password:
        return jsonify({'error': 'New password is required'}), 400
    
    # Validate password
    password_valid, password_error = validate_password(new_password)
    if not password_valid:
        return jsonify({'error': password_error}), 400
    
    session = get_db_session()
    
    # Find user with matching token hash
    token_hash = hash_reset_token(token)
    user = session.query(User).filter_by(password_reset_token=token_hash).first()
    
    if not user:
        session.close()
        return jsonify({'error': 'Invalid or expired reset token'}), 401
    
    # Verify token
    if not verify_reset_token(user, token):
        session.close()
        return jsonify({'error': 'Invalid or expired reset token'}), 401
    
    # Check if account is active
    if not user.is_active:
        session.close()
        return jsonify({'error': 'Account is disabled'}), 403
    
    # Set new password
    user.set_password(new_password)
    
    # Clear reset token
    user.password_reset_token = None
    user.password_reset_expires = None
    
    # Reset failed login attempts
    user.reset_failed_logins()
    
    session.commit()
    session.close()
    
    current_app.logger.info(f"Password reset successful for user {user.id} ({user.email})")
    
    return jsonify({
        'message': 'Password has been reset successfully'
    }), 200

@password_reset_bp.route('/change', methods=['POST'])
def change_password():
    """Change password for authenticated user (requires current password)."""
    from auth.decorators import require_auth
    from auth.jwt_utils import get_current_user
    
    # Get current user (this endpoint requires authentication)
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    current_password = data.get('current_password', '')
    new_password = data.get('new_password', '')
    
    if not current_password or not new_password:
        return jsonify({'error': 'Current password and new password are required'}), 400
    
    # Validate new password
    password_valid, password_error = validate_password(new_password)
    if not password_valid:
        return jsonify({'error': password_error}), 400
    
    session = get_db_session()
    db_user = session.query(User).filter_by(id=user.id).first()
    
    if not db_user:
        session.close()
        return jsonify({'error': 'User not found'}), 404
    
    # Verify current password
    if not db_user.check_password(current_password):
        session.close()
        return jsonify({'error': 'Current password is incorrect'}), 401
    
    # Set new password
    db_user.set_password(new_password)
    
    # Clear any reset tokens
    db_user.password_reset_token = None
    db_user.password_reset_expires = None
    
    session.commit()
    session.close()
    
    current_app.logger.info(f"Password changed for user {user.id} ({user.email})")
    
    return jsonify({
        'message': 'Password has been changed successfully'
    }), 200

# Apply require_auth decorator
from auth.decorators import require_auth as require_auth_decorator
change_password = require_auth_decorator(change_password)
