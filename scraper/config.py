"""
Main scraper configuration.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ScraperConfig:
    """Configuration for scrapers."""
    
    # API Keys
    TWITTER_API_KEY = os.getenv('TWITTER_API_KEY')
    TWITTER_API_SECRET = os.getenv('TWITTER_API_SECRET')
    TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
    
    FACEBOOK_ACCESS_TOKEN = os.getenv('FACEBOOK_ACCESS_TOKEN')
    FACEBOOK_APP_ID = os.getenv('FACEBOOK_APP_ID')
    FACEBOOK_APP_SECRET = os.getenv('FACEBOOK_APP_SECRET')
    
    YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
    
    INSTAGRAM_USERNAME = os.getenv('INSTAGRAM_USERNAME')
    INSTAGRAM_PASSWORD = os.getenv('INSTAGRAM_PASSWORD')
    
    # General Settings
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY = float(os.getenv('RETRY_DELAY', '1.0'))
    
    # Proxy Settings
    PROXY_LIST = os.getenv('PROXY_LIST', '')  # Comma-separated list
    USE_PROXY = os.getenv('USE_PROXY', 'false').lower() == 'true'
    
    # User Agent
    DEFAULT_USER_AGENT = os.getenv(
        'USER_AGENT',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate(cls):
        """Validate configuration and return missing required keys."""
        missing = []
        
        # YouTube API key is recommended but not strictly required (can use web scraping)
        # Other keys are optional
        
        return missing
    
    @classmethod
    def get_api_key_status(cls) -> dict:
        """Get status of API keys."""
        return {
            'twitter': bool(cls.TWITTER_API_KEY or cls.TWITTER_BEARER_TOKEN),
            'facebook': bool(cls.FACEBOOK_ACCESS_TOKEN),
            'youtube': bool(cls.YOUTUBE_API_KEY),
            'instagram': bool(cls.INSTAGRAM_USERNAME and cls.INSTAGRAM_PASSWORD),
        }

