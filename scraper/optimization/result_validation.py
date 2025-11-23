"""
Result validation and verification for scraper outputs.
Ensures data quality and accuracy.
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re

class ResultValidator:
    """Validates scraper results for quality and accuracy."""
    
    def __init__(self):
        self.validation_rules = {
            'followers_count': self._validate_followers,
            'following_count': self._validate_following,
            'posts_count': self._validate_posts,
            'likes_count': self._validate_engagement,
            'comments_count': self._validate_engagement,
            'shares_count': self._validate_engagement,
        }
    
    def validate_result(self, result: Dict, platform: str, account_handle: str) -> Tuple[bool, List[str]]:
        """
        Validate a scraper result.
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        required_fields = ['followers_count', 'following_count', 'posts_count']
        for field in required_fields:
            if field not in result:
                errors.append(f"Missing required field: {field}")
        
        # Validate each field
        for field, value in result.items():
            if field in self.validation_rules:
                is_valid, error = self.validation_rules[field](value, platform, account_handle)
                if not is_valid:
                    errors.append(f"{field}: {error}")
        
        # Platform-specific validation
        platform_errors = self._validate_platform_specific(result, platform)
        errors.extend(platform_errors)
        
        # Consistency checks
        consistency_errors = self._check_consistency(result, platform)
        errors.extend(consistency_errors)
        
        return len(errors) == 0, errors
    
    def _validate_followers(self, value: int, platform: str, handle: str) -> Tuple[bool, str]:
        """Validate followers count."""
        if not isinstance(value, int):
            return False, "Must be an integer"
        
        if value < 0:
            return False, "Cannot be negative"
        
        # Reasonable upper bounds per platform
        max_followers = {
            'X': 500_000_000,  # Elon Musk has ~150M
            'Instagram': 1_000_000_000,
            'Facebook': 10_000_000_000,
            'LinkedIn': 100_000_000,
            'YouTube': 300_000_000,
        }
        
        max_val = max_followers.get(platform, 1_000_000_000)
        if value > max_val:
            return False, f"Unreasonably high for {platform} (>{max_val:,})"
        
        return True, ""
    
    def _validate_following(self, value: int, platform: str, handle: str) -> Tuple[bool, str]:
        """Validate following count."""
        if not isinstance(value, int):
            return False, "Must be an integer"
        
        if value < 0:
            return False, "Cannot be negative"
        
        # Most accounts don't follow more than 10,000 accounts
        if value > 100_000:
            return False, "Unreasonably high following count"
        
        return True, ""
    
    def _validate_posts(self, value: int, platform: str, handle: str) -> Tuple[bool, str]:
        """Validate posts count."""
        if not isinstance(value, int):
            return False, "Must be an integer"
        
        if value < 0:
            return False, "Cannot be negative"
        
        # Daily posts should be reasonable
        if value > 100:  # More than 100 posts in a day is suspicious
            return False, "Unreasonably high daily post count"
        
        return True, ""
    
    def _validate_engagement(self, value: int, platform: str, handle: str) -> Tuple[bool, str]:
        """Validate engagement metrics."""
        if not isinstance(value, int):
            return False, "Must be an integer"
        
        if value < 0:
            return False, "Cannot be negative"
        
        # Engagement should be reasonable
        if value > 10_000_000:  # More than 10M engagements per day is very high
            return False, "Unreasonably high engagement count"
        
        return True, ""
    
    def _validate_platform_specific(self, result: Dict, platform: str) -> List[str]:
        """Platform-specific validation rules."""
        errors = []
        
        if platform == 'YouTube':
            # YouTube should have subscribers_count
            if 'subscribers_count' not in result and 'followers_count' not in result:
                errors.append("YouTube should have subscribers_count")
        
        if platform == 'X':
            # X might have listed_count
            if 'listed_count' in result:
                if not isinstance(result['listed_count'], int) or result['listed_count'] < 0:
                    errors.append("listed_count must be non-negative integer")
        
        return errors
    
    def _check_consistency(self, result: Dict, platform: str) -> List[str]:
        """Check consistency between related fields."""
        errors = []
        
        # Followers should generally be >= following
        if 'followers_count' in result and 'following_count' in result:
            if result['followers_count'] < result['following_count']:
                # This is unusual but not necessarily wrong
                pass  # Some accounts do follow more than follow them
        
        # Engagement should be reasonable relative to followers
        if 'followers_count' in result and 'engagements_total' in result:
            followers = result['followers_count']
            engagement = result['engagements_total']
            
            if followers > 0:
                engagement_rate = engagement / followers
                # Engagement rate > 100% is suspicious (more engagements than followers)
                if engagement_rate > 1.0:
                    errors.append(f"Engagement rate > 100% ({engagement_rate:.1%})")
        
        return errors
    
    def calculate_quality_score(self, result: Dict, platform: str, account_handle: str) -> float:
        """
        Calculate a quality score (0-1) for the result.
        Higher is better.
        """
        is_valid, errors = self.validate_result(result, platform, account_handle)
        
        if not is_valid:
            # Deduct points for errors
            base_score = 1.0
            deduction = len(errors) * 0.1
            return max(0.0, base_score - deduction)
        
        # Check completeness
        required_fields = ['followers_count', 'following_count', 'posts_count']
        completeness = sum(1 for field in required_fields if field in result) / len(required_fields)
        
        # Check data freshness (if timestamp available)
        freshness = 1.0  # Assume fresh if no timestamp
        
        # Overall quality score
        quality_score = (completeness * 0.6 + freshness * 0.4)
        
        return quality_score

# Global validator instance
result_validator = ResultValidator()

