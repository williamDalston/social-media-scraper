"""
Helper functions for parsing data from scraped content.
"""

import re
from typing import Optional


def parse_follower_count(text: str) -> Optional[int]:
    """
    Parse follower count from text in various formats.
    
    Handles formats like:
    - "1.2M" → 1,200,000
    - "500K" → 500,000
    - "1,234" → 1,234
    - "1.5B" → 1,500,000,000
    
    Args:
        text: Text containing follower count
        
    Returns:
        Parsed integer count, or None if not found
    """
    if not text:
        return None
    
    # Remove commas and whitespace
    text = text.replace(',', '').strip()
    
    # Pattern for numbers with K, M, B suffixes
    pattern = r'([\d.]+)\s*([KMBkmb]?)'
    match = re.search(pattern, text)
    
    if not match:
        # Try to find just a number
        numbers = re.findall(r'\d+', text.replace(',', ''))
        if numbers:
            try:
                return int(numbers[0])
            except ValueError:
                return None
        return None
    
    number_str = match.group(1)
    suffix = match.group(2).upper()
    
    try:
        number = float(number_str)
    except ValueError:
        return None
    
    multipliers = {
        'K': 1_000,
        'M': 1_000_000,
        'B': 1_000_000_000,
    }
    
    multiplier = multipliers.get(suffix, 1)
    return int(number * multiplier)


def parse_engagement_metrics(text: str) -> dict:
    """
    Parse engagement metrics (likes, comments, shares) from text.
    
    Args:
        text: Text containing engagement metrics
        
    Returns:
        Dictionary with likes_count, comments_count, shares_count
    """
    result = {
        'likes_count': 0,
        'comments_count': 0,
        'shares_count': 0,
    }
    
    if not text:
        return result
    
    # Common patterns for engagement metrics
    patterns = {
        'likes': [
            r'(\d+[\d,.]*[KMBkmb]?)\s*(?:likes?|❤|👍)',
            r'(?:likes?|❤|👍)\s*[:\-]?\s*(\d+[\d,.]*[KMBkmb]?)',
        ],
        'comments': [
            r'(\d+[\d,.]*[KMBkmb]?)\s*(?:comments?|💬|💭)',
            r'(?:comments?|💬|💭)\s*[:\-]?\s*(\d+[\d,.]*[KMBkmb]?)',
        ],
        'shares': [
            r'(\d+[\d,.]*[KMBkmb]?)\s*(?:shares?|retweets?|🔄|↗)',
            r'(?:shares?|retweets?|🔄|↗)\s*[:\-]?\s*(\d+[\d,.]*[KMBkmb]?)',
        ],
    }
    
    for metric, pattern_list in patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                count = parse_follower_count(match.group(1))
                if count is not None:
                    result[f'{metric}_count'] = count
                    break
    
    return result


def extract_numbers_from_text(text: str) -> list:
    """
    Extract all numbers from text, handling various formats.
    
    Args:
        text: Text to extract numbers from
        
    Returns:
        List of extracted numbers as integers
    """
    if not text:
        return []
    
    # Remove commas
    text = text.replace(',', '')
    
    # Find all numbers (including decimals)
    numbers = re.findall(r'\d+\.?\d*', text)
    
    result = []
    for num_str in numbers:
        try:
            result.append(int(float(num_str)))
        except ValueError:
            continue
    
    return result

