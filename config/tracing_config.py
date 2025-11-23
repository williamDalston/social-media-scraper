"""
Distributed tracing configuration using OpenTelemetry.
Provides request correlation IDs and distributed tracing capabilities.
"""
import os
import uuid
import logging
from functools import wraps

logger = logging.getLogger(__name__)

# Try to import OpenTelemetry (optional dependency)
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.instrumentation.flask import FlaskInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    trace = None
    FlaskInstrumentor = None
    RequestsInstrumentor = None
    SQLAlchemyInstrumentor = None


def init_tracing(app=None, service_name='hhs-social-media-scraper'):
    """
    Initialize OpenTelemetry tracing.
    
    Args:
        app: Flask application instance (optional)
        service_name: Name of the service for tracing
    
    Returns:
        bool: True if tracing was initialized, False otherwise
    """
    if not OPENTELEMETRY_AVAILABLE:
        logger.info("OpenTelemetry not available, using simple correlation IDs")
        return False
    
    try:
        # Create resource with service name
        resource = Resource.create({
            "service.name": service_name,
            "service.version": os.getenv('RELEASE_VERSION', 'unknown'),
            "deployment.environment": os.getenv('ENVIRONMENT', 'development')
        })
        
        # Set up tracer provider
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)
        
        # Add span processor based on environment
        otlp_endpoint = os.getenv('OTLP_ENDPOINT')
        if otlp_endpoint:
            # Use OTLP exporter if endpoint is configured
            exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            logger.info(f"OpenTelemetry tracing initialized with OTLP endpoint: {otlp_endpoint}")
        else:
            # Use console exporter for development
            console_exporter = ConsoleSpanExporter()
            provider.add_span_processor(BatchSpanProcessor(console_exporter))
            logger.info("OpenTelemetry tracing initialized with console exporter")
        
        # Instrument Flask if app is provided
        if app and FlaskInstrumentor:
            FlaskInstrumentor().instrument_app(app)
            logger.info("Flask instrumentation enabled")
        
        # Instrument requests library
        if RequestsInstrumentor:
            RequestsInstrumentor().instrument()
            logger.info("Requests library instrumentation enabled")
        
        # Instrument SQLAlchemy
        if SQLAlchemyInstrumentor:
            SQLAlchemyInstrumentor().instrument()
            logger.info("SQLAlchemy instrumentation enabled")
        
        return True
    except Exception as e:
        logger.warning(f"Failed to initialize OpenTelemetry tracing: {e}")
        return False


def get_tracer(name=None):
    """
    Get a tracer instance.
    
    Args:
        name: Name of the tracer (defaults to module name)
    
    Returns:
        Tracer instance or None if not available
    """
    if not OPENTELEMETRY_AVAILABLE or not trace:
        return None
    
    return trace.get_tracer(name or __name__)


def generate_correlation_id():
    """
    Generate a unique correlation ID for request tracking.
    
    Returns:
        str: UUID-based correlation ID
    """
    return str(uuid.uuid4())


def get_correlation_id():
    """
    Get the current correlation ID from the trace context.
    
    Returns:
        str: Correlation ID or None
    """
    if not OPENTELEMETRY_AVAILABLE or not trace:
        return None
    
    span = trace.get_current_span()
    if span and span.is_recording():
        trace_id = format(span.get_span_context().trace_id, '032x')
        return trace_id[:16]  # Return first 16 chars for readability
    
    return None


def trace_function(operation_name=None):
    """
    Decorator to trace a function call.
    
    Usage:
        @trace_function("scrape_account")
        def scrape(account):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            tracer = get_tracer()
            if tracer:
                with tracer.start_as_current_span(
                    operation_name or func.__name__,
                    attributes={
                        'function': func.__name__,
                        'module': func.__module__
                    }
                ):
                    return func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        return wrapper
    return decorator

