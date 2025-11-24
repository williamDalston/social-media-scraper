"""
Anomaly detection system for monitoring metrics and alerting on anomalies.
Uses statistical methods to detect unusual patterns.
"""
import logging
import statistics
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Anomaly:
    """Represents a detected anomaly."""

    metric_name: str
    value: float
    expected_range: tuple  # (min, max)
    severity: str  # 'low', 'medium', 'high', 'critical'
    timestamp: datetime
    description: str
    context: Dict


class AnomalyDetector:
    """Detects anomalies in time series data using statistical methods."""

    def __init__(self, window_size: int = 100, z_threshold: float = 3.0):
        """
        Initialize anomaly detector.

        Args:
            window_size: Number of data points to use for baseline
            z_threshold: Z-score threshold for anomaly detection (default: 3.0 = 3 sigma)
        """
        self.window_size = window_size
        self.z_threshold = z_threshold
        self.metric_history: Dict[str, deque] = {}
        self.detected_anomalies: List[Anomaly] = []

    def add_data_point(
        self, metric_name: str, value: float, timestamp: Optional[datetime] = None
    ):
        """
        Add a data point for anomaly detection.

        Args:
            metric_name: Name of the metric
            value: Metric value
            timestamp: Timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        if metric_name not in self.metric_history:
            self.metric_history[metric_name] = deque(maxlen=self.window_size)

        self.metric_history[metric_name].append(
            {"value": value, "timestamp": timestamp}
        )

    def detect_anomaly(
        self, metric_name: str, value: float, timestamp: Optional[datetime] = None
    ) -> Optional[Anomaly]:
        """
        Detect if a value is anomalous.

        Args:
            metric_name: Name of the metric
            value: Current value to check
            timestamp: Timestamp (defaults to now)

        Returns:
            Anomaly object if detected, None otherwise
        """
        if metric_name not in self.metric_history:
            # Not enough data yet
            return None

        history = self.metric_history[metric_name]
        if len(history) < 10:  # Need at least 10 data points
            return None

        # Calculate statistics
        values = [d["value"] for d in history]
        mean = statistics.mean(values)
        stdev = statistics.stdev(values) if len(values) > 1 else 0

        if stdev == 0:
            # No variation, can't detect anomalies
            return None

        # Calculate Z-score
        z_score = abs((value - mean) / stdev) if stdev > 0 else 0

        # Determine severity
        if z_score >= self.z_threshold * 2:
            severity = "critical"
        elif z_score >= self.z_threshold * 1.5:
            severity = "high"
        elif z_score >= self.z_threshold:
            severity = "medium"
        else:
            return None  # Not anomalous

        # Calculate expected range
        expected_min = mean - (self.z_threshold * stdev)
        expected_max = mean + (self.z_threshold * stdev)

        anomaly = Anomaly(
            metric_name=metric_name,
            value=value,
            expected_range=(expected_min, expected_max),
            severity=severity,
            timestamp=timestamp or datetime.utcnow(),
            description=f"{metric_name} value {value:.2f} is {z_score:.2f} standard deviations from mean ({mean:.2f})",
            context={
                "mean": mean,
                "stdev": stdev,
                "z_score": z_score,
                "history_size": len(history),
            },
        )

        self.detected_anomalies.append(anomaly)
        return anomaly

    def detect_trend_anomaly(
        self, metric_name: str, window_minutes: int = 60
    ) -> Optional[Anomaly]:
        """
        Detect trend anomalies (sudden changes in trend).

        Args:
            metric_name: Name of the metric
            window_minutes: Time window to analyze

        Returns:
            Anomaly if trend anomaly detected
        """
        if metric_name not in self.metric_history:
            return None

        history = self.metric_history[metric_name]
        if len(history) < 20:
            return None

        # Get recent data points
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        recent = [d for d in history if d["timestamp"] >= cutoff]

        if len(recent) < 10:
            return None

        # Calculate trend (simple linear regression slope)
        values = [d["value"] for d in recent]
        n = len(values)
        x = list(range(n))

        # Calculate slope
        x_mean = sum(x) / n
        y_mean = sum(values) / n

        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return None

        slope = numerator / denominator

        # Compare with historical trend
        # (In production, would compare with longer-term baseline)
        if abs(slope) > statistics.stdev(values) * 2:
            return Anomaly(
                metric_name=metric_name,
                value=values[-1],
                expected_range=(min(values), max(values)),
                severity="medium",
                timestamp=datetime.utcnow(),
                description=f"{metric_name} shows unusual trend (slope: {slope:.2f})",
                context={"slope": slope, "window_minutes": window_minutes},
            )

        return None

    def get_recent_anomalies(
        self, hours: int = 24, severity: Optional[str] = None
    ) -> List[Anomaly]:
        """
        Get recent anomalies.

        Args:
            hours: Number of hours to look back
            severity: Filter by severity (optional)

        Returns:
            List of anomalies
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        anomalies = [a for a in self.detected_anomalies if a.timestamp >= cutoff]

        if severity:
            anomalies = [a for a in anomalies if a.severity == severity]

        return sorted(anomalies, key=lambda x: x.timestamp, reverse=True)


# Global anomaly detector instance
anomaly_detector = AnomalyDetector()


def detect_anomaly(metric_name: str, value: float) -> Optional[Anomaly]:
    """Convenience function to detect anomaly."""
    anomaly = anomaly_detector.detect_anomaly(metric_name, value)
    if anomaly:
        logger.warning(
            f"Anomaly detected: {anomaly.description}",
            extra={
                "metric_name": metric_name,
                "value": value,
                "severity": anomaly.severity,
                "z_score": anomaly.context.get("z_score"),
            },
        )
    return anomaly
