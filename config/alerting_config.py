"""
Alerting and notification configuration.
Supports multiple channels: email, Slack, webhooks.
"""
import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)

# Alert state tracking (in-memory, could be moved to Redis for distributed systems)
_alert_history = defaultdict(list)
_alert_deduplication_window = timedelta(minutes=5)


class AlertSeverity:
    """Alert severity levels."""
    CRITICAL = 'critical'
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'
    INFO = 'info'


class AlertChannel:
    """Alert notification channels."""
    EMAIL = 'email'
    SLACK = 'slack'
    WEBHOOK = 'webhook'
    SENTRY = 'sentry'
    LOG = 'log'


class Alert:
    """Represents an alert."""
    
    def __init__(self, title: str, message: str, severity: str = AlertSeverity.MEDIUM,
                 source: str = 'system', metadata: Optional[Dict] = None):
        self.title = title
        self.message = message
        self.severity = severity
        self.source = source
        self.metadata = metadata or {}
        self.timestamp = datetime.utcnow()
        self.acknowledged = False
        self.acknowledged_by = None
        self.acknowledged_at = None
    
    def to_dict(self):
        """Convert alert to dictionary."""
        return {
            'title': self.title,
            'message': self.message,
            'severity': self.severity,
            'source': self.source,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat(),
            'acknowledged': self.acknowledged,
            'acknowledged_by': self.acknowledged_by,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None
        }


