"""
TikTok scraper using web scraping.
"""

import re
import logging
import requests
from typing import Dict, Any, Optional

from .base_platform import BasePlatformScraper
from ..utils.errors import AccountNotFoundError, ScraperError, PrivateAccountError
from ..utils.parsers import parse_follower_count

logger = logging.getLogger(__name__)


class TikTokScraper(BasePlatformScraper):
    """Scraper for TikTok accounts."""
    
    def __init__(self):
        super().__init__('tiktok')
    
    def _extract_username_from_url(self, url: str) -> Optional[str]:
        """
        Extract username from TikTok URL.
        
        Handles:
        - https://www.tiktok.com/@username
        - https://tiktok.com/@username
        - @username
        """
        # Remove @ if present
        url = url.replace('@', '')
        
        # Extract from URL
        match = re.search(r'tiktok\.com/@?([a-zA-Z0-9_.]+)', url)
        if match:
            return match.group(1)
        
        # If it's just a username
        match = re.search(r'^([a-zA-Z0-9_.]+)$', url)
        if match:
            return match.group(1)
        
        return None
    
    def _normalize_url(self, account_url: str, handle: Optional[str] = None) -> str:
        """
        Normalize TikTok URL.
        
        Args:
            account_url: Original URL
            handle: Username if available
            
        Returns:
            Normalized URL
        """
        if handle:
            return f"https://www.tiktok.com/@{handle}"
        
        username = self._extract_username_from_url(account_url)
        if username:
            return f"https://www.tiktok.com/@{username}"
        
        return account_url
    
    def scrape_account(self, account_url: str, handle: Optional[str] = None) -> Dict[str, Any]:
        """
        Scrape TikTok account data via web scraping.
        
        Args:
            account_url: TikTok account URL
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
                raise AccountNotFoundError(f"TikTok account not found: {normalized_url}")
            
            if response.status_code == 403:
                raise PrivateAccountError(f"TikTok account is private: {normalized_url}")
            
            if response.status_code != 200:
                raise ScraperError(f"Failed to fetch TikTok page: {response.status_code}")
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            followers = 0
            following = 0
            likes = 0
            videos = 0
            
            # TikTok embeds data in script tags with JSON
            scripts = soup.find_all('script', type='application/json')
            for script in scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    
                    # Recursively search for user stats
                    def find_stats(obj, path=""):
                        nonlocal followers, following, likes, videos
                        
                        if isinstance(obj, dict):
                            for key, value in obj.items():
                                key_lower = key.lower()
                                
                                # Look for follower count
                                if 'follower' in key_lower and isinstance(value, (int, str)):
                                    if isinstance(value, str):
                                        parsed = parse_follower_count(value)
                                        if parsed and followers == 0:
                                            followers = parsed
                                    elif isinstance(value, int) and followers == 0:
                                        followers = value
                                
                                # Look for following count
                                if 'following' in key_lower and isinstance(value, (int, str)):
                                    if isinstance(value, str):
                                        parsed = parse_follower_count(value)
                                        if parsed and following == 0:
                                            following = parsed
                                    elif isinstance(value, int) and following == 0:
                                        following = value
                                
                                # Look for likes (total)
                                if 'like' in key_lower and 'count' in key_lower and isinstance(value, (int, str)):
                                    if isinstance(value, str):
                                        parsed = parse_follower_count(value)
                                        if parsed and likes == 0:
                                            likes = parsed
                                    elif isinstance(value, int) and likes == 0:
                                        likes = value
                                
                                # Look for video count
                                if ('video' in key_lower or 'post' in key_lower) and 'count' in key_lower:
                                    if isinstance(value, (int, str)):
                                        if isinstance(value, str):
                                            parsed = parse_follower_count(value)
                                            if parsed and videos == 0:
                                                videos = parsed
                                        elif isinstance(value, int) and videos == 0:
                                            videos = value
                                
                                find_stats(value, f"{path}.{key}")
                        elif isinstance(obj, list):
                            for item in obj:
                                find_stats(item, path)
                    
                    find_stats(data)
                    
                except (json.JSONDecodeError, Exception) as e:
                    logger.debug(f"Error parsing TikTok JSON: {e}")
            
            # Look in meta tags
            meta_tags = soup.find_all('meta')
            for tag in meta_tags:
                name = tag.get('name', '') or tag.get('property', '')
                content = tag.get('content', '')
                
                if 'followers' in name.lower() and content:
                    parsed = parse_follower_count(content)
                    if parsed and followers == 0:
                        followers = parsed
                
                if 'following' in name.lower() and content:
                    parsed = parse_follower_count(content)
                    if parsed and following == 0:
                        following = parsed
                
                if 'likes' in name.lower() and content:
                    parsed = parse_follower_count(content)
                    if parsed and likes == 0:
                        likes = parsed
            
            # Fallback: search in text
            if followers == 0 or following == 0 or videos == 0:
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
                
                # Look for "X Videos" pattern
                if videos == 0:
                    match = re.search(r'([\d.]+[KMBkmb]?)\s*videos?', text, re.IGNORECASE)
                    if match:
                        videos = parse_follower_count(match.group(1)) or 0
            
            # If we still don't have data
            if followers == 0 and following == 0 and videos == 0:
                logger.warning(f"Could not extract data from TikTok page. Page structure may have changed or access is blocked.")
                return {
                    'followers_count': 0,
                    'following_count': 0,
                    'posts_count': 0,
                    'likes_count': 0,
                    'comments_count': 0,
                    'shares_count': 0,
                    'bio_text': '',
                    'verified_status': None,
                    'profile_image_url': '',
                    'account_created_date': None,
                    'account_category': None,
                    'account_type': 'personal',
                }
            
            # Extract metadata
            bio_text = ''
            profile_image_url = ''
            
            return {
                'followers_count': followers,
                'following_count': following,
                'posts_count': videos,
                'likes_count': likes,
                'comments_count': 0,  # Would need to fetch individual videos
                'shares_count': 0,  # Would need to fetch individual videos
                'bio_text': bio_text,
                'verified_status': None,
                'profile_image_url': profile_image_url,
                'account_created_date': None,
                'account_category': None,
                'account_type': 'personal',
            }
            
        except AccountNotFoundError:
            raise
        except PrivateAccountError:
            raise
        except Exception as e:
            raise ScraperError(f"Error scraping TikTok account: {e}")

