"""
Logging middleware for Flask application.
Logs all HTTP requests and responses with structured data.
"""
import time
import logging
from functools import wraps
from flask import request, g

logger = logging.getLogger(__name__)

# Try to import metrics for recording
try:
    from config.metrics_config import record_request
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    record_request = None


def setup_request_logging(app):
    """
    Set up request/response logging middleware for Flask app.
    
    Args:
        app: Flask application instance
    """
    @app.before_request
    def log_request_info():
        """Log incoming request information."""
        g.start_time = time.time()
        
        # Log request details
        logger.info(
            "Incoming request",
            extra={
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr,
                'user_agent': request.headers.get('User-Agent'),
                'content_type': request.content_type,
                'content_length': request.content_length,
            }
        )
    
    @app.after_request
    def log_response_info(response):
        """Log response information after request completes."""
        # Calculate request duration
        duration_ms = (time.time() - g.start_time) * 1000
        
        # Get user info if available (from auth system)
        user_id = getattr(g, 'user_id', None)
        
        # Log response details
        log_level = logging.INFO
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING
        
        duration_seconds = duration_ms / 1000.0
        
        logger.log(
            log_level,
            "Request completed",
            extra={
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration_ms': round(duration_ms, 2),
                'duration_seconds': round(duration_seconds, 3),
                'response_size': response.content_length,
                'user_id': user_id,
                'remote_addr': request.remote_addr,
            }
        )
        
        # Record Prometheus metrics
        if METRICS_AVAILABLE and record_request:
            try:
                # Normalize endpoint path (remove IDs, etc.)
                endpoint = request.path
                # Remove common ID patterns for better aggregation
                import re
                endpoint = re.sub(r'/\d+', '/{id}', endpoint)
                endpoint = re.sub(r'/[a-f0-9-]{36}', '/{uuid}', endpoint)  # UUIDs
                
                record_request(
                    method=request.method,
                    endpoint=endpoint,
                    status=response.status_code,
                    duration=duration_seconds
                )
            except Exception as e:
                # Don't fail request if metrics recording fails
                logger.warning(f"Failed to record metrics: {e}")
        
        return response
    
    @app.errorhandler(Exception)
    def log_exception(error):
        """Log unhandled exceptions."""
        # Calculate duration if available
        duration_ms = 0
        if hasattr(g, 'start_time'):
            duration_ms = (time.time() - g.start_time) * 1000
        
        logger.exception(
            "Unhandled exception",
            extra={
                'method': request.method,
                'path': request.path,
                'error_type': type(error).__name__,
                'error_message': str(error),
                'duration_ms': round(duration_ms, 2),
                'user_id': getattr(g, 'user_id', None),
            }
        )
        
        # Record error metrics
        if METRICS_AVAILABLE and record_request:
            try:
                endpoint = request.path
                import re
                endpoint = re.sub(r'/\d+', '/{id}', endpoint)
                endpoint = re.sub(r'/[a-f0-9-]{36}', '/{uuid}', endpoint)
                
                record_request(
                    method=request.method,
                    endpoint=endpoint,
                    status=500,
                    duration=(time.time() - g.start_time) if hasattr(g, 'start_time') else 0
                )
            except Exception:
                pass  # Don't fail on metrics error
        
        # Re-raise to let Flask handle it
        raise error


def log_function_call(func_name, **kwargs):
    """
    Decorator to log function calls with context.
    
    Usage:
        @log_function_call("scrape_account")
        def scrape(account):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **func_kwargs):
            logger.debug(
                f"Calling {func_name}",
                extra={
                    'function': func_name,
                    **kwargs,
                    **func_kwargs
                }
            )
            try:
                result = func(*args, **func_kwargs)
                logger.debug(
                    f"{func_name} completed successfully",
                    extra={
                        'function': func_name,
                        **kwargs
                    }
                )
                return result
            except Exception as e:
                logger.exception(
                    f"{func_name} failed",
                    extra={
                        'function': func_name,
                        'error': str(e),
                        **kwargs
                    }
                )
                raise
        return wrapper
    return decorator

