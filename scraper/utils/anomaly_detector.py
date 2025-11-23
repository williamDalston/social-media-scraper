"""
Anomaly detection for scraped data.
Detects unusual patterns in follower counts, engagement metrics, etc.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from statistics import mean, stdev

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Detects anomalies in scraped data using statistical methods.
    """
    
    def __init__(self):
        """Initialize anomaly detector."""
        self._historical_data: Dict[int, List[Dict[str, Any]]] = {}  # account_key -> list of snapshots
        logger.info("Initialized AnomalyDetector")
    
    def _calculate_z_score(self, value: float, mean_val: float, std_val: float) -> float:
        """
        Calculate z-score for a value.
        
        Args:
            value: Current value
            mean_val: Mean of historical values
            std_val: Standard deviation of historical values
            
        Returns:
            Z-score
        """
        if std_val == 0:
            return 0.0
        return (value - mean_val) / std_val
    
    def detect_anomalies(self, account_key: int, current_data: Dict[str, Any], threshold: float = 3.0) -> Dict[str, Any]:
        """
        Detect anomalies in current data compared to historical data.
        
        Args:
            account_key: Account key
            current_data: Current snapshot data
            threshold: Z-score threshold for anomaly detection (default: 3.0)
            
        Returns:
            Dictionary with anomaly detection results:
            {
                'has_anomalies': bool,
                'anomalies': List[str],
                'scores': Dict[str, float]
            }
        """
        anomalies = []
        scores = {}
        
        # Get historical data
        if account_key not in self._historical_data:
            # No historical data - can't detect anomalies
            return {
                'has_anomalies': False,
                'anomalies': [],
                'scores': {},
            }
        
        history = self._historical_data[account_key]
        
        if len(history) < 3:
            # Need at least 3 data points for statistical analysis
            return {
                'has_anomalies': False,
                'anomalies': [],
                'scores': {},
            }
        
        # Extract historical values for each metric
        metrics = ['followers_count', 'following_count', 'posts_count', 
                  'likes_count', 'comments_count', 'shares_count']
        
        for metric in metrics:
            if metric not in current_data:
                continue
            
            current_value = current_data.get(metric, 0)
            if current_value is None or current_value == 0:
                continue
            
            # Get historical values
            historical_values = [
                h.get(metric, 0) for h in history
                if h.get(metric) is not None and h.get(metric) > 0
            ]
            
            if len(historical_values) < 3:
                continue
            
            # Calculate statistics
            mean_val = mean(historical_values)
            std_val = stdev(historical_values) if len(historical_values) > 1 else 0
            
            if std_val == 0:
                continue
            
            # Calculate z-score
            z_score = self._calculate_z_score(current_value, mean_val, std_val)
            scores[metric] = z_score
            
            # Check if anomaly (z-score > threshold)
            if abs(z_score) > threshold:
                direction = "increase" if z_score > 0 else "decrease"
                anomalies.append(
                    f"{metric}: {direction} of {abs(z_score):.2f} standard deviations "
                    f"(current: {current_value}, mean: {mean_val:.0f})"
                )
        
        return {
            'has_anomalies': len(anomalies) > 0,
            'anomalies': anomalies,
            'scores': scores,
        }
    
    def add_historical_data(self, account_key: int, snapshot_data: Dict[str, Any], max_history: int = 30):
        """
        Add snapshot data to historical records.
        
        Args:
            account_key: Account key
            snapshot_data: Snapshot data
            max_history: Maximum number of historical records to keep
        """
        if account_key not in self._historical_data:
            self._historical_data[account_key] = []
        
        # Add new data
        self._historical_data[account_key].append(snapshot_data)
        
        # Keep only recent history
        if len(self._historical_data[account_key]) > max_history:
            self._historical_data[account_key] = self._historical_data[account_key][-max_history:]
    
    def clear_old_data(self, days: int = 90):
        """
        Clear old historical data.
        
        Args:
            days: Number of days to keep data
        """
        # Simple implementation - in production, use timestamps
        logger.info(f"Clearing historical data older than {days} days")
        # For now, just clear all (can be enhanced with timestamp tracking)
        self._historical_data.clear()


# Global anomaly detector
_anomaly_detector: Optional[AnomalyDetector] = None


def get_anomaly_detector() -> AnomalyDetector:
    """Get or create global anomaly detector."""
    global _anomaly_detector
    if _anomaly_detector is None:
        _anomaly_detector = AnomalyDetector()
    return _anomaly_detector

