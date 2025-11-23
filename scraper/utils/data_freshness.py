"""
Data freshness monitoring and tracking.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class DataFreshnessMonitor:
    """
    Monitors data freshness and alerts on stale data.
    """
    
    def __init__(self):
        """Initialize data freshness monitor."""
        self._last_update: Dict[int, datetime] = {}  # account_key -> last update time
        logger.info("Initialized DataFreshnessMonitor")
    
    def record_update(self, account_key: int, timestamp: Optional[datetime] = None):
        """
        Record when data was last updated for an account.
        
        Args:
            account_key: Account key
            timestamp: Update timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        self._last_update[account_key] = timestamp
        logger.debug(f"Recorded update for account {account_key} at {timestamp}")
    
    def check_freshness(
        self,
        account_key: int,
        max_age_hours: int = 24,
    ) -> Dict[str, Any]:
        """
        Check data freshness for an account.
        
        Args:
            account_key: Account key
            max_age_hours: Maximum age in hours before data is considered stale
            
        Returns:
            Dictionary with freshness status:
            {
                'is_fresh': bool,
                'age_hours': float,
                'last_update': datetime,
                'status': 'fresh' | 'stale' | 'missing'
            }
        """
        if account_key not in self._last_update:
            return {
                'is_fresh': False,
                'age_hours': None,
                'last_update': None,
                'status': 'missing',
            }
        
        last_update = self._last_update[account_key]
        now = datetime.utcnow()
        age = now - last_update
        age_hours = age.total_seconds() / 3600
        
        is_fresh = age_hours <= max_age_hours
        
        if is_fresh:
            status = 'fresh'
        elif age_hours <= max_age_hours * 2:
            status = 'stale'
        else:
            status = 'very_stale'
        
        return {
            'is_fresh': is_fresh,
            'age_hours': round(age_hours, 2),
            'last_update': last_update.isoformat(),
            'status': status,
        }
    
    def get_stale_accounts(
        self,
        max_age_hours: int = 24,
    ) -> Dict[int, Dict[str, Any]]:
        """
        Get all accounts with stale data.
        
        Args:
            max_age_hours: Maximum age in hours before data is considered stale
            
        Returns:
            Dictionary mapping account_key to freshness info
        """
        stale_accounts = {}
        
        for account_key in self._last_update:
            freshness = self.check_freshness(account_key, max_age_hours)
            if not freshness['is_fresh']:
                stale_accounts[account_key] = freshness
        
        return stale_accounts
    
    def get_freshness_summary(self) -> Dict[str, Any]:
        """
        Get summary of data freshness across all accounts.
        
        Returns:
            Dictionary with freshness summary
        """
        if not self._last_update:
            return {
                'total_accounts': 0,
                'fresh_count': 0,
                'stale_count': 0,
                'missing_count': 0,
            }
        
        now = datetime.utcnow()
        fresh_count = 0
        stale_count = 0
        
        for account_key, last_update in self._last_update.items():
            age = (now - last_update).total_seconds() / 3600
            if age <= 24:
                fresh_count += 1
            else:
                stale_count += 1
        
        return {
            'total_accounts': len(self._last_update),
            'fresh_count': fresh_count,
            'stale_count': stale_count,
            'freshness_rate': round(fresh_count / len(self._last_update), 3) if self._last_update else 0.0,
        }


# Global freshness monitor
_freshness_monitor: Optional[DataFreshnessMonitor] = None


def get_freshness_monitor() -> DataFreshnessMonitor:
    """Get or create global data freshness monitor."""
    global _freshness_monitor
    if _freshness_monitor is None:
        _freshness_monitor = DataFreshnessMonitor()
    return _freshness_monitor

