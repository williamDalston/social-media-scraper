from flask import Blueprint, request, jsonify, current_app
from sqlalchemy.orm import sessionmaker
from scraper.schema import init_db
from models.user import User, UserRole
from .jwt_utils import generate_token, verify_token, get_current_user, get_db_session
from .decorators import require_auth
from .validators import validate_email, validate_password, validate_username
from datetime import datetime
import os

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# Rate limiting will be applied in app.py after blueprint registration

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Register a new user.
    Note: In production, this should be admin-only. For now, we'll allow registration
    but the first user will be admin.
    """
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    username = data.get('username', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    role = data.get('role', UserRole.VIEWER.value)
    
    # Validate input
    username_valid, username_error = validate_username(username)
    if not username_valid:
        return jsonify({'error': username_error}), 400
    
    email_valid, email_error = validate_email(email)
    if not email_valid:
        return jsonify({'error': email_error}), 400
    
    password_valid, password_error = validate_password(password)
    if not password_valid:
        return jsonify({'error': password_error}), 400
    
    # Check if role is valid
    valid_roles = [r.value for r in UserRole]
    if role not in valid_roles:
        return jsonify({'error': f'Invalid role. Must be one of: {", ".join(valid_roles)}'}), 400
    
    session = get_db_session()
    
    # Check if user already exists
    existing_user = session.query(User).filter(
        (User.username == username) | (User.email == email)
    ).first()
    
    if existing_user:
        session.close()
        return jsonify({'error': 'Username or email already exists'}), 409
    
    # Check if this is the first user (make them admin)
    user_count = session.query(User).count()
    if user_count == 0:
        role = UserRole.ADMIN.value
    
    # Create new user
    user = User(
        username=username,
        email=email,
        role=role,
        is_active=True
    )
    user.set_password(password)
    
    session.add(user)
    session.commit()
    
    user_id = user.id
    session.close()
    
    # Generate tokens
    tokens = generate_token(user_id, role)
    
    return jsonify({
        'message': 'User registered successfully',
        'user': {
            'id': user_id,
            'username': username,
            'email': email,
            'role': role
        },
        **tokens
    }), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    """Login and return JWT token."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    username = data.get('username', '').strip()
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    session = get_db_session()
    
    # Find user by username or email
    user = session.query(User).filter(
        (User.username == username) | (User.email == username)
    ).first()
    
    # Check if user exists and account is not locked
    if not user:
        # Don't reveal if user exists - security best practice
        session.close()
        return jsonify({'error': 'Invalid username or password'}), 401
    
    # Check if account is locked
    if user.is_locked():
        session.close()
        return jsonify({
            'error': 'Account is temporarily locked due to multiple failed login attempts. Please try again later.'
        }), 403
    
    # Check if account is active
    if not user.is_active:
        session.close()
        return jsonify({'error': 'Account is disabled'}), 403
    
    # Verify password
    if not user.check_password(password):
        # Record failed login attempt
        user.record_failed_login()
        session.commit()
        session.close()
        return jsonify({'error': 'Invalid username or password'}), 401
    
    # Update last login and reset failed login attempts
    user.last_login = datetime.utcnow()
    user.reset_failed_logins()
    session.commit()
    
    user_id = user.id
    role = user.role
    session.close()
    
    # Generate tokens
    access_token = generate_token(user_id, role, 'access')
    refresh_token = generate_token(user_id, role, 'refresh')
    
    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user_id,
            'username': user.username,
            'email': user.email,
            'role': role
        },
        'access_token': access_token['token'],
        'refresh_token': refresh_token['token'],
        'expires_in': access_token['expires_in']
    }), 200

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """
    Logout endpoint.
    Note: With JWT, logout is typically handled client-side by removing the token.
    This endpoint can be used for server-side token blacklisting if needed.
    """
    return jsonify({'message': 'Logout successful'}), 200

@auth_bp.route('/me', methods=['GET'])
@require_auth
def get_current_user_info():
    """Get current authenticated user information."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify({
        'user': user.to_dict()
    }), 200

@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """Refresh access token using refresh token."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    refresh_token_str = data.get('refresh_token', '')
    
    if not refresh_token_str:
        return jsonify({'error': 'Refresh token is required'}), 400
    
    try:
        payload = verify_token(refresh_token_str)
        
        if payload.get('type') != 'refresh':
            return jsonify({'error': 'Invalid token type'}), 401
        
        user_id = payload.get('user_id')
        role = payload.get('role')
        
        session = get_db_session()
        user = session.query(User).filter_by(id=user_id, is_active=True).first()
        session.close()
        
        if not user:
            return jsonify({'error': 'User not found or inactive'}), 401
        
        # Generate new access token
        access_token = generate_token(user_id, role, 'access')
        
        return jsonify({
            'access_token': access_token['token'],
            'expires_in': access_token['expires_in']
        }), 200
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 401

