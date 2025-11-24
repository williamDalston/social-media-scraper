"""
Alerting rules and thresholds configuration.
Defines when alerts should be triggered based on metrics and conditions.
"""
import logging
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from config.alerting_config import AlertSeverity, send_alert

logger = logging.getLogger(__name__)


class AlertRule:
    """Represents an alerting rule."""

    def __init__(
        self,
        name: str,
        condition: Callable,
        severity: str,
        message_template: str,
        enabled: bool = True,
    ):
        self.name = name
        self.condition = condition
        self.severity = severity
        self.message_template = message_template
        self.enabled = enabled
        self.last_triggered = None
        self.trigger_count = 0

    def check(self, context: Dict) -> Optional[Dict]:
        """
        Check if rule condition is met.

        Args:
            context: Context dictionary with metrics/data

        Returns:
            Alert dictionary if condition met, None otherwise
        """
        if not self.enabled:
            return None

        try:
            if self.condition(context):
                self.trigger_count += 1
                self.last_triggered = datetime.utcnow()

                message = self.message_template.format(**context)

                return {
                    "title": self.name,
                    "message": message,
                    "severity": self.severity,
                    "source": "alerting_rules",
                    "metadata": {
                        "rule_name": self.name,
                        "trigger_count": self.trigger_count,
                        "context": context,
                    },
                }
        except Exception as e:
            logger.error(f"Error checking alert rule {self.name}: {e}")

        return None


# Alert rules registry
_alert_rules: List[AlertRule] = []


def register_alert_rule(rule: AlertRule):
    """Register an alert rule."""
    _alert_rules.append(rule)
    logger.info(f"Registered alert rule: {rule.name}")


def check_all_rules(context: Dict) -> List[Dict]:
    """
    Check all registered alert rules.

    Args:
        context: Context dictionary with metrics/data

    Returns:
        List of triggered alerts
    """
    triggered_alerts = []

    for rule in _alert_rules:
        alert = rule.check(context)
        if alert:
            triggered_alerts.append(alert)
            send_alert(**alert)

    return triggered_alerts


# Define common alert rules


def _high_error_rate(context: Dict) -> bool:
    """Check if error rate is too high."""
    error_rate = context.get("error_rate", 0)
    return error_rate > 10.0  # More than 10% error rate


def _low_success_rate(context: Dict) -> bool:
    """Check if scraping success rate is too low."""
    success_rate = context.get("scraping_success_rate", 100)
    return success_rate < 80.0  # Less than 80% success rate


def _high_memory_usage(context: Dict) -> bool:
    """Check if memory usage is too high."""
    memory_percent = context.get("memory_percent", 0)
    return memory_percent > 90.0  # More than 90% memory usage


def _high_disk_usage(context: Dict) -> bool:
    """Check if disk usage is too high."""
    disk_percent = context.get("disk_percent", 0)
    return disk_percent > 90.0  # More than 90% disk usage


def _slow_response_time(context: Dict) -> bool:
    """Check if API response time is too slow."""
    p95_response_time = context.get("p95_response_time_ms", 0)
    return p95_response_time > 1000.0  # More than 1 second p95


def _database_connection_failed(context: Dict) -> bool:
    """Check if database connection failed."""
    db_status = context.get("database_status", "healthy")
    return db_status != "healthy"


def _no_recent_scrapes(context: Dict) -> bool:
    """Check if no recent successful scrapes."""
    hours_since_last_scrape = context.get("hours_since_last_scrape", 0)
    return hours_since_last_scrape > 24  # No scrape in 24 hours


def _circuit_breaker_open(context: Dict) -> bool:
    """Check if any circuit breaker is open."""
    circuit_breakers = context.get("circuit_breakers", {})
    for cb_name, cb_stats in circuit_breakers.items():
        if cb_stats.get("state") == "open":
            return True
    return False


def _high_slow_query_count(context: Dict) -> bool:
    """Check if there are too many slow queries."""
    slow_query_count = context.get("slow_query_count", 0)
    return slow_query_count > 10  # More than 10 slow queries


# Register default alert rules
register_alert_rule(
    AlertRule(
        name="High Error Rate",
        condition=_high_error_rate,
        severity=AlertSeverity.HIGH,
        message_template="Error rate is {error_rate:.1f}% (threshold: 10%)",
        enabled=True,
    )
)

register_alert_rule(
    AlertRule(
        name="Low Scraping Success Rate",
        condition=_low_success_rate,
        severity=AlertSeverity.MEDIUM,
        message_template="Scraping success rate is {scraping_success_rate:.1f}% (threshold: 80%)",
        enabled=True,
    )
)

register_alert_rule(
    AlertRule(
        name="High Memory Usage",
        condition=_high_memory_usage,
        severity=AlertSeverity.HIGH,
        message_template="Memory usage is {memory_percent:.1f}% (threshold: 90%)",
        enabled=True,
    )
)

register_alert_rule(
    AlertRule(
        name="High Disk Usage",
        condition=_high_disk_usage,
        severity=AlertSeverity.MEDIUM,
        message_template="Disk usage is {disk_percent:.1f}% (threshold: 90%)",
        enabled=True,
    )
)

register_alert_rule(
    AlertRule(
        name="Slow API Response Time",
        condition=_slow_response_time,
        severity=AlertSeverity.MEDIUM,
        message_template="P95 response time is {p95_response_time_ms:.0f}ms (threshold: 1000ms)",
        enabled=True,
    )
)

register_alert_rule(
    AlertRule(
        name="Database Connection Failed",
        condition=_database_connection_failed,
        severity=AlertSeverity.CRITICAL,
        message_template="Database connection failed: {database_status}",
        enabled=True,
    )
)

register_alert_rule(
    AlertRule(
        name="No Recent Scrapes",
        condition=_no_recent_scrapes,
        severity=AlertSeverity.MEDIUM,
        message_template="No successful scrape in {hours_since_last_scrape:.1f} hours",
        enabled=True,
    )
)

register_alert_rule(
    AlertRule(
        name="Circuit Breaker Open",
        condition=_circuit_breaker_open,
        severity=AlertSeverity.HIGH,
        message_template="Circuit breaker(s) are open",
        enabled=True,
    )
)

register_alert_rule(
    AlertRule(
        name="High Slow Query Count",
        condition=_high_slow_query_count,
        severity=AlertSeverity.MEDIUM,
        message_template="{slow_query_count} slow queries detected (threshold: 10)",
        enabled=True,
    )
)


def get_alert_rules_status() -> List[Dict]:
    """Get status of all alert rules."""
    return [
        {
            "name": rule.name,
            "enabled": rule.enabled,
            "severity": rule.severity,
            "trigger_count": rule.trigger_count,
            "last_triggered": rule.last_triggered.isoformat()
            if rule.last_triggered
            else None,
        }
        for rule in _alert_rules
    ]
