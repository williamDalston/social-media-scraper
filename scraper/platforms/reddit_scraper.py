"""
Reddit scraper using web scraping and Reddit API.
"""

import re
import logging
from typing import Dict, Any, Optional

from .base_platform import BasePlatformScraper
from ..utils.errors import (
    AccountNotFoundError,
    ScraperError,
    RateLimitError,
    NetworkError,
    PrivateAccountError,
)
from ..utils.parsers import parse_follower_count
import requests

logger = logging.getLogger(__name__)


class RedditScraper(BasePlatformScraper):
    """Scraper for Reddit subreddits and users."""

    def __init__(self):
        super().__init__("reddit")

    def _extract_subreddit_from_url(self, url: str) -> Optional[str]:
        """
        Extract subreddit name from Reddit URL.

        Handles:
        - https://www.reddit.com/r/subreddit
        - https://reddit.com/r/subreddit
        - r/subreddit
        """
        # Remove r/ if present at start
        url = url.replace("r/", "")

        # Extract from URL
        match = re.search(r"reddit\.com/r/([a-zA-Z0-9_]+)", url)
        if match:
            return match.group(1)

        # If it's just a subreddit name
        match = re.search(r"^([a-zA-Z0-9_]+)$", url)
        if match:
            return match.group(1)

        return None

    def _normalize_url(self, account_url: str, handle: Optional[str] = None) -> str:
        """
        Normalize Reddit URL.

        Args:
            account_url: Original URL
            handle: Subreddit name if available

        Returns:
            Normalized URL
        """
        if handle:
            return f"https://www.reddit.com/r/{handle}/"

        subreddit = self._extract_subreddit_from_url(account_url)
        if subreddit:
            return f"https://www.reddit.com/r/{subreddit}/"

        return account_url

    def scrape_account(
        self, account_url: str, handle: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Scrape Reddit subreddit data via web scraping.

        Args:
            account_url: Reddit subreddit URL
            handle: Subreddit name (optional)

        Returns:
            Dictionary with subreddit metrics
        """
        normalized_url = self._normalize_url(account_url, handle)
        proxy = self._get_proxy()

        try:
            # Validate URL before making request
            if not normalized_url or not isinstance(normalized_url, str):
                raise ScraperError(f"Invalid URL: {normalized_url}")

            # Reddit requires User-Agent header
            headers = {
                **self.headers,
                "User-Agent": "Mozilla/5.0 (compatible; SocialMediaScraper/1.0)",
            }

            try:
                response = requests.get(
                    normalized_url,
                    headers=headers,
                    timeout=self.timeout,
                    proxies=proxy,
                    allow_redirects=True,
                )
            except requests.exceptions.Timeout:
                raise NetworkError(
                    f"Request timeout while fetching Reddit page: {normalized_url}"
                )
            except requests.exceptions.ConnectionError as conn_error:
                raise NetworkError(
                    f"Connection error while fetching Reddit page: {conn_error}"
                )
            except requests.exceptions.RequestException as req_error:
                raise ScraperError(
                    f"Request error while fetching Reddit page: {req_error}"
                )

            if response.status_code == 404:
                raise AccountNotFoundError(
                    f"Reddit subreddit not found: {normalized_url}"
                )

            if response.status_code == 429:
                raise RateLimitError(
                    f"Rate limit exceeded for Reddit: {normalized_url}"
                )

            if response.status_code in (401, 403):
                raise PrivateAccountError(
                    f"Reddit subreddit is private or unauthorized: {normalized_url}"
                )

            if response.status_code != 200:
                raise ScraperError(
                    f"Failed to fetch Reddit page: HTTP {response.status_code}"
                )

            from bs4 import BeautifulSoup

            # Validate response content
            if not response.text:
                logger.warning(f"Empty response from Reddit: {normalized_url}")
                raise ScraperError("Empty response from Reddit")

            try:
                soup = BeautifulSoup(response.text, "html.parser")
            except Exception as parse_error:
                logger.error(
                    f"Error parsing HTML: {parse_error}", extra={"url": normalized_url}
                )
                raise ScraperError(f"Failed to parse Reddit page: {parse_error}")

            subscribers = 0
            active_users = 0
            posts = 0

            # Reddit embeds data in various places
            # Look for subscriber count in meta tags
            try:
                meta_tags = soup.find_all("meta")
            except Exception as find_error:
                logger.warning(
                    f"Error finding meta tags: {find_error}",
                    extra={"url": normalized_url},
                )
                meta_tags = []

            for tag in meta_tags:
                name = tag.get("name", "") or tag.get("property", "")
                content = tag.get("content", "")

                if "subscribers" in name.lower() and content:
                    parsed = parse_follower_count(content)
                    if parsed:
                        subscribers = parsed

                if "members" in name.lower() and content:
                    parsed = parse_follower_count(content)
                    if parsed and subscribers == 0:
                        subscribers = parsed

            # Look in script tags (Reddit embeds JSON data)
            scripts = soup.find_all("script", type="application/json")
            for script in scripts:
                try:
                    import json

                    data = json.loads(script.string)

                    # Recursively search for subscriber count
                    def find_subscribers(obj):
                        nonlocal subscribers, active_users

                        if isinstance(obj, dict):
                            for key, value in obj.items():
                                key_lower = key.lower()
                                if "subscriber" in key_lower and isinstance(
                                    value, (int, str)
                                ):
                                    if isinstance(value, str):
                                        parsed = parse_follower_count(value)
                                        if parsed and subscribers == 0:
                                            subscribers = parsed
                                    elif isinstance(value, int) and subscribers == 0:
                                        subscribers = value

                                if "active" in key_lower and "user" in key_lower:
                                    if isinstance(value, (int, str)):
                                        if isinstance(value, str):
                                            active_users = (
                                                parse_follower_count(value) or 0
                                            )
                                        else:
                                            active_users = value

                                find_subscribers(value)
                        elif isinstance(obj, list):
                            for item in obj:
                                find_subscribers(item)

                    find_subscribers(data)

                except (json.JSONDecodeError, Exception) as e:
                    logger.debug(f"Error parsing Reddit JSON: {e}")

            # Fallback: search in text
            if subscribers == 0:
                text = soup.get_text()
                # Look for "X members" or "X subscribers" pattern
                match = re.search(
                    r"([\d.]+[KMBkmb]?)\s*(?:members?|subscribers?)",
                    text,
                    re.IGNORECASE,
                )
                if match:
                    subscribers = parse_follower_count(match.group(1)) or 0

            # If we still don't have data
            if subscribers == 0:
                logger.warning(
                    f"Could not extract data from Reddit page. Page structure may have changed."
                )
                return {
                    "followers_count": 0,
                    "following_count": 0,
                    "posts_count": 0,
                    "likes_count": 0,
                    "comments_count": 0,
                    "shares_count": 0,
                    "bio_text": "",
                    "verified_status": None,
                    "profile_image_url": "",
                    "account_created_date": None,
                    "account_category": None,
                    "account_type": "subreddit",
                }

            # Extract metadata
            bio_text = ""
            profile_image_url = ""

            return {
                "followers_count": subscribers,  # Reddit uses "subscribers" or "members"
                "following_count": 0,  # Reddit doesn't have following
                "posts_count": posts,
                "likes_count": 0,  # Would need to fetch individual posts
                "comments_count": 0,  # Would need to fetch individual posts
                "shares_count": 0,
                "bio_text": bio_text,
                "verified_status": None,
                "profile_image_url": profile_image_url,
                "account_created_date": None,
                "account_category": None,
                "account_type": "subreddit",
            }

        except AccountNotFoundError:
            raise
        except Exception as e:
            raise ScraperError(f"Error scraping Reddit subreddit: {e}")
