"""
YouTube scraper using YouTube Data API v3.
"""

import re
import logging
import requests
from typing import Dict, Any, Optional

from .base_platform import BasePlatformScraper
from ..utils.errors import AccountNotFoundError, ScraperError
from ..config import ScraperConfig
from ..utils.parsers import parse_follower_count

logger = logging.getLogger(__name__)


class YouTubeScraper(BasePlatformScraper):
    """Scraper for YouTube channels."""

    API_BASE_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self):
        super().__init__("youtube")
        self.api_key = ScraperConfig.YOUTUBE_API_KEY

        if not self.api_key:
            logger.warning(
                "YouTube API key not found. Will attempt web scraping fallback."
            )

    def _extract_channel_id_from_url(self, url: str) -> Optional[str]:
        """
        Extract channel ID from various YouTube URL formats.

        Handles:
        - https://www.youtube.com/@handle
        - https://www.youtube.com/c/channelname
        - https://www.youtube.com/user/username
        - https://www.youtube.com/channel/UCxxxxx
        """
        # Channel ID format
        match = re.search(r"/channel/([a-zA-Z0-9_-]+)", url)
        if match:
            return match.group(1)

        # @handle format
        match = re.search(r"/@([a-zA-Z0-9_-]+)", url)
        if match:
            return match.group(1)

        # /c/ or /user/ format
        match = re.search(r"/(?:c|user)/([a-zA-Z0-9_-]+)", url)
        if match:
            return match.group(1)

        return None

    def _get_channel_id_via_api(self, identifier: str) -> Optional[str]:
        """
        Get channel ID from handle/username using API.

        Note: forUsername is deprecated. For @handles, we use the search API.

        Args:
            identifier: Channel handle (with or without @), username, or channel ID

        Returns:
            Channel ID or None
        """
        if not self.api_key:
            return None

        try:
            # Remove @ if present
            identifier = identifier.lstrip("@")

            # If it looks like a channel ID (starts with UC), try directly
            if identifier.startswith("UC") and len(identifier) == 24:
                url = f"{self.API_BASE_URL}/channels"
                params = {
                    "part": "id",
                    "id": identifier,
                    "key": self.api_key,
                }

                response = requests.get(url, params=params, timeout=self.timeout)

                if response.status_code == 200:
                    data = response.json()
                    if data.get("items"):
                        return data["items"][0]["id"]

            # For @handles, use search API (forUsername is deprecated)
            # Search for channels with this handle
            url = f"{self.API_BASE_URL}/search"
            params = {
                "part": "snippet",
                "q": identifier,
                "type": "channel",
                "maxResults": 1,
                "key": self.api_key,
            }

            response = requests.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                if data.get("items"):
                    # Get the channel ID from the search result
                    channel_id = data["items"][0]["id"].get("channelId")
                    if channel_id:
                        return channel_id

            # Fallback: try as channel ID directly
            url = f"{self.API_BASE_URL}/channels"
            params = {
                "part": "id",
                "id": identifier,
                "key": self.api_key,
            }

            response = requests.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                data = response.json()
                if data.get("items"):
                    return data["items"][0]["id"]

            return None

        except Exception as e:
            logger.error(f"Error getting channel ID: {e}")
            return None

    def _scrape_via_api(self, channel_id: str) -> Dict[str, Any]:
        """
        Scrape channel data using YouTube Data API v3.

        Args:
            channel_id: YouTube channel ID

        Returns:
            Dictionary with channel metrics
        """
        if not self.api_key:
            raise ScraperError("YouTube API key not configured")

        url = f"{self.API_BASE_URL}/channels"
        params = {
            "part": "statistics,snippet",
            "id": channel_id,
            "key": self.api_key,
        }

        response = requests.get(
            url, params=params, timeout=self.timeout, headers=self.headers
        )

        if response.status_code == 404:
            raise AccountNotFoundError(f"YouTube channel not found: {channel_id}")

        if response.status_code != 200:
            error_msg = f"YouTube API error: {response.status_code}"
            if response.status_code == 403:
                error_msg += " (API key may be invalid or quota exceeded)"
            raise ScraperError(error_msg)

        data = response.json()

        if not data.get("items"):
            raise AccountNotFoundError(f"YouTube channel not found: {channel_id}")

        channel = data["items"][0]
        stats = channel.get("statistics", {})

        video_count = int(stats.get("videoCount", 0))
        view_count = int(stats.get("viewCount", 0))

        # Get channel snippet for metadata
        snippet = channel.get("snippet", {})

        return {
            "followers_count": 0,  # YouTube doesn't have followers
            "following_count": 0,
            "subscribers_count": int(stats.get("subscriberCount", 0)),
            "posts_count": video_count,  # Use video_count for posts_count
            "videos_count": video_count,
            "likes_count": 0,  # Would need to fetch videos for this
            "comments_count": 0,  # Would need to fetch videos for this
            "shares_count": 0,
            "views_count": view_count,  # Current view count (deprecated, use total_video_views)
            "total_video_views": view_count,  # Lifetime video views
            # Metadata
            "bio_text": snippet.get("description", ""),
            "account_created_date": None,  # YouTube API doesn't provide this
            "verified_status": "verified"
            if channel.get("brandingSettings", {})
            .get("channel", {})
            .get("isBrandedChannel")
            else None,
            "account_category": snippet.get("categoryId", ""),
            "profile_image_url": snippet.get("thumbnails", {})
            .get("high", {})
            .get("url", ""),
        }

    def _scrape_via_web(self, account_url: str) -> Dict[str, Any]:
        """
        Scrape channel data via web scraping (fallback when API is unavailable).

        Args:
            account_url: YouTube channel URL

        Returns:
            Dictionary with channel metrics
        """
        proxy = self._get_proxy()

        try:
            response = requests.get(
                account_url,
                headers=self.headers,
                timeout=self.timeout,
                proxies=proxy,
            )

            if response.status_code == 404:
                raise AccountNotFoundError(f"YouTube channel not found: {account_url}")

            if response.status_code != 200:
                raise ScraperError(
                    f"Failed to fetch YouTube page: {response.status_code}"
                )

            from bs4 import BeautifulSoup

            soup = BeautifulSoup(response.text, "html.parser")

            # Try to find subscriber count in various places
            subscribers = 0
            views = 0
            videos = 0

            # Look for subscriber count in meta tags or script tags
            meta_tags = soup.find_all(
                "meta", {"property": re.compile(r"subscriber|subscriberCount", re.I)}
            )
            for tag in meta_tags:
                content = tag.get("content", "")
                if content:
                    parsed = parse_follower_count(content)
                    if parsed:
                        subscribers = parsed
                        break

            # Look in script tags (YouTube embeds data in JSON-LD or inline scripts)
            scripts = soup.find_all("script", type="application/ld+json")
            for script in scripts:
                try:
                    import json

                    data = json.loads(script.string)
                    if isinstance(data, dict):
                        # Look for subscriber count
                        if "subscriberCount" in data:
                            subscribers = int(data["subscriberCount"])
                        if "videoCount" in data:
                            videos = int(data["videoCount"])
                except:
                    pass

            # Fallback: search for numbers in text
            if subscribers == 0:
                text = soup.get_text()
                # Look for patterns like "1.2M subscribers"
                match = re.search(
                    r"([\d.]+[KMBkmb]?)\s*subscribers?", text, re.IGNORECASE
                )
                if match:
                    subscribers = parse_follower_count(match.group(1)) or 0

            return {
                "followers_count": 0,
                "following_count": 0,
                "subscribers_count": subscribers,
                "posts_count": videos,
                "likes_count": 0,
                "comments_count": 0,
                "shares_count": 0,
                "views_count": views,
            }

        except AccountNotFoundError:
            raise
        except Exception as e:
            raise ScraperError(f"Web scraping error: {e}")

    def scrape_account(
        self, account_url: str, handle: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Scrape YouTube channel data.

        Args:
            account_url: YouTube channel URL
            handle: Channel handle (optional)

        Returns:
            Dictionary with channel metrics
        """
        # Extract channel identifier
        channel_id = self._extract_channel_id_from_url(account_url)

        # Try API first if key is available
        if self.api_key and channel_id:
            try:
                # If channel_id looks like a handle, try to get actual ID
                if not channel_id.startswith("UC"):
                    actual_id = self._get_channel_id_via_api(channel_id)
                    if actual_id:
                        channel_id = actual_id

                if channel_id:
                    return self._scrape_via_api(channel_id)
            except Exception as e:
                logger.warning(
                    f"API scraping failed, falling back to web scraping: {e}"
                )

        # Fallback to web scraping
        return self._scrape_via_web(account_url)
