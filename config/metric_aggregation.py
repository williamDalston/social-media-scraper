"""
Metric aggregation and rollup functionality.
Aggregates metrics over time periods for trend analysis.
"""
import time
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """A single metric data point."""
    timestamp: datetime
    value: float
    labels: Dict[str, str]


class MetricAggregator:
    """Aggregates metrics over time periods."""
    
    def __init__(self, retention_hours: int = 24):
        self.retention_hours = retention_hours
        self.metrics: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
    
    def record(self, metric_name: str, value: float, labels: Optional[Dict] = None):
        """
        Record a metric value.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            labels: Optional labels for the metric
        """
        point = MetricPoint(
            timestamp=datetime.utcnow(),
            value=value,
            labels=labels or {}
        )
        
        key = self._make_key(metric_name, labels)
        self.metrics[key].append(point)
    
    def _make_key(self, metric_name: str, labels: Optional[Dict]) -> str:
        """Create a key for metric storage."""
        if labels:
            label_str = ','.join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{metric_name}:{label_str}"
        return metric_name
    
    def aggregate(self, metric_name: str, window_minutes: int = 60,
                  labels: Optional[Dict] = None, aggregation: str = 'avg') -> Optional[float]:
        """
        Aggregate metric over a time window.
        
        Args:
            metric_name: Name of the metric
            window_minutes: Time window in minutes
            labels: Optional labels to filter by
            aggregation: Type of aggregation ('avg', 'sum', 'min', 'max', 'count')
        
        Returns:
            Aggregated value or None if no data
        """
        key = self._make_key(metric_name, labels)
        if key not in self.metrics:
            return None
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)
        points = [p for p in self.metrics[key] if p.timestamp >= cutoff_time]
        
        if not points:
            return None
        
        values = [p.value for p in points]
        
        if aggregation == 'avg':
            return sum(values) / len(values)
        elif aggregation == 'sum':
            return sum(values)
        elif aggregation == 'min':
            return min(values)
        elif aggregation == 'max':
            return max(values)
        elif aggregation == 'count':
            return len(values)
        else:
            raise ValueError(f"Unknown aggregation: {aggregation}")
    
    def get_rollup(self, metric_name: str, labels: Optional[Dict] = None,
                   periods: List[int] = None) -> Dict[str, float]:
        """
        Get metric rollups for multiple time periods.
        
        Args:
            metric_name: Name of the metric
            labels: Optional labels to filter by
            periods: List of time periods in minutes (default: [5, 15, 60, 1440])
        
        Returns:
            Dictionary with period -> aggregated value
        """
        if periods is None:
            periods = [5, 15, 60, 1440]  # 5min, 15min, 1hr, 24hr
        
        rollup = {}
        for period in periods:
            value = self.aggregate(metric_name, window_minutes=period, labels=labels)
            if value is not None:
                rollup[f"{period}m"] = value
        
        return rollup
    
    def get_trend(self, metric_name: str, labels: Optional[Dict] = None,
                  window_minutes: int = 60, buckets: int = 10) -> List[Dict]:
        """
        Get metric trend over time (time series data).
        
        Args:
            metric_name: Name of the metric
            labels: Optional labels to filter by
            window_minutes: Time window to analyze
            buckets: Number of time buckets
        
        Returns:
            List of {timestamp, value} dictionaries
        """
        key = self._make_key(metric_name, labels)
        if key not in self.metrics:
            return []
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=window_minutes)
        points = [p for p in self.metrics[key] if p.timestamp >= cutoff_time]
        
        if not points:
            return []
        
        # Group points into buckets
        bucket_size = window_minutes / buckets
        buckets_data = defaultdict(list)
        
        for point in points:
            minutes_ago = (datetime.utcnow() - point.timestamp).total_seconds() / 60
            bucket = int(minutes_ago / bucket_size)
            buckets_data[bucket].append(point.value)
        
        # Aggregate each bucket
        trend = []
        for bucket in sorted(buckets_data.keys()):
            values = buckets_data[bucket]
            timestamp = datetime.utcnow() - timedelta(minutes=(bucket + 0.5) * bucket_size)
            trend.append({
                'timestamp': timestamp.isoformat(),
                'value': sum(values) / len(values) if values else 0,
                'count': len(values)
            })
        
        return trend


# Global aggregator instance
metric_aggregator = MetricAggregator()


def record_metric(metric_name: str, value: float, labels: Optional[Dict] = None):
    """Convenience function to record a metric."""
    metric_aggregator.record(metric_name, value, labels)


def get_metric_rollup(metric_name: str, labels: Optional[Dict] = None) -> Dict[str, float]:
    """Convenience function to get metric rollup."""
    return metric_aggregator.get_rollup(metric_name, labels)


def get_metric_trend(metric_name: str, labels: Optional[Dict] = None,
                     window_minutes: int = 60) -> List[Dict]:
    """Convenience function to get metric trend."""
    return metric_aggregator.get_trend(metric_name, labels, window_minutes)