class AlertManager:
    """Manages alerting and notifications."""
    
    def __init__(self):
        self.channels = {}
        self.routing_rules = {}
        self._setup_channels()
        self._setup_routing()
    
    def _setup_channels(self):
        """Set up alert channels."""
        # Email channel
        if os.getenv('ALERT_EMAIL_ENABLED', 'false').lower() == 'true':
            self.channels[AlertChannel.EMAIL] = self._send_email
        
        # Slack channel
        if os.getenv('SLACK_WEBHOOK_URL'):
            self.channels[AlertChannel.SLACK] = self._send_slack
        
        # Webhook channel
        if os.getenv('ALERT_WEBHOOK_URL'):
            self.channels[AlertChannel.WEBHOOK] = self._send_webhook
        
        # Sentry channel (always available if Sentry is configured)
        self.channels[AlertChannel.SENTRY] = self._send_sentry
        
        # Log channel (always available)
        self.channels[AlertChannel.LOG] = self._send_log
    
    def _setup_routing(self):
        """Set up alert routing rules based on severity."""
        self.routing_rules = {
            AlertSeverity.CRITICAL: [AlertChannel.SLACK, AlertChannel.EMAIL, AlertChannel.WEBHOOK, AlertChannel.SENTRY],
            AlertSeverity.HIGH: [AlertChannel.SLACK, AlertChannel.EMAIL, AlertChannel.SENTRY],
            AlertSeverity.MEDIUM: [AlertChannel.SLACK, AlertChannel.SENTRY],
            AlertSeverity.LOW: [AlertChannel.SENTRY],
            AlertSeverity.INFO: [AlertChannel.LOG]
        }
    
    def send_alert(self, alert: Alert, channels: Optional[List[str]] = None):
        """
        Send an alert through configured channels.
        
        Args:
            alert: Alert object
            channels: List of channels to use (defaults to severity-based routing)
        """
        # Check for deduplication
        if self._is_duplicate(alert):
            logger.debug(f"Alert deduplicated: {alert.title}")
            return
        
        # Store alert in history
        _alert_history[alert.source].append(alert)
        
        # Determine channels
        if channels is None:
            channels = self.routing_rules.get(alert.severity, [AlertChannel.LOG])
        
        # Send to each channel
        for channel in channels:
            if channel in self.channels:
                try:
                    self.channels[channel](alert)
                except Exception as e:
                    logger.error(f"Failed to send alert via {channel}: {e}")
    
    def _is_duplicate(self, alert: Alert) -> bool:
        """Check if alert is a duplicate within the deduplication window."""
        now = datetime.utcnow()
        recent_alerts = [
            a for a in _alert_history[alert.source]
            if (now - a.timestamp) < _alert_deduplication_window
        ]
        
        for recent_alert in recent_alerts:
            if (recent_alert.title == alert.title and
                recent_alert.message == alert.message and
                recent_alert.severity == alert.severity):
                return True
        
        return False
    
    def _send_email(self, alert: Alert):
        """Send alert via email."""
        # This would integrate with an email service (SMTP, SendGrid, etc.)
        # For now, just log
        logger.info(f"EMAIL ALERT [{alert.severity.upper()}]: {alert.title} - {alert.message}")
    
    def _send_slack(self, alert: Alert):
        """Send alert via Slack webhook."""
        import requests
        
        webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        if not webhook_url:
            return
        
        # Color mapping for severity
        color_map = {
            AlertSeverity.CRITICAL: 'danger',
            AlertSeverity.HIGH: 'warning',
            AlertSeverity.MEDIUM: 'warning',
            AlertSeverity.LOW: 'good',
            AlertSeverity.INFO: '#36a64f'
        }
        
        payload = {
            'attachments': [{
                'color': color_map.get(alert.severity, 'good'),
                'title': alert.title,
                'text': alert.message,
                'fields': [
                    {'title': 'Severity', 'value': alert.severity.upper(), 'short': True},
                    {'title': 'Source', 'value': alert.source, 'short': True},
                    {'title': 'Timestamp', 'value': alert.timestamp.isoformat(), 'short': False}
                ],
                'footer': 'HHS Social Media Scraper',
                'ts': int(alert.timestamp.timestamp())
            }]
        }
        
        try:
            response = requests.post(webhook_url, json=payload, timeout=5)
            response.raise_for_status()
            logger.debug(f"Slack alert sent: {alert.title}")
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
    
    def _send_webhook(self, alert: Alert):
        """Send alert via custom webhook."""
        import requests
        
        webhook_url = os.getenv('ALERT_WEBHOOK_URL')
        if not webhook_url:
            return
        
        try:
            response = requests.post(
                webhook_url,
                json=alert.to_dict(),
                timeout=5,
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()
            logger.debug(f"Webhook alert sent: {alert.title}")
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {e}")
    
    def _send_sentry(self, alert: Alert):
        """Send alert to Sentry."""
        try:
            from config.sentry_config import capture_message
            level_map = {
                AlertSeverity.CRITICAL: 'error',
                AlertSeverity.HIGH: 'error',
                AlertSeverity.MEDIUM: 'warning',
                AlertSeverity.LOW: 'info',
                AlertSeverity.INFO: 'info'
            }
            capture_message(
                f"{alert.title}: {alert.message}",
                level=level_map.get(alert.severity, 'info'),
                context=alert.metadata
            )
        except ImportError:
            pass  # Sentry not available
    
    def _send_log(self, alert: Alert):
        """Send alert to logs."""
        log_level_map = {
            AlertSeverity.CRITICAL: logging.CRITICAL,
            AlertSeverity.HIGH: logging.ERROR,
            AlertSeverity.MEDIUM: logging.WARNING,
            AlertSeverity.LOW: logging.INFO,
            AlertSeverity.INFO: logging.INFO
        }
        logger.log(
            log_level_map.get(alert.severity, logging.INFO),
            f"ALERT [{alert.severity.upper()}]: {alert.title} - {alert.message}",
            extra=alert.metadata
        )
    
    def acknowledge_alert(self, alert_title: str, acknowledged_by: str):
        """Acknowledge an alert."""
        for alerts in _alert_history.values():
            for alert in alerts:
                if alert.title == alert_title and not alert.acknowledged:
                    alert.acknowledged = True
                    alert.acknowledged_by = acknowledged_by
                    alert.acknowledged_at = datetime.utcnow()
                    logger.info(f"Alert acknowledged: {alert_title} by {acknowledged_by}")
                    return True
        return False
    
    def get_recent_alerts(self, source: Optional[str] = None, limit: int = 50) -> List[Alert]:
        """Get recent alerts."""
        all_alerts = []
        for alerts in _alert_history.values():
            if source is None or any(a.source == source for a in alerts):
                all_alerts.extend(alerts)
        
        all_alerts.sort(key=lambda x: x.timestamp, reverse=True)
        return all_alerts[:limit]


# Global alert manager instance
alert_manager = AlertManager()


def send_alert(title: str, message: str, severity: str = AlertSeverity.MEDIUM,
               source: str = 'system', metadata: Optional[Dict] = None,
               channels: Optional[List[str]] = None):
    """
    Convenience function to send an alert.
    
    Args:
        title: Alert title
        message: Alert message
        severity: Alert severity (default: MEDIUM)
        source: Alert source (default: 'system')
        metadata: Additional metadata
        channels: Specific channels to use (optional)
    """
    alert = Alert(title, message, severity, source, metadata)
    alert_manager.send_alert(alert, channels)

