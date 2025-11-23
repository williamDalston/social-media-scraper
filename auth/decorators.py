from functools import wraps
from flask import request, jsonify
from .jwt_utils import get_current_user

def require_auth(f):
    """
    Decorator to require authentication for an endpoint.
    Provides detailed error messages for debugging (in development).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please provide a valid JWT token in the Authorization header',
                'format': 'Authorization: Bearer <token>'
            }), 401
        
        user = get_current_user()
        if not user:
            return jsonify({
                'error': 'Invalid or expired token',
                'message': 'The provided token is invalid, expired, or the user account is inactive'
            }), 401
        
        # Attach user to request context
        request.current_user = user
        return f(*args, **kwargs)
    return decorated_function

def require_role(required_role: str):
    """
    Decorator factory to require a specific role.
    
    Args:
        required_role: Required role (Admin, Editor, Viewer)
    """
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user or user.role != required_role:
                return jsonify({'error': f'Insufficient permissions. Required role: {required_role}'}), 403
            request.current_user = user
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_any_role(allowed_roles: list):
    """
    Decorator factory to require one of the specified roles.
    
    Args:
        allowed_roles: List of allowed roles (e.g., ['Admin', 'Editor'])
    """
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user or user.role not in allowed_roles:
                return jsonify({
                    'error': f'Insufficient permissions. Required one of: {", ".join(allowed_roles)}'
                }), 403
            request.current_user = user
            return f(*args, **kwargs)
        return decorated_function
    return decorator

