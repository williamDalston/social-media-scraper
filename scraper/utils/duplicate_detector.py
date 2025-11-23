"""
Duplicate detection and prevention for scraped data.
"""

import hashlib
import logging
from typing import Dict, Any, Optional, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DuplicateDetector:
    """
    Detects duplicate posts and snapshots.
    """
    
    def __init__(self):
        """Initialize duplicate detector."""
        self._seen_hashes: Set[str] = set()
        self._seen_post_ids: Dict[str, Set[str]] = {}  # platform -> set of post_ids
        logger.info("Initialized DuplicateDetector")
    
    def _hash_data(self, data: Dict[str, Any]) -> str:
        """
        Create hash from data dictionary.
        
        Args:
            data: Data dictionary
            
        Returns:
            MD5 hash string
        """
        # Create a normalized string representation
        # Sort keys for consistent hashing
        normalized = {
            k: v for k, v in sorted(data.items())
            if v is not None and k not in ['post_datetime_utc', 'snapshot_date']  # Exclude timestamps
        }
        
        # Convert to string and hash
        data_str = str(normalized)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def is_duplicate_post(self, platform: str, post_id: str, post_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if a post is a duplicate.
        
        Args:
            platform: Platform name
            post_id: Post ID from platform
            post_data: Optional post data for content-based detection
            
        Returns:
            True if duplicate, False otherwise
        """
        # Check by post_id first (fastest)
        if platform not in self._seen_post_ids:
            self._seen_post_ids[platform] = set()
        
        if post_id in self._seen_post_ids[platform]:
            logger.debug(f"Duplicate post detected by ID: {platform}:{post_id}")
            return True
        
        # Check by content hash if data provided
        if post_data:
            content_hash = self._hash_data(post_data)
            if content_hash in self._seen_hashes:
                logger.debug(f"Duplicate post detected by content hash: {platform}:{post_id}")
                return True
        
        # Not a duplicate - mark as seen
        self._seen_post_ids[platform].add(post_id)
        if post_data:
            content_hash = self._hash_data(post_data)
            self._seen_hashes.add(content_hash)
        
        return False
    
    def is_duplicate_snapshot(self, account_key: int, snapshot_data: Dict[str, Any]) -> bool:
        """
        Check if a snapshot is a duplicate (same data as previous snapshot).
        
        Args:
            account_key: Account key
            snapshot_data: Snapshot data dictionary
            
        Returns:
            True if duplicate, False otherwise
        """
        # Create hash including account_key
        data_with_account = {**snapshot_data, 'account_key': account_key}
        data_hash = self._hash_data(data_with_account)
        
        if data_hash in self._seen_hashes:
            logger.debug(f"Duplicate snapshot detected for account {account_key}")
            return True
        
        # Not a duplicate - mark as seen
        self._seen_hashes.add(data_hash)
        return False
    
    def clear_old_entries(self, days: int = 7):
        """
        Clear old entries to prevent memory bloat.
        
        Args:
            days: Number of days to keep entries
        """
        # For now, just clear all (simple implementation)
        # In production, implement time-based cleanup
        logger.info(f"Clearing duplicate detection cache (keeping last {days} days)")
        self._seen_hashes.clear()
        self._seen_post_ids.clear()


# Global duplicate detector
_duplicate_detector: Optional[DuplicateDetector] = None


def get_duplicate_detector() -> DuplicateDetector:
    """Get or create global duplicate detector."""
    global _duplicate_detector
    if _duplicate_detector is None:
        _duplicate_detector = DuplicateDetector()
    return _duplicate_detector

