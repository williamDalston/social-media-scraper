"""
Performance alerting system for production monitoring.
"""
import os
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from collections import deque
from threading import Lock
from enum import Enum

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class PerformanceAlert:
    """Performance alert definition."""

    def __init__(
        self,
        alert_id: str,
        name: str,
        metric: str,
        threshold: float,
        severity: AlertSeverity,
        condition: str = "greater_than",
        cooldown_seconds: int = 300,
        callback: Optional[Callable] = None,
    ):
        """
        Initialize performance alert.

        Args:
            alert_id: Unique alert identifier
            name: Alert name
            metric: Metric to monitor
            threshold: Threshold value
            severity: Alert severity
            condition: Condition type (greater_than, less_than, equals)
            cooldown_seconds: Cooldown period between alerts
            callback: Optional callback function when alert fires
        """
        self.alert_id = alert_id
        self.name = name
        self.metric = metric
        self.threshold = threshold
        self.severity = severity
        self.condition = condition
        self.cooldown_seconds = cooldown_seconds
        self.callback = callback
        self._last_triggered: Optional[datetime] = None
        self._trigger_count = 0
        self._lock = Lock()

    def check(self, value: float) -> bool:
        """
        Check if alert should fire.

        Args:
            value: Current metric value

        Returns:
            True if alert should fire
        """
        # Check cooldown
        if self._last_triggered:
            elapsed = (datetime.utcnow() - self._last_triggered).total_seconds()
            if elapsed < self.cooldown_seconds:
                return False

        # Check condition
        should_fire = False
        if self.condition == "greater_than":
            should_fire = value > self.threshold
        elif self.condition == "less_than":
            should_fire = value < self.threshold
        elif self.condition == "equals":
            should_fire = abs(value - self.threshold) < 0.001

        if should_fire:
            with self._lock:
                self._last_triggered = datetime.utcnow()
                self._trigger_count += 1

            # Call callback if provided
            if self.callback:
                try:
                    self.callback(self, value)
                except Exception as e:
                    logger.error(f"Alert callback failed for {self.alert_id}: {e}")

        return should_fire

    def get_info(self) -> Dict:
        """Get alert information."""
        with self._lock:
            return {
                "alert_id": self.alert_id,
                "name": self.name,
                "metric": self.metric,
                "threshold": self.threshold,
                "severity": self.severity.value,
                "condition": self.condition,
                "cooldown_seconds": self.cooldown_seconds,
                "last_triggered": self._last_triggered.isoformat()
                if self._last_triggered
                else None,
                "trigger_count": self._trigger_count,
            }


