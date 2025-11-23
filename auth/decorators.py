from functools import wraps
from flask import request, jsonify
from .jwt_utils import get_current_user
from .api_keys import verify_api_key
from .ip_filter import is_ip_allowed, get_client_ip

def require_auth(f):
    """
    Decorator to require authentication for an endpoint.
    Supports both JWT tokens and API keys.
    Also checks IP whitelist/blacklist.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check IP filtering first
        ip_allowed, ip_reason = is_ip_allowed()
        if not ip_allowed:
            return jsonify({
                'error': 'Access denied',
                'message': ip_reason
            }), 403
        
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please provide a valid JWT token or API key in the Authorization header',
                'format': 'Authorization: Bearer <token> or Authorization: ApiKey <key>'
            }), 401
        
        user = None
        
        # Try JWT authentication first
        if auth_header.startswith('Bearer '):
            user = get_current_user()
        # Try API key authentication
        elif auth_header.startswith('ApiKey ') or auth_header.startswith('apikey '):
            api_key = auth_header.split(' ', 1)[1] if ' ' in auth_header else auth_header
            user = verify_api_key(api_key)
        
        if not user:
            return jsonify({
                'error': 'Invalid or expired credentials',
                'message': 'The provided token or API key is invalid, expired, or the user account is inactive'
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

