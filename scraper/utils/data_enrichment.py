"""
Data enrichment utilities for adding metadata to scraped data.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import re

logger = logging.getLogger(__name__)


class DataEnricher:
    """
    Enriches scraped data with additional metadata.
    """
    
    def __init__(self):
        """Initialize data enricher."""
        logger.info("Initialized DataEnricher")
    
    def enrich_snapshot(
        self,
        snapshot_data: Dict[str, Any],
        account_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Enrich snapshot data with metadata.
        
        Args:
            snapshot_data: Snapshot data dictionary
            account_data: Optional account metadata
            
        Returns:
            Enriched snapshot data
        """
        enriched = snapshot_data.copy()
        
        # Add timestamp if not present
        if 'scraped_at' not in enriched:
            enriched['scraped_at'] = datetime.utcnow().isoformat()
        
        # Add UTC timezone info
        if 'scraped_at' in enriched and isinstance(enriched['scraped_at'], str):
            # Ensure ISO format with timezone
            if 'Z' not in enriched['scraped_at'] and '+' not in enriched['scraped_at']:
                enriched['scraped_at'] = enriched['scraped_at'] + 'Z'
        
        # Calculate derived metrics
        enriched = self._calculate_derived_metrics(enriched)
        
        # Add account metadata if available
        if account_data:
            enriched['account_handle'] = account_data.get('handle')
            enriched['account_display_name'] = account_data.get('account_display_name')
            enriched['platform'] = account_data.get('platform')
        
        return enriched
    
    def enrich_post(
        self,
        post_data: Dict[str, Any],
        account_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Enrich post data with metadata.
        
        Args:
            post_data: Post data dictionary
            account_data: Optional account metadata
            
        Returns:
            Enriched post data
        """
        enriched = post_data.copy()
        
        # Add timestamp if not present
        if 'scraped_at' not in enriched:
            enriched['scraped_at'] = datetime.utcnow().isoformat()
        
        # Ensure post_datetime_utc is in UTC
        if 'post_datetime_utc' in enriched:
            if isinstance(enriched['post_datetime_utc'], str):
                # Parse and ensure UTC
                try:
                    dt = datetime.fromisoformat(enriched['post_datetime_utc'].replace('Z', '+00:00'))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    enriched['post_datetime_utc'] = dt.isoformat()
                except Exception as e:
                    logger.warning(f"Error parsing post_datetime_utc: {e}")
        
        # Extract content elements if caption_text exists
        if 'caption_text' in enriched and enriched.get('caption_text'):
            from .content_extractor import extract_content_elements
            elements = extract_content_elements(enriched['caption_text'])
            
            # Add hashtags and mentions if not already present
            if 'hashtags' not in enriched and elements.get('hashtags'):
                from .content_extractor import format_hashtags_for_storage
                enriched['hashtags'] = format_hashtags_for_storage(elements['hashtags'])
            
            if 'mentions' not in enriched and elements.get('mentions'):
                from .content_extractor import format_mentions_for_storage
                enriched['mentions'] = format_mentions_for_storage(elements['mentions'])
        
        # Calculate engagement rate if possible
        enriched = self._calculate_engagement_metrics(enriched, account_data)
        
        # Add account metadata if available
        if account_data:
            enriched['account_handle'] = account_data.get('handle')
            enriched['platform'] = account_data.get('platform')
        
        return enriched
    
    def _calculate_derived_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate derived metrics from snapshot data.
        
        Args:
            data: Snapshot data dictionary
            
        Returns:
            Data with derived metrics added
        """
        # Calculate engagement total if not present
        if 'engagements_total' not in data:
            likes = data.get('likes_count', 0) or 0
            comments = data.get('comments_count', 0) or 0
            shares = data.get('shares_count', 0) or 0
            data['engagements_total'] = likes + comments + shares
        
        # Calculate follower growth rate (if previous data available)
        # This would need historical data, so we'll skip for now
        
        return data
    
    def _calculate_engagement_metrics(
        self,
        post_data: Dict[str, Any],
        account_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate engagement metrics for a post.
        
        Args:
            post_data: Post data dictionary
            account_data: Account data with follower count
            
        Returns:
            Post data with engagement metrics added
        """
        # Calculate engagement rate if we have followers
        if account_data and 'followers_count' in account_data:
            followers = account_data.get('followers_count') or account_data.get('subscribers_count', 0)
            
            if followers > 0:
                likes = post_data.get('likes_count', 0) or 0
                comments = post_data.get('comments_count', 0) or 0
                shares = post_data.get('shares_count', 0) or 0
                total_engagement = likes + comments + shares
                
                if total_engagement > 0:
                    engagement_rate = (total_engagement / followers) * 100
                    post_data['engagement_rate'] = round(engagement_rate, 4)
        
        return post_data
    
    def normalize_platform_data(
        self,
        data: Dict[str, Any],
        platform: str,
    ) -> Dict[str, Any]:
        """
        Normalize data across platforms.
        
        Args:
            data: Platform-specific data
            platform: Platform name
            
        Returns:
            Normalized data dictionary
        """
        normalized = data.copy()
        
        # Normalize follower/subscriber counts
        if platform == 'youtube':
            # YouTube uses subscribers_count, normalize to followers_count
            if 'subscribers_count' in normalized:
                normalized['followers_count'] = normalized.get('subscribers_count', 0)
        elif platform == 'reddit':
            # Reddit uses subscribers/members, normalize to followers_count
            if 'subscribers_count' in normalized:
                normalized['followers_count'] = normalized.get('subscribers_count', 0)
        
        # Normalize post types
        if 'post_type' in normalized:
            post_type = normalized['post_type']
            # Standardize post type names
            type_mapping = {
                'tweet': 'text',
                'truth': 'text',
                'reel': 'video',
                'story': 'image',
            }
            normalized['post_type'] = type_mapping.get(post_type.lower(), post_type)
        
        # Normalize engagement metric names
        # All platforms should use: likes_count, comments_count, shares_count
        metric_mapping = {
            'retweets': 'shares_count',
            'reposts': 'shares_count',
            'upvotes': 'likes_count',
            'downvotes': 'likes_count',  # Could be negative, but normalize for now
        }
        
        for old_key, new_key in metric_mapping.items():
            if old_key in normalized and new_key not in normalized:
                normalized[new_key] = normalized.pop(old_key)
        
        return normalized


# Global enricher instance
_enricher: Optional[DataEnricher] = None


def get_data_enricher() -> DataEnricher:
    """Get or create global data enricher."""
    global _enricher
    if _enricher is None:
        _enricher = DataEnricher()
    return _enricher

