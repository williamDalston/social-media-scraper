"""
Main scraper interface that routes to platform-specific scrapers.
"""

import random
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

# Import platform-specific scrapers
from .platforms import (
    XScraper,
    InstagramScraper,
    FacebookScraper,
    LinkedInScraper,
    YouTubeScraper,
    TruthScraper,
    TikTokScraper,
    RedditScraper,
    FlickrScraper,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base class for all scrapers."""

    @abstractmethod
    def scrape(self, account):
        """
        Scrape account data.

        Args:
            account: Account object with platform, account_url, handle attributes

        Returns:
            Dictionary with scraped metrics or None if scraping fails
        """
        pass


class SimulatedScraper(BaseScraper):
    """Simulated scraper for testing/development."""

    def scrape(self, account):
        """
        Generate simulated metrics for an account.

        Args:
            account: Account object

        Returns:
            Dictionary with simulated metrics
        """
        base_followers = 10000
        if account.org_name == "HHS":
            base_followers = 500000

        followers = base_followers + random.randint(-100, 500)

        return {
            "followers_count": followers,
            "following_count": random.randint(10, 500),
            "posts_count": random.randint(0, 5),
            "likes_count": random.randint(50, 5000),
            "comments_count": random.randint(5, 500),
            "shares_count": random.randint(10, 1000),
            "subscribers_count": 0,  # For YouTube compatibility
            "views_count": 0,  # For YouTube compatibility
        }


class RealScraper(BaseScraper):
    """
    Real scraper that routes to platform-specific scrapers.
    """

    # Map platform names to scraper classes
    PLATFORM_SCRAPERS = {
        "x": XScraper,
        "twitter": XScraper,  # Alias for x
        "instagram": InstagramScraper,
        "facebook": FacebookScraper,
        "facebook español": FacebookScraper,  # Spanish Facebook pages
        "linkedin": LinkedInScraper,
        "youtube": YouTubeScraper,
        "truth_social": TruthScraper,
        "truth": TruthScraper,  # Alias
        "truth social": TruthScraper,  # With space
        "tiktok": TikTokScraper,
        "reddit": RedditScraper,
        "flickr": FlickrScraper,
    }

    def __init__(self, max_sleep_seconds: Optional[float] = None):
        """
        Initialize the real scraper with platform-specific scrapers.
        
        Args:
            max_sleep_seconds: Maximum time to sleep when rate limited. If None, waits indefinitely.
        """
        self._scrapers = {}
        self.max_sleep_seconds = max_sleep_seconds
        logger.info("Initialized RealScraper with platform-specific scrapers")

    def _get_scraper_for_platform(self, platform: str):
        """
        Get or create a scraper instance for a platform.

        Args:
            platform: Platform name (e.g., 'x', 'instagram', 'youtube')

        Returns:
            Platform scraper instance or None if platform not supported
        """
        # Normalize platform name
        platform = platform.lower().strip()

        # Normalize common variations
        platform_normalizations = {
            "facebook español": "facebook",
            "facebook espanol": "facebook",
            "truth social": "truth_social",
            "twitter": "x",
        }

        # Apply normalization
        if platform in platform_normalizations:
            platform = platform_normalizations[platform]

        # Check cache first
        if platform in self._scrapers:
            return self._scrapers[platform]

        # Get scraper class
        scraper_class = self.PLATFORM_SCRAPERS.get(platform)

        if not scraper_class:
            logger.warning(f"No scraper available for platform: {platform}")
            return None

        # Create and cache scraper instance
        try:
            # All platform scrapers now accept max_sleep_seconds
            scraper = scraper_class(max_sleep_seconds=self.max_sleep_seconds)
            self._scrapers[platform] = scraper
            return scraper
        except TypeError:
            # Fallback for scrapers that don't accept max_sleep_seconds yet
            try:
                scraper = scraper_class()
                # Manually update rate limiter if scraper has one
                if hasattr(scraper, 'rate_limiter'):
                    scraper.rate_limiter.max_sleep_seconds = self.max_sleep_seconds
                self._scrapers[platform] = scraper
                return scraper
            except Exception as e:
                logger.error(f"Failed to initialize scraper for {platform}: {e}")
                return None
        except Exception as e:
            logger.error(f"Failed to initialize scraper for {platform}: {e}")
            return None

    def scrape(self, account) -> Optional[Dict[str, Any]]:
        """
        Scrape account data using platform-specific scraper.

        Args:
            account: Account object with platform, account_url, handle attributes

        Returns:
            Dictionary with scraped metrics or None if scraping fails
        """
        try:
            logger.info(
                f"Attempting to scrape {account.platform} account: {account.handle}",
                extra={
                    "account_key": account.account_key,
                    "platform": account.platform,
                    "handle": account.handle,
                    "url": account.account_url,
                },
            )

            # Get platform-specific scraper
            scraper = self._get_scraper_for_platform(account.platform)

            if not scraper:
                logger.warning(
                    f"Platform {account.platform} not supported. No data will be collected.",
                    extra={
                        "account_key": account.account_key,
                        "platform": account.platform,
                    },
                )
                return None

            # Scrape using platform scraper
            result = scraper.scrape(account)

            if result:
                logger.info(
                    f"Successfully scraped {account.platform} account: {account.handle}",
                    extra={
                        "account_key": account.account_key,
                        "platform": account.platform,
                        "handle": account.handle,
                        "followers": result.get("followers_count")
                        or result.get("subscribers_count", 0),
                    },
                )
            else:
                logger.warning(
                    f"Scraping returned no data for {account.platform} account: {account.handle}",
                    extra={
                        "account_key": account.account_key,
                        "platform": account.platform,
                        "handle": account.handle,
                    },
                )

            return result

        except Exception as e:
            logger.exception(
                f"Error scraping {account.platform} account: {account.handle}",
                extra={
                    "account_key": account.account_key,
                    "platform": account.platform,
                    "handle": account.handle,
                    "url": account.account_url,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            return None


def get_scraper(mode="real", max_sleep_seconds: Optional[float] = None):
    """
    Get a scraper instance.

    Args:
        mode: 'real' for real scraping (simulated mode disabled)
        max_sleep_seconds: Maximum time to sleep when rate limited. If None, waits indefinitely.

    Returns:
        Scraper instance (always RealScraper)
    """
    # Only real mode is supported - no simulations
    if mode != "real":
        logger.warning(
            f"Simulated mode requested but disabled. Using real scraper instead."
        )
    return RealScraper(max_sleep_seconds=max_sleep_seconds)
