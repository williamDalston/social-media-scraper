"""
Escalation procedures and workflows.
Defines escalation paths and procedures for incidents and alerts.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class EscalationLevel(Enum):
    """Escalation levels."""
    L1 = 'L1'  # First responder
    L2 = 'L2'  # Senior engineer
    L3 = 'L3'  # Architect/Lead
    L4 = 'L4'  # Management
    L5 = 'L5'  # Executive


@dataclass
class EscalationRule:
    """Escalation rule definition."""
    rule_id: str
    condition: str  # 'time_elapsed', 'severity', 'acknowledged'
    threshold: float  # Time in minutes or severity level
    escalate_to: EscalationLevel
    notify_channels: List[str]  # 'email', 'slack', 'pagerduty'
    enabled: bool = True


@dataclass
class EscalationEvent:
    """Represents an escalation event."""
    event_id: str
    incident_id: str
    from_level: EscalationLevel
    to_level: EscalationLevel
    reason: str
    timestamp: datetime
    escalated_by: Optional[str] = None


class EscalationManager:
    """Manages escalation procedures."""
    
    def __init__(self):
        self.rules: List[EscalationRule] = []
        self.events: List[EscalationEvent] = []
        self.event_counter = 0
        self._setup_default_rules()
    
    def _setup_default_rules(self):
        """Set up default escalation rules."""
        # Time-based escalation
        self.add_rule(EscalationRule(
            rule_id='time_critical_30min',
            condition='time_elapsed',
            threshold=30.0,  # 30 minutes
            escalate_to=EscalationLevel.L2,
            notify_channels=['slack', 'email'],
            enabled=True
        ))
        
        self.add_rule(EscalationRule(
            rule_id='time_critical_60min',
            condition='time_elapsed',
            threshold=60.0,  # 60 minutes
            escalate_to=EscalationLevel.L3,
            notify_channels=['slack', 'email', 'pagerduty'],
            enabled=True
        ))
        
        # Severity-based escalation
        self.add_rule(EscalationRule(
            rule_id='severity_critical',
            condition='severity',
            threshold=4.0,  # Critical severity
            escalate_to=EscalationLevel.L2,
            notify_channels=['slack', 'pagerduty'],
            enabled=True
        ))
    
    def add_rule(self, rule: EscalationRule):
        """Add an escalation rule."""
        self.rules.append(rule)
        logger.info(f"Added escalation rule: {rule.rule_id}")
    
    def check_escalation(self, incident_id: str, severity: str, created_at: datetime,
                         acknowledged: bool = False) -> List[EscalationEvent]:
        """
        Check if incident should be escalated.
        
        Args:
            incident_id: Incident ID
            severity: Incident severity
            created_at: When incident was created
            acknowledged: Whether incident is acknowledged
        
        Returns:
            List of escalation events
        """
        escalation_events = []
        time_elapsed = (datetime.utcnow() - created_at).total_seconds() / 60  # minutes
        
        # Severity mapping
        severity_map = {
            'critical': 4.0,
            'high': 3.0,
            'medium': 2.0,
            'low': 1.0
        }
        severity_value = severity_map.get(severity.lower(), 1.0)
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            should_escalate = False
            
            if rule.condition == 'time_elapsed' and time_elapsed >= rule.threshold:
                should_escalate = True
                reason = f"Incident open for {time_elapsed:.0f} minutes (threshold: {rule.threshold} minutes)"
            elif rule.condition == 'severity' and severity_value >= rule.threshold:
                should_escalate = True
                reason = f"Incident severity is {severity} (threshold: {rule.threshold})"
            elif rule.condition == 'acknowledged' and not acknowledged:
                should_escalate = True
                reason = "Incident not acknowledged"
            
            if should_escalate:
                self.event_counter += 1
                event = EscalationEvent(
                    event_id=f"ESC-{self.event_counter:04d}",
                    incident_id=incident_id,
                    from_level=EscalationLevel.L1,  # Default from L1
                    to_level=rule.escalate_to,
                    reason=reason,
                    timestamp=datetime.utcnow()
                )
                
                escalation_events.append(event)
                self.events.append(event)
                
                # Send notifications
                self._send_escalation_notifications(event, rule.notify_channels)
        
        return escalation_events
    
    def _send_escalation_notifications(self, event: EscalationEvent, channels: List[str]):
        """Send escalation notifications."""
        try:
            from config.alerting_config import send_alert, AlertSeverity
            
            message = (
                f"Incident {event.incident_id} escalated to {event.to_level.value}. "
                f"Reason: {event.reason}"
            )
            
            send_alert(
                title=f"Escalation: {event.incident_id}",
                message=message,
                severity=AlertSeverity.HIGH,
                source='escalation',
                channels=channels
            )
        except ImportError:
            logger.warning("Alerting not available for escalation notifications")


# Global escalation manager instance
escalation_manager = EscalationManager()

