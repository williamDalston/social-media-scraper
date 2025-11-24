"""
Data validation utilities for scraped data.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Reasonable maximums for validation (to catch obvious errors)
MAX_FOLLOWERS = 10_000_000_000  # 10 billion
MAX_FOLLOWING = 10_000_000  # 10 million
MAX_POSTS = 1_000_000_000  # 1 billion
MAX_ENGAGEMENT = 1_000_000_000  # 1 billion per metric


def validate_scraped_data(data: Dict[str, Any], platform: str) -> Dict[str, Any]:
    """
    Validate and sanitize scraped data.

    Args:
        data: Raw scraped data dictionary
        platform: Platform name for context

    Returns:
        Validated and sanitized data dictionary
    """
    if not data:
        return {}

    validated = {}

    # Validate followers/subscribers
    followers = data.get("followers_count", 0) or data.get("subscribers_count", 0)
    if isinstance(followers, (int, float)) and 0 <= followers <= MAX_FOLLOWERS:
        validated["followers_count"] = int(followers)
        if "subscribers_count" in data:
            validated["subscribers_count"] = int(data["subscribers_count"])
    else:
        logger.warning(f"Invalid followers count for {platform}: {followers}")
        validated["followers_count"] = 0

    # Validate following
    following = data.get("following_count", 0)
    if isinstance(following, (int, float)) and 0 <= following <= MAX_FOLLOWING:
        validated["following_count"] = int(following)
    else:
        logger.warning(f"Invalid following count for {platform}: {following}")
        validated["following_count"] = 0

    # Validate posts
    posts = data.get("posts_count", 0)
    if isinstance(posts, (int, float)) and 0 <= posts <= MAX_POSTS:
        validated["posts_count"] = int(posts)
    else:
        logger.warning(f"Invalid posts count for {platform}: {posts}")
        validated["posts_count"] = 0

    # Validate engagement metrics
    for metric in ["likes_count", "comments_count", "shares_count", "views_count"]:
        value = data.get(metric, 0)
        if isinstance(value, (int, float)) and 0 <= value <= MAX_ENGAGEMENT:
            validated[metric] = int(value)
        else:
            validated[metric] = 0

    # Ensure subscribers_count is set for YouTube
    if platform == "youtube" and "subscribers_count" not in validated:
        validated["subscribers_count"] = validated.get("followers_count", 0)

    # Ensure views_count is set if provided
    if "views_count" in data:
        validated["views_count"] = validated.get("views_count", 0)

    return validated
