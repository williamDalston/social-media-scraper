"""
High-precision data extraction utilities.
"""

import re
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class PrecisionExtractor:
    """
    High-precision data extraction with multiple parsing strategies.
    """
    
    def __init__(self):
        """Initialize precision extractor."""
        logger.info("Initialized PrecisionExtractor")
    
    def extract_follower_count_precise(
        self,
        text: str,
        platform: Optional[str] = None,
    ) -> Optional[int]:
        """
        Extract follower count with high precision using multiple strategies.
        
        Args:
            text: Text content to extract from
            platform: Platform name for context
            
        Returns:
            Extracted follower count or None
        """
        if not text:
            return None
        
        # Strategy 1: Look for explicit "followers" pattern
        patterns = [
            r'([\d,.\s]+)\s*(?:followers?|subscribers?|members?)',
            r'(?:followers?|subscribers?|members?)[:\s]+([\d,.\s]+)',
            r'([\d,.\s]+[KMBkmb]?)\s*(?:followers?|subscribers?|members?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                from .parsers import parse_follower_count
                value = parse_follower_count(match.group(1))
                if value:
                    return value
        
        # Strategy 2: Look in structured data (JSON, meta tags)
        # This would be handled by platform-specific scrapers
        
        # Strategy 3: Look for numbers near follower-related keywords
        follower_keywords = ['follower', 'subscriber', 'member', 'fan', 'like']
        for keyword in follower_keywords:
            # Find keyword and look for numbers nearby
            keyword_pos = text.lower().find(keyword)
            if keyword_pos >= 0:
                # Look 50 characters before and after
                context = text[max(0, keyword_pos - 50):keyword_pos + 50]
                numbers = re.findall(r'[\d,.\s]+[KMBkmb]?', context)
                if numbers:
                    from .parsers import parse_follower_count
                    for num_str in numbers:
                        value = parse_follower_count(num_str)
                        if value and value > 0:
                            return value
        
        return None
    
    def extract_engagement_precise(
        self,
        text: str,
        platform: Optional[str] = None,
    ) -> Dict[str, int]:
        """
        Extract engagement metrics with high precision.
        
        Args:
            text: Text content to extract from
            platform: Platform name for context
            
        Returns:
            Dictionary with engagement metrics
        """
        result = {
            'likes': 0,
            'comments': 0,
            'shares': 0,
        }
        
        if not text:
            return result
        
        from .parsers import parse_follower_count
        
        # Platform-specific patterns
        if platform == 'x' or platform == 'twitter':
            # X/Twitter uses "likes", "replies", "retweets"
            patterns = {
                'likes': [
                    r'([\d,.\s]+[KMBkmb]?)\s*(?:likes?|❤)',
                    r'(?:likes?|❤)[:\s]+([\d,.\s]+[KMBkmb]?)',
                ],
                'comments': [
                    r'([\d,.\s]+[KMBkmb]?)\s*(?:replies?|comments?|💬)',
                    r'(?:replies?|comments?|💬)[:\s]+([\d,.\s]+[KMBkmb]?)',
                ],
                'shares': [
                    r'([\d,.\s]+[KMBkmb]?)\s*(?:retweets?|shares?|🔄)',
                    r'(?:retweets?|shares?|🔄)[:\s]+([\d,.\s]+[KMBkmb]?)',
                ],
            }
        else:
            # Generic patterns
            patterns = {
                'likes': [
                    r'([\d,.\s]+[KMBkmb]?)\s*(?:likes?|❤|👍)',
                ],
                'comments': [
                    r'([\d,.\s]+[KMBkmb]?)\s*(?:comments?|💬)',
                ],
                'shares': [
                    r'([\d,.\s]+[KMBkmb]?)\s*(?:shares?|🔄)',
                ],
            }
        
        for metric, metric_patterns in patterns.items():
            for pattern in metric_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = parse_follower_count(match.group(1))
                    if value:
                        result[metric] = value
                        break
        
        return result
    
    def extract_post_count_precise(
        self,
        text: str,
        platform: Optional[str] = None,
    ) -> Optional[int]:
        """
        Extract post count with high precision.
        
        Args:
            text: Text content to extract from
            platform: Platform name for context
            
        Returns:
            Extracted post count or None
        """
        if not text:
            return None
        
        # Platform-specific post count keywords
        if platform == 'x' or platform == 'twitter':
            keywords = ['tweets?', 'posts?']
        elif platform == 'instagram':
            keywords = ['posts?', 'photos?']
        elif platform == 'youtube':
            keywords = ['videos?']
        else:
            keywords = ['posts?', 'items?']
        
        from .parsers import parse_follower_count
        
        for keyword in keywords:
            pattern = rf'([\d,.\s]+[KMBkmb]?)\s*{keyword}'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                value = parse_follower_count(match.group(1))
                if value:
                    return value
        
        return None


# Global precision extractor
_precision_extractor: Optional[PrecisionExtractor] = None


def get_precision_extractor() -> PrecisionExtractor:
    """Get or create global precision extractor."""
    global _precision_extractor
    if _precision_extractor is None:
        _precision_extractor = PrecisionExtractor()
    return _precision_extractor

