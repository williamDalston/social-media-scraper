"""
Result validation and verification for scraped data.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ResultValidator:
    """
    Validates and verifies scraped results for accuracy and completeness.
    """
    
    def __init__(self):
        """Initialize result validator."""
        logger.info("Initialized ResultValidator")
    
    def validate_snapshot_result(
        self,
        result: Dict[str, Any],
        previous_result: Optional[Dict[str, Any]] = None,
        platform: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate a snapshot result.
        
        Args:
            result: Current snapshot result
            previous_result: Previous snapshot for comparison
            platform: Platform name for context
            
        Returns:
            Dictionary with validation results:
            {
                'is_valid': bool,
                'confidence': float (0.0 to 1.0),
                'issues': List[str],
                'warnings': List[str],
                'suggestions': List[str]
            }
        """
        issues = []
        warnings = []
        suggestions = []
        confidence = 1.0
        
        # Check required fields
        required_fields = ['followers_count', 'following_count', 'posts_count']
        missing_fields = [f for f in required_fields if result.get(f) is None]
        
        if missing_fields:
            issues.append(f"Missing required fields: {', '.join(missing_fields)}")
            confidence -= 0.3
        
        # Validate data types and ranges
        for field in required_fields:
            value = result.get(field)
            if value is not None:
                if not isinstance(value, (int, float)):
                    issues.append(f"{field} is not a number: {value}")
                    confidence -= 0.2
                elif value < 0:
                    issues.append(f"{field} is negative: {value}")
                    confidence -= 0.2
                elif value > 10_000_000_000:  # 10 billion
                    warnings.append(f"{field} seems unusually large: {value}")
                    confidence -= 0.1
        
        # Compare with previous result if available
        if previous_result:
            # Check for reasonable changes
            for field in ['followers_count', 'following_count', 'posts_count']:
                current = result.get(field, 0)
                previous = previous_result.get(field, 0)
                
                if current is None or previous is None:
                    continue
                
                if previous > 0:
                    change_pct = abs((current - previous) / previous) * 100
                    
                    # Flag large changes
                    if change_pct > 50:  # More than 50% change
                        warnings.append(
                            f"{field} changed by {change_pct:.1f}% "
                            f"({previous} -> {current})"
                        )
                        confidence -= 0.1
                    
                    # Flag impossible changes (followers can't decrease by more than 10% in one day)
                    if field == 'followers_count' and change_pct < -10:
                        issues.append(
                            f"Followers decreased by {abs(change_pct):.1f}% "
                            f"({previous} -> {current}), which is unusual"
                        )
                        confidence -= 0.2
        
        # Platform-specific validation
        if platform:
            if platform == 'youtube':
                # YouTube should have subscribers_count
                if 'subscribers_count' not in result or result.get('subscribers_count') == 0:
                    if 'followers_count' in result and result.get('followers_count') == 0:
                        warnings.append("YouTube account has no subscribers")
                        confidence -= 0.1
        
        # Ensure confidence is between 0 and 1
        confidence = max(0.0, min(1.0, confidence))
        
        # Generate suggestions
        if confidence < 0.7:
            suggestions.append("Consider re-scraping this account to verify data")
        if issues:
            suggestions.append("Review and fix data issues before storing")
        
        return {
            'is_valid': len(issues) == 0,
            'confidence': round(confidence, 3),
            'issues': issues,
            'warnings': warnings,
            'suggestions': suggestions,
        }
    
    def validate_post_result(
        self,
        result: Dict[str, Any],
        platform: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate a post result.
        
        Args:
            result: Post result dictionary
            platform: Platform name for context
            
        Returns:
            Dictionary with validation results
        """
        issues = []
        warnings = []
        confidence = 1.0
        
        # Check required fields
        if 'post_id' not in result or not result.get('post_id'):
            issues.append("Missing post_id")
            confidence -= 0.5
        
        if 'account_key' not in result:
            issues.append("Missing account_key")
            confidence -= 0.3
        
        # Validate engagement metrics
        engagement_fields = ['likes_count', 'comments_count', 'shares_count']
        for field in engagement_fields:
            value = result.get(field)
            if value is not None:
                if not isinstance(value, (int, float)) or value < 0:
                    issues.append(f"Invalid {field}: {value}")
                    confidence -= 0.1
        
        # Check timestamp
        if 'post_datetime_utc' in result:
            post_time = result['post_datetime_utc']
            if isinstance(post_time, datetime):
                # Check if post is in the future (invalid)
                if post_time > datetime.utcnow():
                    issues.append("Post timestamp is in the future")
                    confidence -= 0.3
                
                # Check if post is too old (might be stale)
                if post_time < datetime.utcnow() - timedelta(days=365):
                    warnings.append("Post is more than 1 year old")
        
        confidence = max(0.0, min(1.0, confidence))
        
        return {
            'is_valid': len(issues) == 0,
            'confidence': round(confidence, 3),
            'issues': issues,
            'warnings': warnings,
        }
    
    def verify_data_consistency(
        self,
        results: List[Dict[str, Any]],
        platform: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Verify consistency across multiple results.
        
        Args:
            results: List of result dictionaries
            platform: Platform name for context
            
        Returns:
            Dictionary with consistency check results
        """
        if len(results) < 2:
            return {
                'is_consistent': True,
                'issues': [],
            }
        
        issues = []
        
        # Check for duplicate post_ids
        post_ids = [r.get('post_id') for r in results if r.get('post_id')]
        if len(post_ids) != len(set(post_ids)):
            issues.append("Duplicate post_ids found in results")
        
        # Check for consistent account_keys
        account_keys = set(r.get('account_key') for r in results if r.get('account_key'))
        if len(account_keys) > 1:
            issues.append("Results contain multiple account_keys")
        
        return {
            'is_consistent': len(issues) == 0,
            'issues': issues,
        }


# Global validator instance
_validator: Optional[ResultValidator] = None


def get_result_validator() -> ResultValidator:
    """Get or create global result validator."""
    global _validator
    if _validator is None:
        _validator = ResultValidator()
    return _validator

