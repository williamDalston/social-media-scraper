"""
Sentry error tracking configuration for the HHS Social Media Scraper.
"""
import os
import logging
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.logging import LoggingIntegration


def init_sentry():
    """
    Initialize Sentry for error tracking.
    Reads configuration from environment variables.
    """
    sentry_dsn = os.getenv("SENTRY_DSN")

    if not sentry_dsn:
        # Sentry is optional, so we don't fail if DSN is not provided
        return False

    environment = os.getenv("ENVIRONMENT", "development")
    release = os.getenv("RELEASE_VERSION", "unknown")
    traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))

    # Configure logging integration to capture errors
    logging_integration = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR,  # Send errors and above as events
    )

    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=environment,
        release=release,
        traces_sample_rate=traces_sample_rate,
        integrations=[FlaskIntegration(), SqlalchemyIntegration(), logging_integration],
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        profiles_sample_rate=1.0,
        # Enable sending of PII (Personally Identifiable Information)
        send_default_pii=False,  # Set to True if you need to track user info
    )

    return True


def capture_exception(error, context=None):
    """
    Manually capture an exception with additional context.

    Args:
        error: Exception object
        context: Dictionary with additional context (account_key, platform, etc.)
    """
    if context:
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_context(key, value)
            sentry_sdk.capture_exception(error)
    else:
        sentry_sdk.capture_exception(error)


def capture_message(message, level="info", context=None):
    """
    Capture a message with optional context.

    Args:
        message: Message string
        level: Severity level ('info', 'warning', 'error')
        context: Dictionary with additional context
    """
    if context:
        with sentry_sdk.push_scope() as scope:
            for key, value in context.items():
                scope.set_context(key, value)
            sentry_sdk.capture_message(message, level=level)
    else:
        sentry_sdk.capture_message(message, level=level)
