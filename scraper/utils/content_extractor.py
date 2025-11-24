"""
Content extraction utilities for posts.
Extracts hashtags, mentions, and other content elements.
"""

import re
import logging
from typing import List, Dict, Optional, Set

logger = logging.getLogger(__name__)


def extract_hashtags(text: str) -> List[str]:
    """
    Extract hashtags from text.

    Args:
        text: Text content to extract hashtags from

    Returns:
        List of unique hashtags (without # symbol)
    """
    if not text:
        return []

    # Pattern for hashtags: # followed by alphanumeric and underscore
    # Supports Unicode characters for international hashtags
    pattern = r"#([\w\u00c0-\u017f]+)"
    hashtags = re.findall(pattern, text, re.UNICODE)

    # Remove duplicates and return
    return list(set(hashtags))


def extract_mentions(text: str) -> List[str]:
    """
    Extract mentions from text.

    Args:
        text: Text content to extract mentions from

    Returns:
        List of unique mentions (without @ symbol)
    """
    if not text:
        return []

    # Pattern for mentions: @ followed by alphanumeric and underscore
    # Supports Unicode characters
    pattern = r"@([\w\u00c0-\u017f]+)"
    mentions = re.findall(pattern, text, re.UNICODE)

    # Remove duplicates and return
    return list(set(mentions))


def extract_urls(text: str) -> List[str]:
    """
    Extract URLs from text.

    Args:
        text: Text content to extract URLs from

    Returns:
        List of unique URLs
    """
    if not text:
        return []

    # Pattern for URLs (http, https, www)
    pattern = r"(https?://[^\s]+|www\.[^\s]+)"
    urls = re.findall(pattern, text)

    # Remove duplicates and return
    return list(set(urls))


def extract_emojis(text: str) -> List[str]:
    """
    Extract emojis from text.

    Args:
        text: Text content to extract emojis from

    Returns:
        List of unique emojis
    """
    if not text:
        return []

    # Pattern for emojis (Unicode emoji ranges)
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"  # dingbats
        "\U000024C2-\U0001F251"  # enclosed characters
        "]+",
        flags=re.UNICODE,
    )

    emojis = emoji_pattern.findall(text)
    return list(set(emojis))


def extract_content_elements(text: str) -> Dict[str, List[str]]:
    """
    Extract all content elements from text.

    Args:
        text: Text content to analyze

    Returns:
        Dictionary with extracted elements:
        {
            'hashtags': List[str],
            'mentions': List[str],
            'urls': List[str],
            'emojis': List[str]
        }
    """
    return {
        "hashtags": extract_hashtags(text),
        "mentions": extract_mentions(text),
        "urls": extract_urls(text),
        "emojis": extract_emojis(text),
    }


def format_hashtags_for_storage(hashtags: List[str]) -> Optional[str]:
    """
    Format hashtags list for database storage.

    Args:
        hashtags: List of hashtag strings

    Returns:
        Comma-separated string or None
    """
    if not hashtags:
        return None
    return ",".join(sorted(hashtags))


def format_mentions_for_storage(mentions: List[str]) -> Optional[str]:
    """
    Format mentions list for database storage.

    Args:
        mentions: List of mention strings

    Returns:
        Comma-separated string or None
    """
    if not mentions:
        return None
    return ",".join(sorted(mentions))


def parse_stored_hashtags(hashtags_str: Optional[str]) -> List[str]:
    """
    Parse stored hashtags string back to list.

    Args:
        hashtags_str: Comma-separated hashtags string

    Returns:
        List of hashtags
    """
    if not hashtags_str:
        return []
    return [h.strip() for h in hashtags_str.split(",") if h.strip()]


def parse_stored_mentions(mentions_str: Optional[str]) -> List[str]:
    """
    Parse stored mentions string back to list.

    Args:
        mentions_str: Comma-separated mentions string

    Returns:
        List of mentions
    """
    if not mentions_str:
        return []
    return [m.strip() for m in mentions_str.split(",") if m.strip()]
