"""
Structured logging configuration for the HHS Social Media Scraper.
Supports JSON logging for production and readable format for development.
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from pythonjsonlogger import jsonlogger


def setup_logging(log_level=None, log_format=None, log_file=None):
    """
    Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: 'json' for structured JSON logs, 'text' for readable format
        log_file: Path to log file (optional, logs to console if not provided)
    """
    # Get configuration from environment or use defaults
    log_level = log_level or os.getenv("LOG_LEVEL", "INFO").upper()
    log_format = log_format or os.getenv("LOG_FORMAT", "text").lower()

    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level, logging.INFO)

    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers = []

    # Create formatters
    if log_format == "json":
        formatter = jsonlogger.JsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s", timestamp=True
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Console handler (always add)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (if log_file is specified)
    if log_file:
        # Use rotating file handler to prevent disk fill
        file_handler = RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Also set up time-based rotation for daily logs (optional)
    if log_file and os.getenv("ENABLE_DAILY_LOGS", "false").lower() == "true":
        daily_handler = TimedRotatingFileHandler(
            log_file.replace(".log", "_daily.log"),
            when="midnight",
            interval=1,
            backupCount=30,  # Keep 30 days
        )
        daily_handler.setLevel(numeric_level)
        daily_handler.setFormatter(formatter)
        root_logger.addHandler(daily_handler)

    # Set specific logger levels
    logging.getLogger("werkzeug").setLevel(logging.WARNING)  # Reduce Flask noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)  # Reduce HTTP noise

    return root_logger


def get_logger(name):
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
