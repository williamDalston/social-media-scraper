"""
Utility modules for scrapers.
"""

from .errors import (
    ScraperError,
    RateLimitError,
    AuthenticationError,
    AccountNotFoundError,
    PrivateAccountError,
    NetworkError,
)

from .retry import retry_with_backoff
from .rate_limiter import RateLimiter
from .proxy_manager import ProxyManager
from .parsers import parse_follower_count, parse_engagement_metrics
from .validators import validate_scraped_data

__all__ = [
    'ScraperError',
    'RateLimitError',
    'AuthenticationError',
    'AccountNotFoundError',
    'PrivateAccountError',
    'NetworkError',
    'retry_with_backoff',
    'RateLimiter',
    'ProxyManager',
    'parse_follower_count',
    'parse_engagement_metrics',
    'validate_scraped_data',
]

