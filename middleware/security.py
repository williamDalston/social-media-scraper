from flask import Flask
from functools import wraps

def setup_security_headers(app: Flask):
    """
    Add security headers to all responses.
    """
    @app.after_request
    def add_security_headers(response):
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        
        # Enable XSS protection
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Content Security Policy
        # Adjust based on your needs
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "  # Allow inline for simplicity
            "style-src 'self' 'unsafe-inline'; "  # Allow inline styles
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response.headers['Content-Security-Policy'] = csp
        
        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy (formerly Feature Policy)
        response.headers['Permissions-Policy'] = (
            'geolocation=(), microphone=(), camera=()'
        )
        
        return response

