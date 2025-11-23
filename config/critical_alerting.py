"""
Critical issue alerting system.
Monitors for critical issues and sends alerts.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
logger = logging.getLogger(__name__)

# Use AlertSeverity from alerting_config
try:
    from config.alerting_config import AlertSeverity
except ImportError:
    # Fallback if not available
    class AlertSeverity:
        INFO = 'info'
        WARNING = 'warning'
        HIGH = 'high'
        CRITICAL = 'critical'


@dataclass
class CriticalAlert:
    """Represents a critical alert."""
    alert_id: str
    title: str
    message: str
    severity: str  # Alert severity as string
    source: str  # 'slo', 'anomaly', 'incident', 'health'
    source_id: Optional[str] = None
    created_at: datetime = None
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class CriticalAlertManager:
    """Manages critical alerts."""
    
    def __init__(self):
        self.alerts: List[CriticalAlert] = []
        self.alert_counter = 0
    
    def create_alert(self, title: str, message: str, severity: str,
                    source: str, source_id: Optional[str] = None) -> CriticalAlert:
        """Create a new critical alert."""
        self.alert_counter += 1
        alert_id = f"ALERT-{self.alert_counter:04d}"
        
        # Convert AlertSeverity constant to string if needed
        if hasattr(severity, 'value'):
            severity = severity.value
        elif not isinstance(severity, str):
            severity = str(severity)
        
        alert = CriticalAlert(
            alert_id=alert_id,
            title=title,
            message=message,
            severity=severity,
            source=source,
            source_id=source_id
        )
        
        self.alerts.append(alert)
        
        # Send alert notification
        self._send_alert_notification(alert)
        
        logger.critical(
            f"Critical alert created: {title}",
            extra={
                'alert_id': alert_id,
                'severity': severity,
                'source': source
            }
        )
        
        return alert
    
    def _send_alert_notification(self, alert: CriticalAlert):
        """Send alert notification via configured channels."""
        try:
            from config.alerting_config import send_alert, AlertSeverity
            
            # Determine channels based on severity
            if alert.severity == AlertSeverity.CRITICAL:
                channels = ['slack', 'email']
            elif alert.severity == AlertSeverity.HIGH:
                channels = ['slack', 'email']
            else:
                channels = ['slack']
            
            send_alert(
                title=alert.title,
                message=alert.message,
                severity=alert.severity,
                source=alert.source,
                channels=channels
            )
        except ImportError:
            logger.warning("Alerting config not available")
    
    def check_slo_violations(self):
        """Check for SLO violations and create alerts."""
        try:
            from config.slo_sla_tracking import get_slo_status
            
            slo_status = get_slo_status()
            
            for slo_name, slo_data in slo_status.get('slos', {}).items():
                if slo_data['status'] == 'breached':
                    # Check if alert already exists
                    existing = next(
                        (a for a in self.alerts
                         if a.source == 'slo' and a.source_id == slo_name and not a.resolved),
                        None
                    )
                    
                    if not existing:
                        self.create_alert(
                            title=f"SLO Violation: {slo_name}",
                            message=f"SLO {slo_name} is breached. Value: {slo_data['value']:.2f}, Target: {slo_data['target']}",
                            severity=AlertSeverity.CRITICAL,
                            source='slo',
                            source_id=slo_name
                        )
        except Exception as e:
            logger.exception("Failed to check SLO violations")
    
    def check_anomalies(self):
        """Check for critical anomalies and create alerts."""
        try:
            from config.anomaly_detection import anomaly_detector
            
            critical_anomalies = anomaly_detector.get_recent_anomalies(
                hours=1, severity='critical'
            )
            
            for anomaly in critical_anomalies:
                # Check if alert already exists
                existing = next(
                    (a for a in self.alerts
                     if a.source == 'anomaly' and a.source_id == anomaly.metric_name
                     and (datetime.utcnow() - a.created_at).total_seconds() < 3600
                     and not a.resolved),
                    None
                )
                
                if not existing:
                    self.create_alert(
                        title=f"Critical Anomaly: {anomaly.metric_name}",
                        message=anomaly.description,
                        severity=AlertSeverity.CRITICAL,
                        source='anomaly',
                        source_id=anomaly.metric_name
                    )
        except Exception as e:
            logger.exception("Failed to check anomalies")
    
    def check_incidents(self):
        """Check for critical incidents and create alerts."""
        try:
            from config.incident_management import incident_manager, IncidentSeverity
            
            critical_incidents = incident_manager.get_open_incidents(
                severity=IncidentSeverity.CRITICAL
            )
            
            for incident in critical_incidents:
                # Check if alert already exists
                existing = next(
                    (a for a in self.alerts
                     if a.source == 'incident' and a.source_id == incident.incident_id
                     and not a.resolved),
                    None
                )
                
                if not existing:
                    self.create_alert(
                        title=f"Critical Incident: {incident.title}",
                        message=incident.description,
                        severity=AlertSeverity.CRITICAL,
                        source='incident',
                        source_id=incident.incident_id
                    )
        except Exception as e:
            logger.exception("Failed to check incidents")
    
    def check_health_issues(self):
        """Check for health check failures and create alerts."""
        try:
            from config.health_checks import run_all_health_checks
            import os
            
            health_checks = run_all_health_checks(os.getenv('DATABASE_PATH', 'social_media.db'))
            
            for name, result in health_checks.items():
                if result.status != 'healthy':
                    # Check if alert already exists
                    existing = next(
                        (a for a in self.alerts
                         if a.source == 'health' and a.source_id == name and not a.resolved),
                        None
                    )
                    
                    if not existing:
                        severity = AlertSeverity.CRITICAL if result.status == 'unhealthy' else AlertSeverity.HIGH
                        self.create_alert(
                            title=f"Health Check Failed: {name}",
                            message=result.message or f"Health check {name} is {result.status}",
                            severity=severity,
                            source='health',
                            source_id=name
                        )
        except Exception as e:
            logger.exception("Failed to check health issues")
    
    def check_all(self):
        """Check all sources for critical issues."""
        self.check_slo_violations()
        self.check_anomalies()
        self.check_incidents()
        self.check_health_issues()
    
    def get_active_alerts(self, severity: Optional[str] = None) -> List[CriticalAlert]:
        """Get active (unresolved) alerts."""
        alerts = [a for a in self.alerts if not a.resolved]
        
        if severity:
            # Convert AlertSeverity constant to string if needed
            if hasattr(severity, 'value'):
                severity = severity.value
            alerts = [a for a in alerts if a.severity == severity]
        
        return sorted(alerts, key=lambda x: (
            {'critical': 0, 'high': 1, 'warning': 2, 'info': 3}.get(x.severity.value, 4),
            x.created_at
        ))
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str):
        """Acknowledge an alert."""
        alert = next((a for a in self.alerts if a.alert_id == alert_id), None)
        if alert:
            alert.acknowledged = True
            alert.acknowledged_by = acknowledged_by
            alert.acknowledged_at = datetime.utcnow()
            return True
        return False
    
    def resolve_alert(self, alert_id: str):
        """Resolve an alert."""
        alert = next((a for a in self.alerts if a.alert_id == alert_id), None)
        if alert:
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            return True
        return False


# Global alert manager instance
alert_manager = CriticalAlertManager()


def check_critical_issues():
    """Convenience function to check for critical issues."""
    alert_manager.check_all()

