"""
Scraper health monitoring and metrics tracking.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class ScraperHealthMonitor:
    """
    Monitors scraper health and performance metrics.
    """
    
    def __init__(self):
        """Initialize health monitor."""
        self._metrics: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._recent_errors: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._success_rates: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        logger.info("Initialized ScraperHealthMonitor")
    
    def record_success(self, platform: str, duration: float):
        """
        Record a successful scrape.
        
        Args:
            platform: Platform name
            duration: Scrape duration in seconds
        """
        if platform not in self._metrics:
            self._metrics[platform] = {
                'total_scrapes': 0,
                'successful_scrapes': 0,
                'failed_scrapes': 0,
                'total_duration': 0.0,
                'last_success': None,
                'last_failure': None,
            }
        
        metrics = self._metrics[platform]
        metrics['total_scrapes'] += 1
        metrics['successful_scrapes'] += 1
        metrics['total_duration'] += duration
        metrics['last_success'] = datetime.utcnow()
        
        # Track success rate
        self._success_rates[platform].append(1)
    
    def record_failure(self, platform: str, error: str, duration: Optional[float] = None):
        """
        Record a failed scrape.
        
        Args:
            platform: Platform name
            error: Error message
            duration: Scrape duration in seconds (if available)
        """
        if platform not in self._metrics:
            self._metrics[platform] = {
                'total_scrapes': 0,
                'successful_scrapes': 0,
                'failed_scrapes': 0,
                'total_duration': 0.0,
                'last_success': None,
                'last_failure': None,
            }
        
        metrics = self._metrics[platform]
        metrics['total_scrapes'] += 1
        metrics['failed_scrapes'] += 1
        if duration:
            metrics['total_duration'] += duration
        metrics['last_failure'] = datetime.utcnow()
        
        # Track error
        self._recent_errors[platform].append({
            'timestamp': datetime.utcnow(),
            'error': error,
        })
        
        # Track success rate
        self._success_rates[platform].append(0)
    
    def get_health_status(self, platform: str) -> Dict[str, Any]:
        """
        Get health status for a platform.
        
        Args:
            platform: Platform name
            
        Returns:
            Dictionary with health metrics
        """
        if platform not in self._metrics:
            return {
                'status': 'unknown',
                'message': 'No data available',
            }
        
        metrics = self._metrics[platform]
        
        # Calculate success rate
        total = metrics['total_scrapes']
        if total == 0:
            success_rate = 0.0
        else:
            success_rate = metrics['successful_scrapes'] / total
        
        # Calculate average duration
        if metrics['successful_scrapes'] > 0:
            avg_duration = metrics['total_duration'] / metrics['successful_scrapes']
        else:
            avg_duration = 0.0
        
        # Determine health status
        if success_rate >= 0.95:
            status = 'healthy'
        elif success_rate >= 0.80:
            status = 'degraded'
        elif success_rate >= 0.50:
            status = 'unhealthy'
        else:
            status = 'critical'
        
        # Check recent errors
        recent_errors = list(self._recent_errors[platform])
        error_count_24h = sum(
            1 for e in recent_errors
            if datetime.utcnow() - e['timestamp'] < timedelta(hours=24)
        )
        
        return {
            'status': status,
            'success_rate': round(success_rate, 3),
            'total_scrapes': total,
            'successful_scrapes': metrics['successful_scrapes'],
            'failed_scrapes': metrics['failed_scrapes'],
            'average_duration': round(avg_duration, 2),
            'last_success': metrics['last_success'].isoformat() if metrics['last_success'] else None,
            'last_failure': metrics['last_failure'].isoformat() if metrics['last_failure'] else None,
            'errors_24h': error_count_24h,
        }
    
    def get_all_health_status(self) -> Dict[str, Dict[str, Any]]:
        """
        Get health status for all platforms.
        
        Returns:
            Dictionary mapping platform names to health status
        """
        return {
            platform: self.get_health_status(platform)
            for platform in self._metrics.keys()
        }
    
    def get_recent_errors(self, platform: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent errors for a platform.
        
        Args:
            platform: Platform name
            limit: Maximum number of errors to return
            
        Returns:
            List of recent errors
        """
        errors = list(self._recent_errors[platform])
        # Sort by timestamp (most recent first)
        errors.sort(key=lambda x: x['timestamp'], reverse=True)
        return errors[:limit]
    
    def clear_old_data(self, days: int = 7):
        """
        Clear old metrics data.
        
        Args:
            days: Number of days to keep data
        """
        logger.info(f"Clearing health monitor data older than {days} days")
        # Simple implementation - in production, use timestamps
        # For now, just clear error history
        for platform in list(self._recent_errors.keys()):
            self._recent_errors[platform].clear()


# Global health monitor
_health_monitor: Optional[ScraperHealthMonitor] = None


def get_health_monitor() -> ScraperHealthMonitor:
    """Get or create global health monitor."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = ScraperHealthMonitor()
    return _health_monitor

