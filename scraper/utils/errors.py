"""
Custom exceptions for scraper operations.
"""


class ScraperError(Exception):
    """Base exception for all scraper-related errors."""
    pass


class RateLimitError(ScraperError):
    """Raised when rate limit is exceeded."""
    def __init__(self, message="Rate limit exceeded", retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after  # Seconds to wait before retrying


class AuthenticationError(ScraperError):
    """Raised when authentication fails."""
    pass


class AccountNotFoundError(ScraperError):
    """Raised when an account cannot be found."""
    pass


class PrivateAccountError(ScraperError):
    """Raised when attempting to access a private account."""
    pass


class NetworkError(ScraperError):
    """Raised when a network error occurs."""
    pass

