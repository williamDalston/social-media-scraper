"""
Post content scraping utilities for extracting full post content, images, and videos.
"""

import logging
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class PostContentScraper:
    """
    Scrapes full post content including text, images, and video metadata.
    """

    def __init__(self):
        """Initialize post content scraper."""
        logger.info("Initialized PostContentScraper")

    def extract_post_content(
        self,
        html_content: str,
        platform: str,
    ) -> Dict[str, Any]:
        """
        Extract full post content from HTML.

        Args:
            html_content: HTML content of the post page
            platform: Platform name

        Returns:
            Dictionary with extracted content:
            {
                'text': str,
                'images': List[Dict],
                'videos': List[Dict],
                'links': List[str],
            }
        """
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html_content, "html.parser")

        result = {
            "text": "",
            "images": [],
            "videos": [],
            "links": [],
        }

        # Extract text content
        result["text"] = self._extract_text(soup, platform)

        # Extract images
        result["images"] = self._extract_images(soup, platform)

        # Extract videos
        result["videos"] = self._extract_videos(soup, platform)

        # Extract links
        result["links"] = self._extract_links(soup)

        return result

    def _extract_text(self, soup, platform: str) -> str:
        """Extract text content from post."""
        # Platform-specific text extraction
        if platform in ["x", "twitter"]:
            # X/Twitter post text
            text_elements = soup.find_all(
                ["p", "span"], class_=re.compile(r"text|tweet", re.I)
            )
        elif platform == "instagram":
            # Instagram caption
            text_elements = soup.find_all(
                ["span", "div"], class_=re.compile(r"caption|text", re.I)
            )
        else:
            # Generic text extraction
            text_elements = soup.find_all(
                ["p", "div", "span"], class_=re.compile(r"content|text|post", re.I)
            )

        text_parts = []
        for elem in text_elements:
            text = elem.get_text(strip=True)
            if text and len(text) > 10:  # Filter out short/noise text
                text_parts.append(text)

        return " ".join(text_parts)

    def _extract_images(self, soup, platform: str) -> List[Dict[str, Any]]:
        """Extract image metadata from post."""
        images = []

        # Find all img tags
        img_tags = soup.find_all("img")

        for img in img_tags:
            src = img.get("src") or img.get("data-src") or img.get("data-url")
            if not src:
                continue

            # Skip small icons/avatars
            width = img.get("width") or img.get("data-width")
            height = img.get("height") or img.get("data-height")

            if width and int(width) < 100:
                continue  # Likely an icon

            image_data = {
                "url": src,
                "alt": img.get("alt", ""),
                "width": int(width) if width else None,
                "height": int(height) if height else None,
            }

            images.append(image_data)

        return images

    def _extract_videos(self, soup, platform: str) -> List[Dict[str, Any]]:
        """Extract video metadata from post."""
        videos = []

        # Find video tags
        video_tags = soup.find_all("video")
        for video in video_tags:
            src = video.get("src") or video.get("data-src")
            if src:
                videos.append(
                    {
                        "url": src,
                        "type": "video",
                        "duration": video.get("duration"),
                    }
                )

        # Find iframe embeds (YouTube, etc.)
        iframes = soup.find_all("iframe")
        for iframe in iframes:
            src = iframe.get("src", "")
            if "youtube" in src or "vimeo" in src or "video" in src:
                videos.append(
                    {
                        "url": src,
                        "type": "embed",
                        "platform": "youtube" if "youtube" in src else "other",
                    }
                )

        return videos

    def _extract_links(self, soup) -> List[str]:
        """Extract links from post."""
        links = []

        a_tags = soup.find_all("a", href=True)
        for a in a_tags:
            href = a.get("href")
            if href and href.startswith("http"):
                links.append(href)

        # Remove duplicates
        return list(set(links))

    def extract_media_metadata(
        self,
        media_url: str,
        media_type: str = "image",
    ) -> Dict[str, Any]:
        """
        Extract metadata from media URL.

        Args:
            media_url: URL of the media
            media_type: Type of media ('image' or 'video')

        Returns:
            Dictionary with media metadata
        """
        import requests

        metadata = {
            "url": media_url,
            "type": media_type,
        }

        try:
            # Get headers to check content type and size
            response = requests.head(media_url, timeout=10, allow_redirects=True)

            if response.status_code == 200:
                metadata["content_type"] = response.headers.get("Content-Type", "")
                metadata["content_length"] = response.headers.get("Content-Length")

                # Extract dimensions if image
                if media_type == "image" and "image" in metadata.get(
                    "content_type", ""
                ):
                    # Could use PIL to get actual dimensions, but that requires downloading
                    # For now, just return what we have
                    pass
        except Exception as e:
            logger.debug(f"Error extracting media metadata: {e}")

        return metadata


# Global post content scraper
_post_content_scraper: Optional[PostContentScraper] = None


def get_post_content_scraper() -> PostContentScraper:
    """Get or create global post content scraper."""
    global _post_content_scraper
    if _post_content_scraper is None:
        _post_content_scraper = PostContentScraper()
    return _post_content_scraper
