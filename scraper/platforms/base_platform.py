"""
Base class for platform-specific scrapers.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from ..utils.errors import (
    ScraperError,
    RateLimitError,
    AccountNotFoundError,
    PrivateAccountError,
    NetworkError,
)
from ..utils.rate_limiter import get_rate_limiter, RateLimitExceeded
from ..utils.proxy_manager import get_proxy_manager
from ..utils.retry import retry_with_backoff
from ..utils.validators import validate_scraped_data
from ..config import ScraperConfig
from .config import get_headers, get_timeout, get_retry_count

logger = logging.getLogger(__name__)


class BasePlatformScraper(ABC):
    """
    Base class for all platform scrapers.
    Provides common functionality like rate limiting, retry logic, and error handling.
    """

    def __init__(self, platform: str, max_sleep_seconds: Optional[float] = None):
        """
        Initialize base scraper.

        Args:
            platform: Platform name (e.g., 'x', 'instagram', 'youtube')
            max_sleep_seconds: Maximum time to sleep when rate limited. If None, waits indefinitely.
        """
        self.platform = platform
        self.rate_limiter = get_rate_limiter(platform, max_sleep_seconds=max_sleep_seconds)
        self.proxy_manager = get_proxy_manager() if ScraperConfig.USE_PROXY else None
        self.timeout = get_timeout(platform)
        self.max_retries = get_retry_count(platform)
        self.headers = get_headers(platform)

        logger.info(f"Initialized {platform} scraper")

    @abstractmethod
    def scrape_account(
        self, account_url: str, handle: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Scrape account data from a platform.

        Args:
            account_url: Full URL to the account
            handle: Account handle (optional, for convenience)

        Returns:
            Dictionary with scraped data:
            {
                'followers_count': int,
                'following_count': int,
                'posts_count': int,
                'likes_count': int,
                'comments_count': int,
                'shares_count': int,
                'subscribers_count': int,  # For YouTube
                'views_count': int,  # For YouTube
            }

        Raises:
            ScraperError: For various scraper errors
        """
        pass

    def _apply_rate_limit(self):
        """Apply rate limiting before making a request."""
        self.rate_limiter.wait_if_needed()

    def _get_proxy(self) -> Optional[dict]:
        """Get proxy configuration if available."""
        if self.proxy_manager:
            return self.proxy_manager.get_proxy()
        return None

    def _handle_error(self, error: Exception, account_url: str):
        """
        Handle errors and convert to appropriate scraper exceptions.

        Args:
            error: The exception that occurred
            account_url: URL that was being scraped
        """
        error_str = str(error).lower()

        if "429" in error_str or "rate limit" in error_str:
            raise RateLimitError(f"Rate limit exceeded for {self.platform}")
        elif "401" in error_str or "403" in error_str or "unauthorized" in error_str:
            raise PrivateAccountError(
                f"Account is private or unauthorized: {account_url}"
            )
        elif "404" in error_str or "not found" in error_str:
            raise AccountNotFoundError(f"Account not found: {account_url}")
        elif "timeout" in error_str or "connection" in error_str:
            raise NetworkError(f"Network error: {error}")
        else:
            raise ScraperError(f"Scraper error for {self.platform}: {error}")

    def scrape(self, account) -> Optional[Dict[str, Any]]:
        """
        Main scrape method that applies rate limiting and retry logic.

        Args:
            account: Account object with account_url and handle attributes

        Returns:
            Scraped data dictionary or None if scraping fails
        """
        try:
            # Apply rate limiting
            self._apply_rate_limit()

            # Scrape with retry logic
            @retry_with_backoff(
                max_retries=self.max_retries,
                retryable_exceptions=(
                    RateLimitError,
                    NetworkError,
                    ConnectionError,
                    TimeoutError,
                ),
            )
            def _scrape_with_retry():
                raw_data = self.scrape_account(account.account_url, account.handle)
                # Validate and sanitize the data
                if raw_data:
                    return validate_scraped_data(raw_data, self.platform)
                return None

            return _scrape_with_retry()

        except AccountNotFoundError:
            logger.warning(f"Account not found: {account.account_url}")
            return None
        except PrivateAccountError:
            logger.warning(f"Account is private: {account.account_url}")
            return None
        except RateLimitError as e:
            logger.error(f"Rate limit exceeded for {self.platform}: {e}")
            return None
        except RateLimitExceeded as e:
            logger.warning(f"Rate limit wait time too long for {self.platform}, skipping: {e}")
            return None
        except ScraperError as e:
            logger.error(f"Scraper error for {self.platform}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error scraping {account.account_url}: {e}")
            return None
