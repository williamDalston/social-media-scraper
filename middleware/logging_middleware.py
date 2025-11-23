"""
Logging middleware for Flask application.
Logs all HTTP requests and responses with structured data.
Includes correlation ID support for distributed tracing.
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

# Try to import correlation ID utilities
try:
    from config.tracing_config import generate_correlation_id, get_correlation_id
    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False
    def generate_correlation_id():
        import uuid
        return str(uuid.uuid4())
    def get_correlation_id():
        return None


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
        
        # Generate or get correlation ID
        correlation_id = request.headers.get('X-Correlation-ID') or generate_correlation_id()
        g.correlation_id = correlation_id
        
        # Try to get trace ID from OpenTelemetry if available
        trace_id = get_correlation_id() if TRACING_AVAILABLE else None
        
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
                'correlation_id': correlation_id,
                'trace_id': trace_id,
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
        
        # Add correlation ID to response headers
        correlation_id = getattr(g, 'correlation_id', None)
        if correlation_id:
            response.headers['X-Correlation-ID'] = correlation_id
        
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
                'correlation_id': correlation_id,
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
        """Log unhandled exceptions with enhanced error detection."""
        # Calculate duration if available
        duration_ms = 0
        if hasattr(g, 'start_time'):
            duration_ms = (time.time() - g.start_time) * 1000
        
        # Enhanced error detection
        error_context = None
        fix_suggestion = None
        try:
            from config.error_detection import detect_error, get_fix_suggestion
            
            error_context = detect_error(error, context={
                'request_id': getattr(g, 'request_id', None),
                'user_id': getattr(g, 'user_id', None),
                'path': request.path,
                'method': request.method,
                'duration_ms': round(duration_ms, 2),
            })
            
            fix_suggestion = get_fix_suggestion(error_context)
        except Exception as e:
            # If error detection fails, log it but don't fail
            logger.debug(f"Error detection failed: {e}")
        
        # Log with enhanced context
        log_extra = {
            'method': request.method,
            'path': request.path,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'duration_ms': round(duration_ms, 2),
            'user_id': getattr(g, 'user_id', None),
        }
        
        if error_context:
            log_extra.update({
                'error_category': error_context.category.value,
                'error_severity': error_context.severity.value,
                'error_file': error_context.file_path,
                'error_line': error_context.line_number,
                'error_function': error_context.function_name,
            })
        
        if fix_suggestion:
            log_extra['fix_suggestion'] = fix_suggestion.description
            log_extra['fix_steps'] = fix_suggestion.steps
        
        logger.exception(
            "Unhandled exception",
            extra=log_extra
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

