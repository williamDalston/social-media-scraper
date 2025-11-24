"""
API v1 module.

This module contains all version 1 API endpoints organized by namespace.
"""

from .auth import ns as auth_ns
from .metrics import ns as metrics_ns
from .accounts import ns as accounts_ns
from .jobs import ns as jobs_ns
from .admin import ns as admin_ns
from .job_monitoring import ns as job_monitoring_ns

__all__ = [
    "auth_ns",
    "metrics_ns",
    "accounts_ns",
    "jobs_ns",
    "admin_ns",
    "job_monitoring_ns",
]
