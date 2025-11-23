"""
Incident management system.
Tracks incidents, manages response workflows, and handles post-incident reviews.
"""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)


class IncidentSeverity(Enum):
    """Incident severity levels."""
    CRITICAL = 'critical'
    HIGH = 'high'
    MEDIUM = 'medium'
    LOW = 'low'


class IncidentStatus(Enum):
    """Incident status."""
    OPEN = 'open'
    INVESTIGATING = 'investigating'
    RESOLVED = 'resolved'
    CLOSED = 'closed'


@dataclass
class Incident:
    """Represents an incident."""
    incident_id: str
    title: str
    description: str
    severity: IncidentSeverity
    status: IncidentStatus
    created_at: datetime
    detected_by: Optional[str] = None
    assigned_to: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution: Optional[str] = None
    affected_services: List[str] = field(default_factory=list)
    related_alerts: List[str] = field(default_factory=list)
    timeline: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class OnCallRotation:
    """On-call rotation schedule."""
    rotation_id: str
    name: str
    members: List[str]
    current_on_call: Optional[str] = None
    schedule: Dict = field(default_factory=dict)  # Day -> user mapping


class IncidentManager:
    """Manages incidents and response workflows."""
    
    def __init__(self):
        self.incidents: Dict[str, Incident] = {}
        self.on_call_rotations: Dict[str, OnCallRotation] = {}
        self.incident_counter = 0
    
    def create_incident(self, title: str, description: str, severity: IncidentSeverity,
                       detected_by: Optional[str] = None, affected_services: Optional[List[str]] = None) -> Incident:
        """
        Create a new incident.
        
        Args:
            title: Incident title
            description: Incident description
            severity: Incident severity
            detected_by: Who detected the incident
            affected_services: List of affected services
        
        Returns:
            Created incident
        """
        self.incident_counter += 1
        incident_id = f"INC-{self.incident_counter:04d}"
        
        incident = Incident(
            incident_id=incident_id,
            title=title,
            description=description,
            severity=severity,
            status=IncidentStatus.OPEN,
            created_at=datetime.utcnow(),
            detected_by=detected_by,
            affected_services=affected_services or []
        )
        
        # Add initial timeline entry
        incident.timeline.append({
            'timestamp': incident.created_at.isoformat(),
            'action': 'incident_created',
            'user': detected_by or 'system',
            'description': f"Incident created: {title}"
        })
        
        self.incidents[incident_id] = incident
        
        logger.critical(
            f"Incident created: {incident_id} - {title}",
            extra={
                'incident_id': incident_id,
                'severity': severity.value,
                'affected_services': affected_services
            }
        )
        
        return incident
    
    def update_incident_status(self, incident_id: str, status: IncidentStatus,
                              user: str, notes: Optional[str] = None):
        """Update incident status."""
        if incident_id not in self.incidents:
            return False
        
        incident = self.incidents[incident_id]
        old_status = incident.status
        incident.status = status
        
        if status == IncidentStatus.RESOLVED:
            incident.resolved_at = datetime.utcnow()
            incident.resolved_by = user
        
        incident.timeline.append({
            'timestamp': datetime.utcnow().isoformat(),
            'action': 'status_change',
            'user': user,
            'old_status': old_status.value,
            'new_status': status.value,
            'notes': notes
        })
        
        return True
    
    def assign_incident(self, incident_id: str, user: str):
        """Assign incident to a user."""
        if incident_id not in self.incidents:
            return False
        
        incident = self.incidents[incident_id]
        incident.assigned_to = user
        
        incident.timeline.append({
            'timestamp': datetime.utcnow().isoformat(),
            'action': 'assigned',
            'user': user,
            'assigned_to': user
        })
        
        return True
    
    def add_timeline_entry(self, incident_id: str, action: str, user: str, description: str):
        """Add timeline entry to incident."""
        if incident_id not in self.incidents:
            return False
        
        incident = self.incidents[incident_id]
        incident.timeline.append({
            'timestamp': datetime.utcnow().isoformat(),
            'action': action,
            'user': user,
            'description': description
        })
        
        return True
    
    def resolve_incident(self, incident_id: str, resolved_by: str, resolution: str):
        """Resolve an incident."""
        if incident_id not in self.incidents:
            return False
        
        incident = self.incidents[incident_id]
        incident.status = IncidentStatus.RESOLVED
        incident.resolved_at = datetime.utcnow()
        incident.resolved_by = resolved_by
        incident.resolution = resolution
        
        incident.timeline.append({
            'timestamp': datetime.utcnow().isoformat(),
            'action': 'resolved',
            'user': resolved_by,
            'resolution': resolution
        })
        
        logger.info(f"Incident resolved: {incident_id} by {resolved_by}")
        return True
    
    def get_open_incidents(self, severity: Optional[IncidentSeverity] = None) -> List[Incident]:
        """Get open incidents."""
        incidents = [
            inc for inc in self.incidents.values()
            if inc.status in [IncidentStatus.OPEN, IncidentStatus.INVESTIGATING]
        ]
        
        if severity:
            incidents = [inc for inc in incidents if inc.severity == severity]
        
        return sorted(incidents, key=lambda x: x.created_at, reverse=True)
    
    def get_incident(self, incident_id: str) -> Optional[Incident]:
        """Get incident by ID."""
        return self.incidents.get(incident_id)
    
    def create_on_call_rotation(self, rotation_id: str, name: str, members: List[str]) -> OnCallRotation:
        """Create an on-call rotation."""
        rotation = OnCallRotation(
            rotation_id=rotation_id,
            name=name,
            members=members
        )
        self.on_call_rotations[rotation_id] = rotation
        return rotation
    
    def get_current_on_call(self, rotation_id: str) -> Optional[str]:
        """Get current on-call person for a rotation."""
        if rotation_id not in self.on_call_rotations:
            return None
        
        rotation = self.on_call_rotations[rotation_id]
        if rotation.current_on_call:
            return rotation.current_on_call
        
        # Simple round-robin if no current assignment
        if rotation.members:
            # Use day of year to rotate
            day_of_year = datetime.utcnow().timetuple().tm_yday
            index = day_of_year % len(rotation.members)
            return rotation.members[index]
        
        return None


# Global incident manager instance
incident_manager = IncidentManager()


def create_incident(title: str, description: str, severity: IncidentSeverity,
                   detected_by: Optional[str] = None) -> Incident:
    """Convenience function to create incident."""
    return incident_manager.create_incident(title, description, severity, detected_by)

