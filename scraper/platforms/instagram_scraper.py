"""
Instagram scraper using web scraping.
"""

import re
import logging
import requests
from typing import Dict, Any, Optional

from .base_platform import BasePlatformScraper
from ..utils.errors import AccountNotFoundError, ScraperError, PrivateAccountError
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


class InstagramScraper(BasePlatformScraper):
    """Scraper for Instagram accounts."""

    def __init__(self, max_sleep_seconds: Optional[float] = None):
        super().__init__("instagram", max_sleep_seconds=max_sleep_seconds)

    def _extract_username_from_url(self, url: str) -> Optional[str]:
        """
        Extract username from Instagram URL.

        Handles:
        - https://www.instagram.com/username/
        - https://instagram.com/username
        - @username
        """
        # Remove @ if present
        url = url.replace("@", "")

        # Extract from URL
        match = re.search(r"instagram\.com/([a-zA-Z0-9_.]+)", url)
        if match:
            username = match.group(1).rstrip("/")
            return username

        # If it's just a username
        match = re.search(r"^([a-zA-Z0-9_.]+)$", url)
        if match:
            return match.group(1)

        return None

    def _normalize_url(self, account_url: str, handle: Optional[str] = None) -> str:
        """
        Normalize Instagram URL.

        Args:
            account_url: Original URL
            handle: Username if available

        Returns:
            Normalized URL
        """
        if handle:
            return f"https://www.instagram.com/{handle}/"

        username = self._extract_username_from_url(account_url)
        if username:
            return f"https://www.instagram.com/{username}/"

        return account_url

    def scrape_account(
        self, account_url: str, handle: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Scrape Instagram account data via web scraping.

        Args:
            account_url: Instagram account URL
            handle: Account username (optional)

        Returns:
            Dictionary with account metrics
        """
        normalized_url = self._normalize_url(account_url, handle)
        proxy = self._get_proxy()

        try:
            response = requests.get(
                normalized_url,
                headers=self.headers,
                timeout=self.timeout,
                proxies=proxy,
                allow_redirects=True,
            )

            if response.status_code == 404:
                raise AccountNotFoundError(
                    f"Instagram account not found: {normalized_url}"
                )

            if response.status_code == 403:
                raise PrivateAccountError(
                    f"Instagram account is private: {normalized_url}"
                )

            if response.status_code != 200:
                raise ScraperError(
                    f"Failed to fetch Instagram page: {response.status_code}"
                )

            from bs4 import BeautifulSoup

            soup = BeautifulSoup(response.text, "html.parser")

            followers = 0
            following = 0
            posts = 0

            # Instagram embeds data in script tags with JSON
            scripts = soup.find_all("script", type="application/ld+json")
            for script in scripts:
                try:
                    import json

                    data = json.loads(script.string)

                    # Look for interactionStatistic
                    if isinstance(data, dict):
                        if "mainEntity" in data:
                            entity = data["mainEntity"]
                            if (
                                isinstance(entity, dict)
                                and "interactionStatistic" in entity
                            ):
                                for stat in entity["interactionStatistic"]:
                                    if isinstance(stat, dict):
                                        interaction_type = stat.get(
                                            "interactionType", {}
                                        ).get("@type", "")
                                        value = stat.get("userInteractionCount", 0)

                                        if (
                                            "FollowAction" in interaction_type
                                            or "followers" in interaction_type.lower()
                                        ):
                                            if isinstance(value, str):
                                                followers = (
                                                    parse_follower_count(value) or 0
                                                )
                                            else:
                                                followers = int(value) if value else 0

                                        if "following" in interaction_type.lower():
                                            if isinstance(value, str):
                                                following = (
                                                    parse_follower_count(value) or 0
                                                )
                                            else:
                                                following = int(value) if value else 0
                except (json.JSONDecodeError, Exception) as e:
                    logger.debug(f"Error parsing JSON-LD: {e}")

            # Also look in window._sharedData (Instagram's embedded data)
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string and "window._sharedData" in script.string:
                    try:
                        # Extract JSON from window._sharedData = {...}
                        match = re.search(
                            r"window\._sharedData\s*=\s*({.+?});",
                            script.string,
                            re.DOTALL,
                        )
                        if match:
                            import json

                            data = json.loads(match.group(1))

                            # Navigate to profile data
                            if (
                                "entry_data" in data
                                and "ProfilePage" in data["entry_data"]
                            ):
                                profile = data["entry_data"]["ProfilePage"][0]
                                if (
                                    "graphql" in profile
                                    and "user" in profile["graphql"]
                                ):
                                    user = profile["graphql"]["user"]

                                    followers = user.get("edge_followed_by", {}).get(
                                        "count", 0
                                    )
                                    following = user.get("edge_follow", {}).get(
                                        "count", 0
                                    )
                                    posts = user.get(
                                        "edge_owner_to_timeline_media", {}
                                    ).get("count", 0)
                    except (json.JSONDecodeError, Exception) as e:
                        logger.debug(f"Error parsing _sharedData: {e}")

            # Fallback: search in meta tags
            if followers == 0 or following == 0:
                meta_tags = soup.find_all("meta")
                for tag in meta_tags:
                    name = tag.get("name", "") or tag.get("property", "")
                    content = tag.get("content", "")

                    if "followers" in name.lower() and content:
                        parsed = parse_follower_count(content)
                        if parsed and followers == 0:
                            followers = parsed

                    if "following" in name.lower() and content:
                        parsed = parse_follower_count(content)
                        if parsed and following == 0:
                            following = parsed

                    if "posts" in name.lower() and content:
                        parsed = parse_follower_count(content)
                        if parsed and posts == 0:
                            posts = parsed

            # Final fallback: search in text
            if followers == 0 or following == 0 or posts == 0:
                text = soup.get_text()

                # Look for "X followers" pattern
                if followers == 0:
                    match = re.search(
                        r"([\d.]+[KMBkmb]?)\s*followers?", text, re.IGNORECASE
                    )
                    if match:
                        followers = parse_follower_count(match.group(1)) or 0

                # Look for "X following" pattern
                if following == 0:
                    match = re.search(
                        r"([\d.]+[KMBkmb]?)\s*following", text, re.IGNORECASE
                    )
                    if match:
                        following = parse_follower_count(match.group(1)) or 0

                # Look for "X posts" pattern
                if posts == 0:
                    match = re.search(
                        r"([\d.]+[KMBkmb]?)\s*posts?", text, re.IGNORECASE
                    )
                    if match:
                        posts = parse_follower_count(match.group(1)) or 0

            # Extract metadata
            bio_text = ""
            bio_link = ""
            profile_image_url = ""
            account_type = None
            verified_status = None

            # Extract from window._sharedData if available
            scripts = soup.find_all("script")
            for script in scripts:
                if script.string and "window._sharedData" in script.string:
                    try:
                        match = re.search(
                            r"window\._sharedData\s*=\s*({.+?});",
                            script.string,
                            re.DOTALL,
                        )
                        if match:
                            import json

                            data = json.loads(match.group(1))

                            if (
                                "entry_data" in data
                                and "ProfilePage" in data["entry_data"]
                            ):
                                profile = data["entry_data"]["ProfilePage"][0]
                                if (
                                    "graphql" in profile
                                    and "user" in profile["graphql"]
                                ):
                                    user = profile["graphql"]["user"]

                                    bio_text = user.get("biography", "")
                                    bio_link = user.get("external_url", "")
                                    profile_image_url = user.get(
                                        "profile_pic_url_hd", ""
                                    ) or user.get("profile_pic_url", "")
                                    account_type = (
                                        "business"
                                        if user.get("is_business_account")
                                        else "personal"
                                    )
                                    verified_status = (
                                        "verified" if user.get("is_verified") else None
                                    )
                                    break
                    except (json.JSONDecodeError, Exception) as e:
                        logger.debug(f"Error parsing _sharedData for metadata: {e}")

            # If we have some data, return it
            if followers > 0 or following > 0 or posts > 0:
                return {
                    "followers_count": followers,
                    "following_count": following,
                    "posts_count": posts,
                    "likes_count": 0,  # Would need to fetch individual posts
                    "comments_count": 0,  # Would need to fetch individual posts
                    "shares_count": 0,
                    "bio_text": bio_text,
                    "bio_link": bio_link,
                    "profile_image_url": profile_image_url,
                    "account_type": account_type,
                    "verified_status": verified_status,
                    "account_created_date": None,  # Instagram doesn't expose this publicly
                    "account_category": None,
                }

            # If no data from static HTML, try browser automation (dynamic content)
            if BROWSER_AVAILABLE:
                logger.info(
                    f"Static HTML returned no data for Instagram account. Trying browser automation..."
                )
                try:
                    html = scrape_with_browser(
                        normalized_url, wait_time=10, driver_type="selenium"
                    )
                    if html:
                        soup = BeautifulSoup(html, "html.parser")

                        # Look for window._sharedData in rendered page
                        scripts = soup.find_all("script")
                        for script in scripts:
                            if script.string and "window._sharedData" in script.string:
                                try:
                                    match = re.search(
                                        r"window\._sharedData\s*=\s*({.+?});",
                                        script.string,
                                        re.DOTALL,
                                    )
                                    if match:
                                        import json

                                        data = json.loads(match.group(1))

                                        if (
                                            "entry_data" in data
                                            and "ProfilePage" in data["entry_data"]
                                        ):
                                            profile = data["entry_data"]["ProfilePage"][
                                                0
                                            ]
                                            if (
                                                "graphql" in profile
                                                and "user" in profile["graphql"]
                                            ):
                                                user = profile["graphql"]["user"]
                                                followers = user.get(
                                                    "edge_followed_by", {}
                                                ).get("count", 0)
                                                following = user.get(
                                                    "edge_follow", {}
                                                ).get("count", 0)
                                                posts = user.get(
                                                    "edge_owner_to_timeline_media", {}
                                                ).get("count", 0)
                                                break
                                except (json.JSONDecodeError, Exception) as e:
                                    logger.debug(f"Error parsing _sharedData: {e}")

                        # Also try meta tags from rendered page
                        if followers == 0 or following == 0 or posts == 0:
                            meta_tags = soup.find_all("meta")
                            for tag in meta_tags:
                                name = tag.get("name", "") or tag.get("property", "")
                                content = tag.get("content", "")

                                if (
                                    "followers" in name.lower()
                                    and content
                                    and followers == 0
                                ):
                                    parsed = parse_follower_count(content)
                                    if parsed:
                                        followers = parsed

                                if (
                                    "following" in name.lower()
                                    and content
                                    and following == 0
                                ):
                                    parsed = parse_follower_count(content)
                                    if parsed:
                                        following = parsed

                                if "posts" in name.lower() and content and posts == 0:
                                    parsed = parse_follower_count(content)
                                    if parsed:
                                        posts = parsed

                        if followers > 0 or following > 0 or posts > 0:
                            logger.info(
                                f"Successfully extracted data using browser automation for Instagram account"
                            )
                            # Extract metadata from rendered page
                            bio_text = ""
                            bio_link = ""
                            profile_image_url = ""
                            account_type = None
                            verified_status = None

                            scripts = soup.find_all("script")
                            for script in scripts:
                                if (
                                    script.string
                                    and "window._sharedData" in script.string
                                ):
                                    try:
                                        match = re.search(
                                            r"window\._sharedData\s*=\s*({.+?});",
                                            script.string,
                                            re.DOTALL,
                                        )
                                        if match:
                                            import json

                                            data = json.loads(match.group(1))
                                            if (
                                                "entry_data" in data
                                                and "ProfilePage" in data["entry_data"]
                                            ):
                                                profile = data["entry_data"][
                                                    "ProfilePage"
                                                ][0]
                                                if (
                                                    "graphql" in profile
                                                    and "user" in profile["graphql"]
                                                ):
                                                    user = profile["graphql"]["user"]
                                                    bio_text = user.get("biography", "")
                                                    bio_link = user.get(
                                                        "external_url", ""
                                                    )
                                                    profile_image_url = user.get(
                                                        "profile_pic_url_hd", ""
                                                    ) or user.get("profile_pic_url", "")
                                                    account_type = (
                                                        "business"
                                                        if user.get(
                                                            "is_business_account"
                                                        )
                                                        else "personal"
                                                    )
                                                    verified_status = (
                                                        "verified"
                                                        if user.get("is_verified")
                                                        else None
                                                    )
                                                    break
                                    except (json.JSONDecodeError, Exception):
                                        pass

                            return {
                                "followers_count": followers,
                                "following_count": following,
                                "posts_count": posts,
                                "likes_count": 0,
                                "comments_count": 0,
                                "shares_count": 0,
                                "bio_text": bio_text,
                                "bio_link": bio_link,
                                "profile_image_url": profile_image_url,
                                "account_type": account_type,
                                "verified_status": verified_status,
                                "account_created_date": None,
                                "account_category": None,
                            }
                except Exception as e:
                    logger.warning(
                        f"Browser automation failed for Instagram account: {e}"
                    )

            # If still no data, return zeros
            logger.warning(
                f"Could not extract data from Instagram page. Account may be private or page structure changed."
            )
            return {
                "followers_count": 0,
                "following_count": 0,
                "posts_count": 0,
                "likes_count": 0,
                "comments_count": 0,
                "shares_count": 0,
                "bio_text": "",
                "bio_link": "",
                "profile_image_url": "",
                "verified_status": None,
                "account_created_date": None,
                "account_category": None,
            }

        except AccountNotFoundError:
            raise
        except PrivateAccountError:
            raise
        except Exception as e:
            raise ScraperError(f"Error scraping Instagram account: {e}")
