"""
Flickr scraper using web scraping.
"""

import re
import logging
from typing import Dict, Any, Optional

from .base_platform import BasePlatformScraper
from ..utils.errors import (
    AccountNotFoundError,
    ScraperError,
    PrivateAccountError,
    RateLimitError,
    NetworkError,
)
from ..utils.parsers import parse_follower_count
import requests

logger = logging.getLogger(__name__)


class FlickrScraper(BasePlatformScraper):
    """Scraper for Flickr accounts."""

    def __init__(self, max_sleep_seconds: Optional[float] = None):
        super().__init__("flickr", max_sleep_seconds=max_sleep_seconds)

    def _extract_user_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract user ID or username from Flickr URL.

        Handles:
        - https://www.flickr.com/photos/username/
        - https://flickr.com/photos/username
        - https://www.flickr.com/people/username/
        """
        # Extract username or user ID from /photos/ or /people/
        match = re.search(r"flickr\.com/(?:photos|people)/([^/?]+)", url)
        if match:
            return match.group(1)

        return None

    def _normalize_url(self, account_url: str, handle: Optional[str] = None) -> str:
        """
        Normalize Flickr URL.

        Args:
            account_url: Original URL
            handle: Username if available

        Returns:
            Normalized URL
        """
        if handle:
            return f"https://www.flickr.com/photos/{handle}/"

        user_id = self._extract_user_id_from_url(account_url)
        if user_id:
            return f"https://www.flickr.com/photos/{user_id}/"

        return account_url

    def scrape_account(
        self, account_url: str, handle: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Scrape Flickr account data via web scraping.

        Args:
            account_url: Flickr account URL
            handle: Account username (optional)

        Returns:
            Dictionary with account metrics
        """
        normalized_url = self._normalize_url(account_url, handle)
        proxy = self._get_proxy()

        try:
            # Validate URL before making request
            if not normalized_url or not isinstance(normalized_url, str):
                raise ScraperError(f"Invalid URL: {normalized_url}")

            try:
                response = requests.get(
                    normalized_url,
                    headers=self.headers,
                    timeout=self.timeout,
                    proxies=proxy,
                    allow_redirects=True,
                )
            except requests.exceptions.Timeout:
                raise NetworkError(
                    f"Request timeout while fetching Flickr page: {normalized_url}"
                )
            except requests.exceptions.ConnectionError as conn_error:
                raise NetworkError(
                    f"Connection error while fetching Flickr page: {conn_error}"
                )
            except requests.exceptions.RequestException as req_error:
                raise ScraperError(
                    f"Request error while fetching Flickr page: {req_error}"
                )

            if response.status_code == 404:
                raise AccountNotFoundError(
                    f"Flickr account not found: {normalized_url}"
                )

            if response.status_code == 429:
                raise RateLimitError(
                    f"Rate limit exceeded for Flickr: {normalized_url}"
                )

            if response.status_code == 403:
                raise PrivateAccountError(
                    f"Flickr account is private: {normalized_url}"
                )

            if response.status_code != 200:
                raise ScraperError(
                    f"Failed to fetch Flickr page: HTTP {response.status_code}"
                )

            from bs4 import BeautifulSoup

            # Validate response content
            if not response.text:
                logger.warning(f"Empty response from Flickr: {normalized_url}")
                raise ScraperError("Empty response from Flickr")

            try:
                soup = BeautifulSoup(response.text, "html.parser")
            except Exception as parse_error:
                logger.error(
                    f"Error parsing HTML: {parse_error}", extra={"url": normalized_url}
                )
                raise ScraperError(f"Failed to parse Flickr page: {parse_error}")

            followers = 0
            following = 0
            photos = 0

            # Flickr embeds data in various places
            # Look in meta tags
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

                if "followers" in name.lower() and content:
                    parsed = parse_follower_count(content)
                    if parsed:
                        followers = parsed

                if "following" in name.lower() and content:
                    parsed = parse_follower_count(content)
                    if parsed:
                        following = parsed

                if "photos" in name.lower() or "photostream" in name.lower():
                    if content:
                        parsed = parse_follower_count(content)
                        if parsed:
                            photos = parsed

            # Look in script tags (Flickr uses JSON-LD)
            scripts = soup.find_all("script", type="application/ld+json")
            for script in scripts:
                try:
                    import json

                    data = json.loads(script.string)

                    if isinstance(data, dict):
                        if "interactionStatistic" in data:
                            for stat in data["interactionStatistic"]:
                                if isinstance(stat, dict):
                                    interaction_type = stat.get(
                                        "interactionType", {}
                                    ).get("@type", "")
                                    value = stat.get("userInteractionCount", 0)

                                    if (
                                        "followers" in interaction_type.lower()
                                        or "FollowAction" in interaction_type
                                    ):
                                        if isinstance(value, str):
                                            followers = parse_follower_count(value) or 0
                                        else:
                                            followers = int(value) if value else 0

                                    if "following" in interaction_type.lower():
                                        if isinstance(value, str):
                                            following = parse_follower_count(value) or 0
                                        else:
                                            following = int(value) if value else 0
                except (json.JSONDecodeError, Exception):
                    pass

            # Fallback: search in text content
            if followers == 0 or following == 0 or photos == 0:
                text = soup.get_text()

                # Look for "X Followers" pattern
                if followers == 0:
                    match = re.search(
                        r"([\d.]+[KMBkmb]?)\s*followers?", text, re.IGNORECASE
                    )
                    if match:
                        followers = parse_follower_count(match.group(1)) or 0

                # Look for "X Following" pattern
                if following == 0:
                    match = re.search(
                        r"([\d.]+[KMBkmb]?)\s*following", text, re.IGNORECASE
                    )
                    if match:
                        following = parse_follower_count(match.group(1)) or 0

                # Look for "X Photos" pattern
                if photos == 0:
                    match = re.search(
                        r"([\d.]+[KMBkmb]?)\s*photos?", text, re.IGNORECASE
                    )
                    if match:
                        photos = parse_follower_count(match.group(1)) or 0

                # Alternative: look for photostream count
                if photos == 0:
                    match = re.search(r"photostream[:\s]+([\d,]+)", text, re.IGNORECASE)
                    if match:
                        photos = int(match.group(1).replace(",", ""))

            # Extract metadata
            bio_text = ""
            profile_image_url = ""

            # Try to extract metadata from meta tags or page content
            meta_tags = soup.find_all("meta")
            for tag in meta_tags:
                name = tag.get("name", "") or tag.get("property", "")
                content = tag.get("content", "")

                if "description" in name.lower() and content:
                    bio_text = content

                if "image" in name.lower() and content:
                    profile_image_url = content

            # If we still don't have data
            if followers == 0 and following == 0 and photos == 0:
                logger.warning(
                    f"Could not extract data from Flickr page. Page structure may have changed."
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
                    "account_type": "personal",
                }

            return {
                "followers_count": followers,
                "following_count": following,
                "posts_count": photos,  # Flickr uses photos instead of posts
                "likes_count": 0,  # Would need to fetch individual photos
                "comments_count": 0,  # Would need to fetch individual photos
                "shares_count": 0,
                "bio_text": bio_text,
                "verified_status": None,
                "profile_image_url": profile_image_url,
                "account_created_date": None,  # Flickr doesn't expose this publicly
                "account_category": None,
                "account_type": "personal",
            }

        except AccountNotFoundError:
            raise
        except PrivateAccountError:
            raise
        except Exception as e:
            raise ScraperError(f"Error scraping Flickr account: {e}")
