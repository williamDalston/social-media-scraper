"""
LinkedIn scraper using web scraping.
"""

import re
import logging
import requests
from typing import Dict, Any, Optional

from .base_platform import BasePlatformScraper
from ..utils.errors import AccountNotFoundError, ScraperError, PrivateAccountError
from ..utils.parsers import parse_follower_count

logger = logging.getLogger(__name__)


class LinkedInScraper(BasePlatformScraper):
    """Scraper for LinkedIn company/showcase pages."""
    
    def __init__(self):
        super().__init__('linkedin')
    
    def _extract_identifier_from_url(self, url: str) -> Optional[str]:
        """
        Extract company/page identifier from LinkedIn URL.
        
        Handles:
        - https://www.linkedin.com/company/companyname
        - https://www.linkedin.com/showcase/showcasename
        - https://linkedin.com/company/companyname
        """
        # Extract company or showcase name
        match = re.search(r'linkedin\.com/(?:company|showcase)/([^/?]+)', url)
        if match:
            return match.group(1)
        
        return None
    
    def _normalize_url(self, account_url: str, handle: Optional[str] = None) -> str:
        """
        Normalize LinkedIn URL.
        
        Args:
            account_url: Original URL
            handle: Company/showcase name if available
            
        Returns:
            Normalized URL
        """
        if handle:
            # Try company first, then showcase
            return f"https://www.linkedin.com/company/{handle}/"
        
        identifier = self._extract_identifier_from_url(account_url)
        if identifier:
            return f"https://www.linkedin.com/company/{identifier}/"
        
        return account_url
    
    def scrape_account(self, account_url: str, handle: Optional[str] = None) -> Dict[str, Any]:
        """
        Scrape LinkedIn page data via web scraping.
        
        Args:
            account_url: LinkedIn page URL
            handle: Company/showcase name (optional)
            
        Returns:
            Dictionary with page metrics
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
                raise AccountNotFoundError(f"LinkedIn page not found: {normalized_url}")
            
            if response.status_code == 403:
                raise PrivateAccountError(f"LinkedIn page access denied: {normalized_url}")
            
            if response.status_code != 200:
                raise ScraperError(f"Failed to fetch LinkedIn page: {response.status_code}")
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            followers = 0
            
            # LinkedIn uses structured data
            # Look in meta tags
            meta_tags = soup.find_all('meta')
            for tag in meta_tags:
                name = tag.get('name', '') or tag.get('property', '')
                content = tag.get('content', '')
                
                if 'followers' in name.lower() and content:
                    parsed = parse_follower_count(content)
                    if parsed:
                        followers = parsed
            
            # Look in script tags with JSON-LD
            scripts = soup.find_all('script', type='application/ld+json')
            for script in scripts:
                try:
                    import json
                    data = json.loads(script.string)
                    
                    if isinstance(data, dict):
                        if 'interactionStatistic' in data:
                            for stat in data['interactionStatistic']:
                                if isinstance(stat, dict):
                                    interaction_type = stat.get('interactionType', {}).get('@type', '')
                                    value = stat.get('userInteractionCount', 0)
                                    
                                    if 'followers' in interaction_type.lower() or 'FollowAction' in interaction_type:
                                        if isinstance(value, str):
                                            followers = parse_follower_count(value) or 0
                                        else:
                                            followers = int(value) if value else 0
                except (json.JSONDecodeError, Exception):
                    pass
            
            # Fallback: search in text
            if followers == 0:
                text = soup.get_text()
                # Look for "X followers" pattern
                match = re.search(r'([\d.]+[KMBkmb]?)\s*followers?', text, re.IGNORECASE)
                if match:
                    followers = parse_follower_count(match.group(1)) or 0
            
            # LinkedIn is very restrictive and may block scrapers
            if followers == 0:
                logger.warning(f"Could not extract data from LinkedIn page. LinkedIn may be blocking scrapers or page structure changed.")
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
                'following_count': 0,  # LinkedIn pages don't have following
                'posts_count': 0,  # Hard to extract
                'likes_count': 0,
                'comments_count': 0,
                'shares_count': 0,
            }
            
        except AccountNotFoundError:
            raise
        except PrivateAccountError:
            raise
        except Exception as e:
            raise ScraperError(f"Error scraping LinkedIn page: {e}")

