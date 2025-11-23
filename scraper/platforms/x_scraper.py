"""
X (Twitter) scraper using web scraping.
"""

import re
import logging
import requests
from typing import Dict, Any, Optional

from .base_platform import BasePlatformScraper
from ..utils.errors import AccountNotFoundError, ScraperError, PrivateAccountError
from ..utils.parsers import parse_follower_count

logger = logging.getLogger(__name__)


class XScraper(BasePlatformScraper):
    """Scraper for X (Twitter) accounts."""
    
    def __init__(self):
        super().__init__('x')
    
    def _extract_handle_from_url(self, url: str) -> Optional[str]:
        """
        Extract handle from X/Twitter URL.
        
        Handles:
        - https://twitter.com/username
        - https://x.com/username
        - @username
        """
        # Remove @ if present
        url = url.replace('@', '')
        
        # Extract from URL
        match = re.search(r'(?:twitter\.com|x\.com)/([a-zA-Z0-9_]+)', url)
        if match:
            return match.group(1)
        
        # If it's just a handle
        match = re.search(r'^([a-zA-Z0-9_]+)$', url)
        if match:
            return match.group(1)
        
        return None
    
    def _normalize_url(self, account_url: str, handle: Optional[str] = None) -> str:
        """
        Normalize X/Twitter URL.
        
        Args:
            account_url: Original URL
            handle: Handle if available
            
        Returns:
            Normalized URL
        """
        if handle:
            return f"https://x.com/{handle}"
        
        handle = self._extract_handle_from_url(account_url)
        if handle:
            return f"https://x.com/{handle}"
        
        return account_url
    
    def scrape_account(self, account_url: str, handle: Optional[str] = None) -> Dict[str, Any]:
        """
        Scrape X (Twitter) account data via web scraping.
        
        Args:
            account_url: X/Twitter account URL
            handle: Account handle (optional)
            
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
                raise AccountNotFoundError(f"X account not found: {normalized_url}")
            
            if response.status_code == 403:
                raise PrivateAccountError(f"X account is private or blocked: {normalized_url}")
            
            if response.status_code != 200:
                raise ScraperError(f"Failed to fetch X page: {response.status_code}")
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # X/Twitter uses dynamic content, so we need to look for data in various places
            followers = 0
            following = 0
            posts = 0
            likes = 0
            
            # Try to find data in meta tags
            meta_tags = soup.find_all('meta')
            for tag in meta_tags:
                name = tag.get('name', '') or tag.get('property', '')
                content = tag.get('content', '')
                
                if 'followers' in name.lower() and content:
                    parsed = parse_follower_count(content)
                    if parsed:
                        followers = parsed
                
                if 'following' in name.lower() and content:
                    parsed = parse_follower_count(content)
                    if parsed:
                        following = parsed
                
                if 'tweets' in name.lower() or 'posts' in name.lower():
                    if content:
                        parsed = parse_follower_count(content)
                        if parsed:
                            posts = parsed
            
            # Look for data in script tags (X embeds data in JSON)
            scripts = soup.find_all('script', type='application/json')
            for script in scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    
                    # Recursively search for follower/following counts
                    def find_counts(obj, path=""):
                        nonlocal followers, following, posts
                        
                        if isinstance(obj, dict):
                            for key, value in obj.items():
                                key_lower = key.lower()
                                if 'follower' in key_lower and isinstance(value, (int, str)):
                                    if isinstance(value, str):
                                        parsed = parse_follower_count(value)
                                        if parsed and followers == 0:
                                            followers = parsed
                                    elif isinstance(value, int) and followers == 0:
                                        followers = value
                                
                                if 'following' in key_lower and isinstance(value, (int, str)):
                                    if isinstance(value, str):
                                        parsed = parse_follower_count(value)
                                        if parsed and following == 0:
                                            following = parsed
                                    elif isinstance(value, int) and following == 0:
                                        following = value
                                
                                if ('tweet' in key_lower or 'post' in key_lower) and 'count' in key_lower:
                                    if isinstance(value, (int, str)):
                                        if isinstance(value, str):
                                            parsed = parse_follower_count(value)
                                            if parsed and posts == 0:
                                                posts = parsed
                                        elif isinstance(value, int) and posts == 0:
                                            posts = value
                                
                                find_counts(value, f"{path}.{key}")
                        elif isinstance(obj, list):
                            for item in obj:
                                find_counts(item, path)
                    
                    find_counts(data)
                    
                except (json.JSONDecodeError, Exception):
                    pass
            
            # Fallback: search in text content
            if followers == 0 or following == 0:
                text = soup.get_text()
                
                # Look for "X Followers" pattern
                if followers == 0:
                    match = re.search(r'([\d.]+[KMBkmb]?)\s*followers?', text, re.IGNORECASE)
                    if match:
                        followers = parse_follower_count(match.group(1)) or 0
                
                # Look for "X Following" pattern
                if following == 0:
                    match = re.search(r'([\d.]+[KMBkmb]?)\s*following', text, re.IGNORECASE)
                    if match:
                        following = parse_follower_count(match.group(1)) or 0
                
                # Look for "X Posts" or "X Tweets" pattern
                if posts == 0:
                    match = re.search(r'([\d.]+[KMBkmb]?)\s*(?:posts?|tweets?)', text, re.IGNORECASE)
                    if match:
                        posts = parse_follower_count(match.group(1)) or 0
            
            # If we still don't have data, X might be blocking us or the page structure changed
            if followers == 0 and following == 0 and posts == 0:
                logger.warning(f"Could not extract data from X page. Page structure may have changed or access is blocked.")
                # Return minimal data to indicate we tried
                return {
                    'followers_count': 0,
                    'following_count': 0,
                    'posts_count': 0,
                    'likes_count': 0,
                    'comments_count': 0,
                    'shares_count': 0,
                }
            
            return {
                'followers_count': followers,
                'following_count': following,
                'posts_count': posts,
                'likes_count': likes,  # Would need to fetch individual tweets
                'comments_count': 0,  # Would need to fetch individual tweets
                'shares_count': 0,  # Would need to fetch individual tweets
            }
            
        except AccountNotFoundError:
            raise
        except PrivateAccountError:
            raise
        except Exception as e:
            raise ScraperError(f"Error scraping X account: {e}")

