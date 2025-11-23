"""
Real-time data validation during scraping.
"""

import logging
from typing import Dict, Any, Optional, Callable

from .validators import get_result_validator
from .data_quality import get_quality_scorer

logger = logging.getLogger(__name__)


class RealtimeValidator:
    """
    Performs real-time validation during data collection.
    """
    
    def __init__(self):
        """Initialize real-time validator."""
        self.result_validator = get_result_validator()
        self.quality_scorer = get_quality_scorer()
        logger.info("Initialized RealtimeValidator")
    
    def validate_snapshot_realtime(
        self,
        snapshot_data: Dict[str, Any],
        previous_snapshot: Optional[Dict[str, Any]] = None,
        platform: Optional[str] = None,
        on_issue: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Validate snapshot data in real-time.
        
        Args:
            snapshot_data: Snapshot data to validate
            previous_snapshot: Previous snapshot for comparison
            platform: Platform name
            on_issue: Optional callback function for issues
            
        Returns:
            Dictionary with validation results and potentially corrected data
        """
        # Validate using result validator
        validation = self.result_validator.validate_snapshot_result(
            snapshot_data,
            previous_snapshot,
            platform
        )
        
        # Score data quality
        quality_score = self.quality_scorer.score_snapshot(snapshot_data)
        
        # Combine results
        result = {
            'is_valid': validation['is_valid'] and quality_score['score'] > 0.7,
            'validation': validation,
            'quality_score': quality_score,
            'data': snapshot_data,
        }
        
        # Call issue handler if provided
        if on_issue:
            for issue in validation.get('issues', []):
                on_issue(f"Validation issue: {issue}")
            for issue in quality_score.get('issues', []):
                on_issue(f"Quality issue: {issue}")
        
        # Log issues
        if not result['is_valid']:
            logger.warning(
                f"Real-time validation failed for platform {platform}: "
                f"{validation.get('issues', []) + quality_score.get('issues', [])}"
            )
        
        return result
    
    def validate_post_realtime(
        self,
        post_data: Dict[str, Any],
        platform: Optional[str] = None,
        on_issue: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Validate post data in real-time.
        
        Args:
            post_data: Post data to validate
            platform: Platform name
            on_issue: Optional callback function for issues
            
        Returns:
            Dictionary with validation results
        """
        # Validate using result validator
        validation = self.result_validator.validate_post_result(post_data, platform)
        
        # Score data quality
        quality_score = self.quality_scorer.score_post(post_data)
        
        # Combine results
        result = {
            'is_valid': validation['is_valid'] and quality_score['score'] > 0.7,
            'validation': validation,
            'quality_score': quality_score,
            'data': post_data,
        }
        
        # Call issue handler if provided
        if on_issue:
            for issue in validation.get('issues', []):
                on_issue(f"Validation issue: {issue}")
            for issue in quality_score.get('issues', []):
                on_issue(f"Quality issue: {issue}")
        
        return result
    
    def should_store_data(
        self,
        validation_result: Dict[str, Any],
        min_confidence: float = 0.7,
    ) -> bool:
        """
        Determine if data should be stored based on validation.
        
        Args:
            validation_result: Result from validate_snapshot_realtime or validate_post_realtime
            min_confidence: Minimum confidence threshold
            
        Returns:
            True if data should be stored, False otherwise
        """
        if not validation_result.get('is_valid', False):
            return False
        
        validation = validation_result.get('validation', {})
        quality_score = validation_result.get('quality_score', {})
        
        # Check confidence thresholds
        if validation.get('confidence', 0) < min_confidence:
            return False
        
        if quality_score.get('score', 0) < min_confidence:
            return False
        
        return True


# Global real-time validator
_realtime_validator: Optional[RealtimeValidator] = None


def get_realtime_validator() -> RealtimeValidator:
    """Get or create global real-time validator."""
    global _realtime_validator
    if _realtime_validator is None:
        _realtime_validator = RealtimeValidator()
    return _realtime_validator

