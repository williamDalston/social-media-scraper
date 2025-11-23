"""
Comprehensive metrics calculation for social media data.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from statistics import mean, median

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """
    Calculates comprehensive metrics from social media data.
    """
    
    def __init__(self):
        """Initialize metrics calculator."""
        logger.info("Initialized MetricsCalculator")
    
    def calculate_account_metrics(
        self,
        current_snapshot: Dict[str, Any],
        previous_snapshots: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive metrics for an account.
        
        Args:
            current_snapshot: Current snapshot data
            previous_snapshots: List of previous snapshots for trend analysis
            
        Returns:
            Dictionary with calculated metrics
        """
        metrics = {}
        
        # Basic metrics
        metrics['followers'] = current_snapshot.get('followers_count', 0)
        metrics['following'] = current_snapshot.get('following_count', 0)
        metrics['posts'] = current_snapshot.get('posts_count', 0)
        
        # Engagement metrics
        likes = current_snapshot.get('likes_count', 0) or 0
        comments = current_snapshot.get('comments_count', 0) or 0
        shares = current_snapshot.get('shares_count', 0) or 0
        metrics['total_engagement'] = likes + comments + shares
        
        # Engagement rate
        if metrics['followers'] > 0:
            metrics['engagement_rate'] = round(
                (metrics['total_engagement'] / metrics['followers']) * 100,
                4
            )
        else:
            metrics['engagement_rate'] = 0.0
        
        # Calculate growth metrics if previous snapshots available
        if previous_snapshots and len(previous_snapshots) > 0:
            metrics.update(self._calculate_growth_metrics(
                current_snapshot,
                previous_snapshots
            ))
        
        return metrics
    
    def _calculate_growth_metrics(
        self,
        current: Dict[str, Any],
        previous: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Calculate growth metrics from historical data.
        
        Args:
            current: Current snapshot
            previous: List of previous snapshots (most recent first)
            
        Returns:
            Dictionary with growth metrics
        """
        growth = {}
        
        if not previous:
            return growth
        
        # Compare with most recent previous snapshot
        latest_previous = previous[0]
        
        current_followers = current.get('followers_count', 0) or 0
        previous_followers = latest_previous.get('followers_count', 0) or 0
        
        if previous_followers > 0:
            follower_change = current_followers - previous_followers
            follower_growth_rate = (follower_change / previous_followers) * 100
            
            growth['follower_change'] = follower_change
            growth['follower_growth_rate'] = round(follower_growth_rate, 2)
            growth['follower_growth_direction'] = 'up' if follower_change > 0 else 'down'
        else:
            growth['follower_change'] = 0
            growth['follower_growth_rate'] = 0.0
            growth['follower_growth_direction'] = 'neutral'
        
        # Calculate average growth over time period
        if len(previous) >= 2:
            oldest = previous[-1]
            oldest_followers = oldest.get('followers_count', 0) or 0
            
            if oldest_followers > 0 and len(previous) > 1:
                total_growth = current_followers - oldest_followers
                growth['total_growth'] = total_growth
                growth['average_daily_growth'] = round(
                    total_growth / len(previous),
                    2
                )
        
        return growth
    
    def calculate_engagement_metrics(
        self,
        posts: List[Dict[str, Any]],
        account_followers: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Calculate engagement metrics from posts.
        
        Args:
            posts: List of post data dictionaries
            account_followers: Account follower count for engagement rate
            
        Returns:
            Dictionary with engagement metrics
        """
        if not posts:
            return {
                'total_posts': 0,
                'total_engagement': 0,
                'average_engagement': 0.0,
            }
        
        total_likes = sum(p.get('likes_count', 0) or 0 for p in posts)
        total_comments = sum(p.get('comments_count', 0) or 0 for p in posts)
        total_shares = sum(p.get('shares_count', 0) or 0 for p in posts)
        total_engagement = total_likes + total_comments + total_shares
        
        metrics = {
            'total_posts': len(posts),
            'total_likes': total_likes,
            'total_comments': total_comments,
            'total_shares': total_shares,
            'total_engagement': total_engagement,
            'average_likes': round(total_likes / len(posts), 2),
            'average_comments': round(total_comments / len(posts), 2),
            'average_shares': round(total_shares / len(posts), 2),
            'average_engagement': round(total_engagement / len(posts), 2),
        }
        
        # Engagement rate if followers available
        if account_followers and account_followers > 0:
            metrics['engagement_rate'] = round(
                (total_engagement / (len(posts) * account_followers)) * 100,
                4
            )
        
        # Calculate percentiles
        engagement_values = [
            (p.get('likes_count', 0) or 0) +
            (p.get('comments_count', 0) or 0) +
            (p.get('shares_count', 0) or 0)
            for p in posts
        ]
        
        if engagement_values:
            engagement_values.sort()
            metrics['median_engagement'] = median(engagement_values)
            metrics['p95_engagement'] = engagement_values[int(len(engagement_values) * 0.95)] if engagement_values else 0
        
        return metrics
    
    def calculate_trend_metrics(
        self,
        snapshots: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Calculate trend metrics from historical snapshots.
        
        Args:
            snapshots: List of snapshot data (most recent first)
            
        Returns:
            Dictionary with trend metrics
        """
        if len(snapshots) < 2:
            return {
                'trend': 'insufficient_data',
            }
        
        # Extract follower counts
        followers = [s.get('followers_count', 0) or 0 for s in snapshots]
        
        # Calculate trend direction
        if followers[0] > followers[-1]:
            trend = 'increasing'
        elif followers[0] < followers[-1]:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        # Calculate growth rate
        if followers[-1] > 0:
            total_growth = followers[0] - followers[-1]
            growth_rate = (total_growth / followers[-1]) * 100
        else:
            growth_rate = 0.0
        
        # Calculate volatility (standard deviation of changes)
        changes = [
            followers[i] - followers[i+1]
            for i in range(len(followers) - 1)
        ]
        
        if changes:
            avg_change = mean(changes)
            volatility = sum((c - avg_change) ** 2 for c in changes) / len(changes)
            volatility = volatility ** 0.5
        else:
            volatility = 0.0
        
        return {
            'trend': trend,
            'growth_rate': round(growth_rate, 2),
            'total_growth': followers[0] - followers[-1],
            'volatility': round(volatility, 2),
            'data_points': len(snapshots),
        }


# Global metrics calculator
_metrics_calculator: Optional[MetricsCalculator] = None


def get_metrics_calculator() -> MetricsCalculator:
    """Get or create global metrics calculator."""
    global _metrics_calculator
    if _metrics_calculator is None:
        _metrics_calculator = MetricsCalculator()
    return _metrics_calculator