class PerformanceAlertManager:
    """Manages performance alerts."""

    def __init__(self):
        """Initialize alert manager."""
        self._lock = Lock()
        self._alerts: Dict[str, PerformanceAlert] = {}
        self._alert_history = deque(maxlen=1000)  # Keep last 1000 alerts

        # Initialize default alerts
        self._initialize_default_alerts()

    def _initialize_default_alerts(self):
        """Initialize default production alerts."""
        # API Response Time Alerts
        self.add_alert(
            PerformanceAlert(
                alert_id="api_response_slow_p95",
                name="API Response Time Slow (p95)",
                metric="api_response_p95",
                threshold=1.0,  # 1 second
                severity=AlertSeverity.WARNING,
                condition="greater_than",
                cooldown_seconds=300,
            )
        )

        self.add_alert(
            PerformanceAlert(
                alert_id="api_response_critical_p95",
                name="API Response Time Critical (p95)",
                metric="api_response_p95",
                threshold=2.0,  # 2 seconds
                severity=AlertSeverity.CRITICAL,
                condition="greater_than",
                cooldown_seconds=60,
            )
        )

        # Database Query Alerts
        self.add_alert(
            PerformanceAlert(
                alert_id="db_query_slow_p95",
                name="Database Query Slow (p95)",
                metric="db_query_p95",
                threshold=0.5,  # 500ms
                severity=AlertSeverity.WARNING,
                condition="greater_than",
                cooldown_seconds=300,
            )
        )

        # Cache Hit Rate Alerts
        self.add_alert(
            PerformanceAlert(
                alert_id="cache_hit_rate_low",
                name="Cache Hit Rate Low",
                metric="cache_hit_rate",
                threshold=70.0,  # 70%
                severity=AlertSeverity.WARNING,
                condition="less_than",
                cooldown_seconds=600,
            )
        )

        # Scraper Performance Alerts
        self.add_alert(
            PerformanceAlert(
                alert_id="scraper_slow_p95",
                name="Scraper Execution Slow (p95)",
                metric="scraper_execution_p95",
                threshold=10.0,  # 10 seconds
                severity=AlertSeverity.WARNING,
                condition="greater_than",
                cooldown_seconds=300,
            )
        )

        # Error Rate Alerts
        self.add_alert(
            PerformanceAlert(
                alert_id="api_error_rate_high",
                name="API Error Rate High",
                metric="api_error_rate",
                threshold=5.0,  # 5%
                severity=AlertSeverity.WARNING,
                condition="greater_than",
                cooldown_seconds=300,
            )
        )

    def add_alert(self, alert: PerformanceAlert):
        """Add an alert."""
        with self._lock:
            self._alerts[alert.alert_id] = alert

    def remove_alert(self, alert_id: str):
        """Remove an alert."""
        with self._lock:
            if alert_id in self._alerts:
                del self._alerts[alert_id]

    def check_metric(self, metric_name: str, value: float) -> List[Dict]:
        """
        Check metric against all alerts.

        Args:
            metric_name: Metric name
            value: Metric value

        Returns:
            List of triggered alerts
        """
        triggered = []

        with self._lock:
            for alert in self._alerts.values():
                if alert.metric == metric_name:
                    if alert.check(value):
                        alert_info = alert.get_info()
                        alert_info["current_value"] = value
                        alert_info["timestamp"] = datetime.utcnow().isoformat()

                        triggered.append(alert_info)

                        # Add to history
                        self._alert_history.append(
                            {
                                "alert_id": alert.alert_id,
                                "name": alert.name,
                                "metric": metric_name,
                                "value": value,
                                "threshold": alert.threshold,
                                "severity": alert.severity.value,
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        )

                        # Log alert
                        log_level = {
                            AlertSeverity.INFO: logging.INFO,
                            AlertSeverity.WARNING: logging.WARNING,
                            AlertSeverity.CRITICAL: logging.CRITICAL,
                        }.get(alert.severity, logging.WARNING)

                        logger.log(
                            log_level,
                            f"Performance alert triggered: {alert.name} - "
                            f"{metric_name}={value} (threshold={alert.threshold})",
                            extra={
                                "alert_id": alert.alert_id,
                                "metric": metric_name,
                                "value": value,
                                "threshold": alert.threshold,
                                "severity": alert.severity.value,
                            },
                        )

        return triggered

    def get_alert_history(
        self, limit: int = 100, severity: Optional[AlertSeverity] = None
    ) -> List[Dict]:
        """
        Get alert history.

        Args:
            limit: Maximum number of alerts to return
            severity: Filter by severity

        Returns:
            List of alert records
        """
        with self._lock:
            history = list(self._alert_history)

            if severity:
                history = [h for h in history if h["severity"] == severity.value]

            return history[-limit:]

    def get_active_alerts(self) -> List[Dict]:
        """Get all active alerts configuration."""
        with self._lock:
            return [alert.get_info() for alert in self._alerts.values()]

    def get_alert_summary(self) -> Dict:
        """Get alert summary statistics."""
        with self._lock:
            total_alerts = len(self._alerts)
            total_triggers = len(self._alert_history)

            # Count by severity
            severity_counts = {}
            for alert in self._alert_history:
                severity = alert["severity"]
                severity_counts[severity] = severity_counts.get(severity, 0) + 1

            # Recent triggers (last hour)
            cutoff = datetime.utcnow() - timedelta(hours=1)
            recent_triggers = [
                a
                for a in self._alert_history
                if datetime.fromisoformat(a["timestamp"]) >= cutoff
            ]

            return {
                "total_alerts_configured": total_alerts,
                "total_triggers": total_triggers,
                "recent_triggers": len(recent_triggers),
                "triggers_by_severity": severity_counts,
                "timestamp": datetime.utcnow().isoformat(),
            }


# Global instance
_alert_manager: Optional[PerformanceAlertManager] = None
_alert_manager_lock = Lock()


def get_alert_manager() -> PerformanceAlertManager:
    """Get global alert manager instance."""
    global _alert_manager
    with _alert_manager_lock:
        if _alert_manager is None:
            _alert_manager = PerformanceAlertManager()
        return _alert_manager


def check_performance_alerts(metric_name: str, value: float) -> List[Dict]:
    """Check performance alerts for a metric."""
    manager = get_alert_manager()
    return manager.check_metric(metric_name, value)


def get_alert_history(
    limit: int = 100, severity: Optional[AlertSeverity] = None
) -> List[Dict]:
    """Get alert history."""
    manager = get_alert_manager()
    return manager.get_alert_history(limit, severity)


def get_alert_summary() -> Dict:
    """Get alert summary."""
    manager = get_alert_manager()
    return manager.get_alert_summary()
