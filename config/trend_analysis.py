"""
Trend analysis and forecasting for metrics.
Provides trend detection, forecasting, and comparative analysis.
"""
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque
import statistics

logger = logging.getLogger(__name__)


class TrendAnalyzer:
    """Analyzes trends in time series data."""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.metric_data: Dict[str, deque] = {}
    
    def add_data_point(self, metric_name: str, value: float, timestamp: Optional[datetime] = None):
        """Add a data point for trend analysis."""
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        if metric_name not in self.metric_data:
            self.metric_data[metric_name] = deque(maxlen=self.window_size)
        
        self.metric_data[metric_name].append({
            'value': value,
            'timestamp': timestamp
        })
    
    def calculate_trend(self, metric_name: str, window_minutes: Optional[int] = None) -> Dict:
        """
        Calculate trend for a metric.
        
        Args:
            metric_name: Name of the metric
            window_minutes: Time window to analyze (optional)
        
        Returns:
            Dictionary with trend information
        """
        if metric_name not in self.metric_data:
            return {}
        
        data = self.metric_data[metric_name]
        if len(data) < 2:
            return {}
        
        # Filter by time window if specified
        if window_minutes:
            cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
            data = [d for d in data if d['timestamp'] >= cutoff]
        
        if len(data) < 2:
            return {}
        
        # Calculate linear regression
        values = [d['value'] for d in data]
        timestamps = [d['timestamp'] for d in data]
        
        # Convert timestamps to numeric (seconds since first)
        first_ts = timestamps[0]
        x = [(ts - first_ts).total_seconds() for ts in timestamps]
        
        n = len(values)
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # Calculate R-squared (coefficient of determination)
        y_pred = [y_mean + slope * (x[i] - x_mean) for i in range(n)]
        ss_res = sum((values[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((values[i] - y_mean) ** 2 for i in range(n))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # Determine trend direction
        if slope > 0.01:
            direction = 'increasing'
        elif slope < -0.01:
            direction = 'decreasing'
        else:
            direction = 'stable'
        
        # Calculate change percentage
        if len(values) > 1:
            change_pct = ((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else 0
        else:
            change_pct = 0
        
        return {
            'metric_name': metric_name,
            'direction': direction,
            'slope': slope,
            'r_squared': r_squared,
            'change_percent': change_pct,
            'current_value': values[-1],
            'first_value': values[0],
            'data_points': n,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def forecast(self, metric_name: str, periods: int = 7, method: str = 'linear') -> List[Dict]:
        """
        Forecast future values.
        
        Args:
            metric_name: Name of the metric
            periods: Number of periods to forecast
            method: Forecasting method ('linear', 'moving_average')
        
        Returns:
            List of forecasted values
        """
        if metric_name not in self.metric_data:
            return []
        
        data = self.metric_data[metric_name]
        if len(data) < 2:
            return []
        
        values = [d['value'] for d in data]
        last_timestamp = data[-1]['timestamp']
        
        forecasts = []
        
        if method == 'linear':
            # Simple linear extrapolation
            trend = self.calculate_trend(metric_name)
            slope = trend.get('slope', 0)
            current_value = values[-1]
            
            for i in range(1, periods + 1):
                # Assume each period is 1 hour
                forecast_timestamp = last_timestamp + timedelta(hours=i)
                forecast_value = current_value + (slope * i * 3600)  # Convert slope to per-hour
                
                forecasts.append({
                    'timestamp': forecast_timestamp.isoformat(),
                    'value': forecast_value,
                    'confidence': max(0, 1 - (i * 0.1))  # Decreasing confidence
                })
        
        elif method == 'moving_average':
            # Moving average forecast
            window = min(7, len(values))
            avg = sum(values[-window:]) / window
            
            for i in range(1, periods + 1):
                forecast_timestamp = last_timestamp + timedelta(hours=i)
                forecasts.append({
                    'timestamp': forecast_timestamp.isoformat(),
                    'value': avg,
                    'confidence': max(0, 1 - (i * 0.15))
                })
        
        return forecasts
    
    def compare_periods(self, metric_name: str, period1_start: datetime, period1_end: datetime,
                       period2_start: datetime, period2_end: datetime) -> Dict:
        """
        Compare metric values between two time periods.
        
        Args:
            metric_name: Name of the metric
            period1_start: Start of first period
            period1_end: End of first period
            period2_start: Start of second period
            period2_end: End of second period
        
        Returns:
            Comparison dictionary
        """
        if metric_name not in self.metric_data:
            return {}
        
        data = self.metric_data[metric_name]
        
        # Get data for each period
        period1_data = [
            d for d in data
            if period1_start <= d['timestamp'] <= period1_end
        ]
        period2_data = [
            d for d in data
            if period2_start <= d['timestamp'] <= period2_end
        ]
        
        if not period1_data or not period2_data:
            return {}
        
        period1_values = [d['value'] for d in period1_data]
        period2_values = [d['value'] for d in period2_data]
        
        period1_avg = statistics.mean(period1_values)
        period2_avg = statistics.mean(period2_values)
        
        change = period2_avg - period1_avg
        change_pct = (change / period1_avg * 100) if period1_avg != 0 else 0
        
        return {
            'metric_name': metric_name,
            'period1': {
                'start': period1_start.isoformat(),
                'end': period1_end.isoformat(),
                'average': period1_avg,
                'min': min(period1_values),
                'max': max(period1_values),
                'count': len(period1_values)
            },
            'period2': {
                'start': period2_start.isoformat(),
                'end': period2_end.isoformat(),
                'average': period2_avg,
                'min': min(period2_values),
                'max': max(period2_values),
                'count': len(period2_values)
            },
            'comparison': {
                'change': change,
                'change_percent': change_pct,
                'direction': 'increase' if change > 0 else 'decrease' if change < 0 else 'stable'
            }
        }


# Global trend analyzer instance
trend_analyzer = TrendAnalyzer()

