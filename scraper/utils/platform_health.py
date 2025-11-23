"""
Platform health monitoring and tracking.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class PlatformHealthMonitor:
    """
    Monitors health of each platform scraper.
    """
    
    def __init__(self):
        """Initialize platform health monitor."""
        self._platform_health: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._platform_errors: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        logger.info("Initialized PlatformHealthMonitor")
    
    def record_scrape_result(
        self,
        platform: str,
        success: bool,
        duration: Optional[float] = None,
        error: Optional[str] = None,
    ):
        """
        Record a scrape result for a platform.
        
        Args:
            platform: Platform name
            success: Whether scraping was successful
            duration: Scrape duration in seconds
            error: Error message if failed
        """
        if platform not in self._platform_health:
            self._platform_health[platform] = {
                'total_scrapes': 0,
                'successful_scrapes': 0,
                'failed_scrapes': 0,
                'total_duration': 0.0,
                'last_success': None,
                'last_failure': None,
                'consecutive_failures': 0,
                'status': 'unknown',
            }
        
        health = self._platform_health[platform]
        health['total_scrapes'] += 1
        
        if success:
            health['successful_scrapes'] += 1
            health['last_success'] = datetime.utcnow().isoformat()
            health['consecutive_failures'] = 0
            if duration:
                health['total_duration'] += duration
        else:
            health['failed_scrapes'] += 1
            health['last_failure'] = datetime.utcnow().isoformat()
            health['consecutive_failures'] += 1
            
            # Record error
            if error:
                self._platform_errors[platform].append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'error': error,
                })
                # Keep only recent errors
                if len(self._platform_errors[platform]) > 100:
                    self._platform_errors[platform] = self._platform_errors[platform][-100:]
        
        # Update status
        self._update_status(platform)
    
    def _update_status(self, platform: str):
        """Update health status for a platform."""
        health = self._platform_health[platform]
        
        if health['total_scrapes'] == 0:
            health['status'] = 'unknown'
            return
        
        success_rate = health['successful_scrapes'] / health['total_scrapes']
        consecutive_failures = health['consecutive_failures']
        
        # Determine status
        if consecutive_failures >= 5:
            health['status'] = 'critical'
        elif consecutive_failures >= 3:
            health['status'] = 'unhealthy'
        elif success_rate >= 0.95:
            health['status'] = 'healthy'
        elif success_rate >= 0.80:
            health['status'] = 'degraded'
        else:
            health['status'] = 'unhealthy'
    
    def get_platform_health(self, platform: str) -> Dict[str, Any]:
        """
        Get health status for a platform.
        
        Args:
            platform: Platform name
            
        Returns:
            Dictionary with health information
        """
        if platform not in self._platform_health:
            return {
                'status': 'unknown',
                'message': 'No data available',
            }
        
        health = self._platform_health[platform].copy()
        
        # Calculate metrics
        if health['total_scrapes'] > 0:
            health['success_rate'] = round(
                health['successful_scrapes'] / health['total_scrapes'],
                3
            )
            if health['successful_scrapes'] > 0:
                health['average_duration'] = round(
                    health['total_duration'] / health['successful_scrapes'],
                    2
                )
            else:
                health['average_duration'] = 0.0
        else:
            health['success_rate'] = 0.0
            health['average_duration'] = 0.0
        
        # Add recent errors
        health['recent_errors'] = self._platform_errors[platform][-5:]
        
        return health
    
    def get_all_platform_health(self) -> Dict[str, Dict[str, Any]]:
        """
        Get health status for all platforms.
        
        Returns:
            Dictionary mapping platform names to health information
        """
        return {
            platform: self.get_platform_health(platform)
            for platform in self._platform_health.keys()
        }
    
    def get_unhealthy_platforms(self) -> List[str]:
        """
        Get list of unhealthy platforms.
        
        Returns:
            List of platform names with unhealthy status
        """
        unhealthy = []
        for platform in self._platform_health.keys():
            health = self.get_platform_health(platform)
            if health['status'] in ['unhealthy', 'critical']:
                unhealthy.append(platform)
        return unhealthy
    
    def detect_platform_changes(
        self,
        platform: str,
        current_structure: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Detect if platform structure has changed.
        
        Args:
            platform: Platform name
            current_structure: Current page structure (e.g., key elements found)
            
        Returns:
            Dictionary with change detection results
        """
        # Simple implementation - in production, compare with known good structure
        # For now, detect based on error patterns
        if platform not in self._platform_health:
            return {
                'has_changed': False,
                'confidence': 0.0,
            }
        
        health = self._platform_health[platform]
        
        # If consecutive failures are high, might indicate structure change
        if health['consecutive_failures'] >= 3:
            return {
                'has_changed': True,
                'confidence': min(0.8, health['consecutive_failures'] / 10),
                'reason': f"{health['consecutive_failures']} consecutive failures",
            }
        
        return {
            'has_changed': False,
            'confidence': 0.0,
        }


# Global platform health monitor
_platform_health_monitor: Optional[PlatformHealthMonitor] = None


def get_platform_health_monitor() -> PlatformHealthMonitor:
    """Get or create global platform health monitor."""
    global _platform_health_monitor
    if _platform_health_monitor is None:
        _platform_health_monitor = PlatformHealthMonitor()
    return _platform_health_monitor

