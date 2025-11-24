"""
Facebook scraper using Graph API and web scraping fallback.
"""

import re
import logging
import requests
from typing import Dict, Any, Optional

from .base_platform import BasePlatformScraper
from ..utils.errors import AccountNotFoundError, ScraperError, AuthenticationError
from ..config import ScraperConfig
from ..utils.parsers import parse_follower_count

logger = logging.getLogger(__name__)

# Try to import browser scraper (optional dependency)
try:
    from ..utils.browser_scraper import scrape_with_browser

    BROWSER_AVAILABLE = True
except ImportError:
    BROWSER_AVAILABLE = False
    logger.debug(
        "Browser scraper not available. Install undetected-chromedriver for better results."
    )


class FacebookScraper(BasePlatformScraper):
    """Scraper for Facebook pages."""

    GRAPH_API_BASE = "https://graph.facebook.com/v18.0"

    def __init__(self, max_sleep_seconds: Optional[float] = None):
        super().__init__("facebook", max_sleep_seconds=max_sleep_seconds)
        self.access_token = ScraperConfig.FACEBOOK_ACCESS_TOKEN

        if not self.access_token:
            logger.warning(
                "Facebook access token not found. Will use web scraping fallback."
            )

    def _extract_page_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract page ID or username from Facebook URL.

        Handles:
        - https://www.facebook.com/username
        - https://www.facebook.com/pages/PageName/123456
        - https://facebook.com/username
        """
        # Extract username or page ID
        match = re.search(r"facebook\.com/(?:pages/)?([^/?]+)", url)
        if match:
            return match.group(1)

        return None

    def _scrape_via_api(self, page_id: str) -> Dict[str, Any]:
        """
        Scrape page data using Facebook Graph API.

        Args:
            page_id: Facebook page ID or username

        Returns:
            Dictionary with page metrics
        """
        if not self.access_token:
            raise ScraperError("Facebook access token not configured")

        url = f"{self.GRAPH_API_BASE}/{page_id}"
        params = {
            "fields": "followers_count,fan_count,likes,name,posts",
            "access_token": self.access_token,
        }

        response = requests.get(
            url, params=params, timeout=self.timeout, headers=self.headers
        )

        if response.status_code == 404:
            raise AccountNotFoundError(f"Facebook page not found: {page_id}")

        if response.status_code == 401 or response.status_code == 403:
            raise AuthenticationError(
                f"Facebook API authentication failed: {response.status_code}"
            )

        if response.status_code != 200:
            error_msg = f"Facebook API error: {response.status_code}"
            try:
                error_data = response.json()
                if "error" in error_data:
                    error_msg += f" - {error_data['error'].get('message', '')}"
            except:
                pass
            raise ScraperError(error_msg)

        data = response.json()

        # Get followers (fan_count is legacy, followers_count is new)
        followers = data.get("followers_count") or data.get("fan_count", 0)

        # Get post count (would need separate API call for recent posts)
        posts = 0  # Graph API doesn't return total post count directly

        # Get metadata from snippet
        snippet = data.get("snippet", {}) or {}

        return {
            "followers_count": int(followers),
            "following_count": 0,  # Pages don't have following
            "posts_count": posts,
            "likes_count": 0,  # Would need to fetch posts
            "comments_count": 0,  # Would need to fetch posts
            "shares_count": 0,  # Would need to fetch posts
            "bio_text": data.get("about", "") or data.get("description", ""),
            "verified_status": "verified" if data.get("is_verified") else None,
            "account_category": data.get("category", ""),
            "profile_image_url": data.get("picture", {}).get("data", {}).get("url", "")
            if isinstance(data.get("picture"), dict)
            else "",
            "account_created_date": None,  # Graph API doesn't provide this
            "account_type": "page",
        }

    def _scrape_via_web(self, account_url: str) -> Dict[str, Any]:
        """
        Scrape page data via web scraping (fallback when API is unavailable).

        Args:
            account_url: Facebook page URL

        Returns:
            Dictionary with page metrics
        """
        proxy = self._get_proxy()

        try:
            response = requests.get(
                account_url,
                headers=self.headers,
                timeout=self.timeout,
                proxies=proxy,
                allow_redirects=True,
            )

            if response.status_code == 404:
                raise AccountNotFoundError(f"Facebook page not found: {account_url}")

            if response.status_code != 200:
                raise ScraperError(
                    f"Failed to fetch Facebook page: {response.status_code}"
                )

            from bs4 import BeautifulSoup

            soup = BeautifulSoup(response.text, "html.parser")

            followers = 0
            likes = 0

            # Facebook embeds data in various places
            # Look in meta tags
            meta_tags = soup.find_all("meta")
            for tag in meta_tags:
                name = tag.get("name", "") or tag.get("property", "")
                content = tag.get("content", "")

                if "followers" in name.lower() and content:
                    parsed = parse_follower_count(content)
                    if parsed:
                        followers = parsed

                if "likes" in name.lower() and content:
                    parsed = parse_follower_count(content)
                    if parsed:
                        likes = parsed

            # Look in script tags
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
                except (json.JSONDecodeError, Exception):
                    pass

            # Fallback: search in text
            if followers == 0:
                text = soup.get_text()
                match = re.search(
                    r"([\d.]+[KMBkmb]?)\s*(?:followers?|people\s+like\s+this)",
                    text,
                    re.IGNORECASE,
                )
                if match:
                    followers = parse_follower_count(match.group(1)) or 0

            # Extract metadata
            bio_text = ""
            verified_status = None
            profile_image_url = ""

            # Try to extract metadata from meta tags
            for tag in meta_tags:
                name = tag.get("name", "") or tag.get("property", "")
                content = tag.get("content", "")

                if "description" in name.lower() and content:
                    bio_text = content

                if "image" in name.lower() and content:
                    profile_image_url = content

            # If we have data, return it
            if followers > 0:
                return {
                    "followers_count": followers,
                    "following_count": 0,
                    "posts_count": 0,  # Hard to extract from web scraping
                    "likes_count": likes,
                    "comments_count": 0,
                    "shares_count": 0,
                    "bio_text": bio_text,
                    "verified_status": verified_status,
                    "profile_image_url": profile_image_url,
                    "account_created_date": None,
                    "account_category": None,
                    "account_type": "page",
                }

            # If no data from static HTML, try browser automation (dynamic content)
            if BROWSER_AVAILABLE:
                logger.info(
                    f"Static HTML returned no data for Facebook page. Trying browser automation..."
                )
                try:
                    html = scrape_with_browser(
                        account_url, wait_time=8, driver_type="selenium"
                    )
                    if html:
                        soup = BeautifulSoup(html, "html.parser")

                        # Try to extract data from rendered page
                        meta_tags = soup.find_all("meta")
                        for tag in meta_tags:
                            name = tag.get("name", "") or tag.get("property", "")
                            content = tag.get("content", "")

                            if "followers" in name.lower() and content:
                                parsed = parse_follower_count(content)
                                if parsed:
                                    followers = parsed

                            if "likes" in name.lower() and content:
                                parsed = parse_follower_count(content)
                                if parsed:
                                    likes = parsed

                        # Also try script tags with JSON-LD
                        scripts = soup.find_all("script", type="application/ld+json")
                        for script in scripts:
                            try:
                                import json

                                data = json.loads(script.string)
                                if (
                                    isinstance(data, dict)
                                    and "interactionStatistic" in data
                                ):
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
                                                    followers = (
                                                        parse_follower_count(value) or 0
                                                    )
                                                else:
                                                    followers = (
                                                        int(value) if value else 0
                                                    )
                            except (json.JSONDecodeError, Exception):
                                pass

                        if followers > 0:
                            logger.info(
                                f"Successfully extracted data using browser automation for Facebook page"
                            )
                            return {
                                "followers_count": followers,
                                "following_count": 0,
                                "posts_count": 0,
                                "likes_count": likes,
                                "comments_count": 0,
                                "shares_count": 0,
                                "bio_text": bio_text,
                                "verified_status": verified_status,
                                "profile_image_url": profile_image_url,
                                "account_created_date": None,
                                "account_category": None,
                                "account_type": "page",
                            }
                except Exception as e:
                    logger.warning(f"Browser automation failed for Facebook page: {e}")

            # Return whatever we have (may be zeros)
            return {
                "followers_count": followers,
                "following_count": 0,
                "posts_count": 0,
                "likes_count": likes,
                "comments_count": 0,
                "shares_count": 0,
                "bio_text": "",
                "verified_status": None,
                "profile_image_url": "",
                "account_created_date": None,
                "account_category": None,
                "account_type": "page",
            }

        except AccountNotFoundError:
            raise
        except Exception as e:
            raise ScraperError(f"Web scraping error: {e}")

    def scrape_account(
        self, account_url: str, handle: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Scrape Facebook page data.

        Args:
            account_url: Facebook page URL
            handle: Page username (optional)

        Returns:
            Dictionary with page metrics
        """
        page_id = self._extract_page_id_from_url(account_url)

        # Try API first if token is available
        if self.access_token and page_id:
            try:
                return self._scrape_via_api(page_id)
            except Exception as e:
                logger.warning(
                    f"API scraping failed, falling back to web scraping: {e}"
                )

        # Fallback to web scraping
        return self._scrape_via_web(account_url)
