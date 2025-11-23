"""
Security policy enforcement middleware.
"""
from flask import request, jsonify, g
from functools import wraps
import re

# Security policies
SECURITY_POLICIES = {
    'require_https': True,  # Require HTTPS in production
    'require_secure_headers': True,  # Require security headers
    'block_suspicious_paths': True,  # Block access to suspicious paths
    'enforce_content_type': True,  # Enforce proper content types
    'validate_request_size': True,  # Validate request size limits
    'block_known_attack_patterns': True,  # Block known attack patterns
}

# Suspicious path patterns
SUSPICIOUS_PATHS = [
    r'\.\./',  # Path traversal
    r'\.env',  # Environment files
    r'config\.php',  # Config files
    r'wp-admin',  # WordPress admin
    r'admin\.php',  # Admin scripts
    r'\.git',  # Git directories
    r'\.svn',  # SVN directories
]

# Known attack patterns in request data
ATTACK_PATTERNS = [
    r'<script[^>]*>',  # XSS attempts
    r'union.*select',  # SQL injection
    r'exec\(',  # Code execution
    r'eval\(',  # Code evaluation
    r'\.\./',  # Path traversal
    r'javascript:',  # JavaScript protocol
    r'on\w+\s*=',  # Event handlers
]

# Request size limits (in bytes)
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
MAX_JSON_SIZE = 1 * 1024 * 1024  # 1MB

def check_security_policies():
    """
    Check security policies for the current request.
    
    Returns:
        Tuple of (violation_found, violation_message)
    """
    if not request:
        return False, None
    
    # Check HTTPS requirement (in production)
    if SECURITY_POLICIES['require_https']:
        if not request.is_secure and request.headers.get('X-Forwarded-Proto') != 'https':
            # Allow in development
            if request.environ.get('SERVER_NAME', '').startswith('localhost'):
                pass  # Allow HTTP in development
            else:
                return True, 'HTTPS required'
    
    # Check suspicious paths
    if SECURITY_POLICIES['block_suspicious_paths']:
        path = request.path.lower()
        for pattern in SUSPICIOUS_PATHS:
            if re.search(pattern, path, re.IGNORECASE):
                return True, f'Suspicious path pattern detected: {pattern}'
    
    # Check request size
    if SECURITY_POLICIES['validate_request_size']:
        content_length = request.content_length
        if content_length and content_length > MAX_REQUEST_SIZE:
            return True, f'Request size exceeds maximum allowed size: {MAX_REQUEST_SIZE} bytes'
        
        # Check JSON size
        if request.is_json:
            try:
                data = request.get_json()
                import json
                json_size = len(json.dumps(data))
                if json_size > MAX_JSON_SIZE:
                    return True, f'JSON payload size exceeds maximum: {MAX_JSON_SIZE} bytes'
            except Exception:
                pass
    
    # Check for attack patterns in request data
    if SECURITY_POLICIES['block_known_attack_patterns']:
        # Check URL parameters
        for key, value in request.args.items():
            if isinstance(value, str):
                for pattern in ATTACK_PATTERNS:
                    if re.search(pattern, value, re.IGNORECASE):
                        return True, f'Attack pattern detected in parameter {key}: {pattern}'
        
        # Check form data
        if request.form:
            for key, value in request.form.items():
                if isinstance(value, str):
                    for pattern in ATTACK_PATTERNS:
                        if re.search(pattern, value, re.IGNORECASE):
                            return True, f'Attack pattern detected in form field {key}: {pattern}'
        
        # Check JSON data
        if request.is_json:
            try:
                data = request.get_json()
                data_str = str(data)
                for pattern in ATTACK_PATTERNS:
                    if re.search(pattern, data_str, re.IGNORECASE):
                        return True, f'Attack pattern detected in JSON data: {pattern}'
            except Exception:
                pass
    
    return False, None

def enforce_security_policy(f):
    """
    Decorator to enforce security policies on an endpoint.
    
    Args:
        f: Flask route function
    
    Returns:
        Decorated function
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        violation, message = check_security_policies()
        
        if violation:
            # Log the violation
            try:
                from auth.audit import log_security_event
                log_security_event(
                    'security_policy_violation',
                    ip_address=request.remote_addr if request else None,
                    resource_type='security_policy',
                    action='violation',
                    details={'message': message, 'path': request.path if request else None},
                    success=False,
                    error_message=message
                )
            except Exception:
                pass  # Don't fail if logging fails
        
        if violation:
            return jsonify({
                'error': 'Security policy violation',
                'message': message
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function

