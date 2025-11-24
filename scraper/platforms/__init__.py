"""
Platform-specific scrapers for social media platforms.
"""

from .base_platform import BasePlatformScraper
from .x_scraper import XScraper
from .instagram_scraper import InstagramScraper
from .facebook_scraper import FacebookScraper
from .linkedin_scraper import LinkedInScraper
from .youtube_scraper import YouTubeScraper
from .truth_scraper import TruthScraper
from .tiktok_scraper import TikTokScraper
from .reddit_scraper import RedditScraper
from .flickr_scraper import FlickrScraper

__all__ = [
    'BasePlatformScraper',
    'XScraper',
    'InstagramScraper',
    'FacebookScraper',
    'LinkedInScraper',
    'YouTubeScraper',
    'TruthScraper',
    'TikTokScraper',
    'RedditScraper',
    'FlickrScraper',
]

