"""
Usage analytics tracking.
Tracks API usage, user activity, feature usage, and system utilization.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class UsageEvent:
    """Represents a usage event."""
    event_type: str  # 'api_call', 'scraper_run', 'dashboard_view', etc.
    user_id: Optional[str] = None
    endpoint: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict = field(default_factory=dict)


class UsageAnalytics:
    """Tracks and analyzes usage patterns."""
    
    def __init__(self, retention_days: int = 90):
        self.retention_days = retention_days
        self.events: deque = deque(maxlen=10000)
        self.endpoint_usage: Dict[str, int] = defaultdict(int)
        self.user_activity: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.feature_usage: Dict[str, int] = defaultdict(int)
    
    def record_event(self, event: UsageEvent):
        """Record a usage event."""
        self.events.append(event)
        
        # Track endpoint usage
        if event.endpoint:
            self.endpoint_usage[event.endpoint] += 1
        
        # Track user activity
        if event.user_id:
            self.user_activity[event.user_id].append(event)
        
        # Track feature usage
        self.feature_usage[event.event_type] += 1
    
    def get_endpoint_usage(self, hours: int = 24) -> Dict[str, int]:
        """
        Get endpoint usage statistics.
        
        Args:
            hours: Number of hours to analyze
        
        Returns:
            Dictionary of endpoint -> count
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent_events = [
            e for e in self.events
            if e.timestamp >= cutoff and e.endpoint
        ]
        
        usage = defaultdict(int)
        for event in recent_events:
            usage[event.endpoint] += 1
        
        return dict(usage)
    
    def get_user_activity(self, user_id: str, hours: int = 24) -> List[UsageEvent]:
        """
        Get user activity.
        
        Args:
            user_id: User ID
            hours: Number of hours to look back
        
        Returns:
            List of usage events
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [
            e for e in self.user_activity.get(user_id, [])
            if e.timestamp >= cutoff
        ]
    
    def get_feature_usage(self, hours: int = 24) -> Dict[str, int]:
        """
        Get feature usage statistics.
        
        Args:
            hours: Number of hours to analyze
        
        Returns:
            Dictionary of feature -> count
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent_events = [
            e for e in self.events
            if e.timestamp >= cutoff
        ]
        
        usage = defaultdict(int)
        for event in recent_events:
            usage[event.event_type] += 1
        
        return dict(usage)
    
    def get_active_users(self, hours: int = 24) -> List[str]:
        """
        Get list of active users.
        
        Args:
            hours: Number of hours to look back
        
        Returns:
            List of user IDs
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        active_users = set()
        
        for event in self.events:
            if event.timestamp >= cutoff and event.user_id:
                active_users.add(event.user_id)
        
        return list(active_users)
    
    def get_usage_summary(self, hours: int = 24) -> Dict:
        """
        Get comprehensive usage summary.
        
        Args:
            hours: Number of hours to analyze
        
        Returns:
            Dictionary with usage statistics
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent_events = [e for e in self.events if e.timestamp >= cutoff]
        
        return {
            'period_hours': hours,
            'total_events': len(recent_events),
            'active_users': len(self.get_active_users(hours)),
            'endpoint_usage': self.get_endpoint_usage(hours),
            'feature_usage': self.get_feature_usage(hours),
            'timestamp': datetime.utcnow().isoformat()
        }


# Global usage analytics instance
usage_analytics = UsageAnalytics()


def record_usage_event(event_type: str, user_id: Optional[str] = None,
                      endpoint: Optional[str] = None, metadata: Optional[Dict] = None):
    """Convenience function to record usage event."""
    event = UsageEvent(
        event_type=event_type,
        user_id=user_id,
        endpoint=endpoint,
        metadata=metadata or {}
    )
    usage_analytics.record_event(event)

