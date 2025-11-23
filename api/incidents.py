"""
Incident management API endpoints.
"""
import logging
from flask import Blueprint, jsonify, request
from auth.decorators import require_auth, require_any_role
from datetime import datetime
from config.incident_management import IncidentSeverity, IncidentStatus

logger = logging.getLogger(__name__)

incidents_bp = Blueprint('incidents', __name__, url_prefix='/api/incidents')


@incidents_bp.route('/', methods=['GET'])
@require_any_role(['Admin', 'Viewer'])
def get_incidents():
    """Get incidents."""
    try:
        from config.incident_management import incident_manager
        
        status = request.args.get('status', type=str)
        severity = request.args.get('severity', type=str)
        
        if status == 'open':
            incidents = incident_manager.get_open_incidents()
        else:
            # Get all incidents (simplified - in production would paginate)
            incidents = list(incident_manager.incidents.values())
        
        if severity:
            try:
                severity_enum = IncidentSeverity(severity.lower())
                incidents = [i for i in incidents if i.severity == severity_enum]
            except ValueError:
                pass
        
        return jsonify({
            'incidents': [
                {
                    'incident_id': i.incident_id,
                    'title': i.title,
                    'description': i.description,
                    'severity': i.severity.value,
                    'status': i.status.value,
                    'created_at': i.created_at.isoformat(),
                    'resolved_at': i.resolved_at.isoformat() if i.resolved_at else None,
                    'assigned_to': i.assigned_to,
                    'affected_services': i.affected_services
                }
                for i in incidents[:50]  # Limit to 50
            ],
            'count': len(incidents),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.exception("Failed to get incidents")
        return jsonify({'error': str(e)}), 500


@incidents_bp.route('/', methods=['POST'])
@require_any_role(['Admin'])
def create_incident():
    """Create a new incident."""
    try:
        from config.incident_management import incident_manager, IncidentSeverity
        
        data = request.get_json()
        title = data.get('title')
        description = data.get('description')
        severity_str = data.get('severity', 'medium')
        detected_by = data.get('detected_by')
        affected_services = data.get('affected_services', [])
        
        if not title or not description:
            return jsonify({'error': 'Title and description required'}), 400
        
        try:
            severity = IncidentSeverity(severity_str.lower())
        except ValueError:
            return jsonify({'error': 'Invalid severity'}), 400
        
        incident = incident_manager.create_incident(
            title=title,
            description=description,
            severity=severity,
            detected_by=detected_by,
            affected_services=affected_services
        )
        
        return jsonify({
            'incident_id': incident.incident_id,
            'title': incident.title,
            'severity': incident.severity.value,
            'status': incident.status.value,
            'created_at': incident.created_at.isoformat()
        }), 201
    except Exception as e:
        logger.exception("Failed to create incident")
        return jsonify({'error': str(e)}), 500


@incidents_bp.route('/<incident_id>', methods=['GET'])
@require_any_role(['Admin', 'Viewer'])
def get_incident(incident_id):
    """Get a specific incident."""
    try:
        from config.incident_management import incident_manager
        
        incident = incident_manager.get_incident(incident_id)
        
        if not incident:
            return jsonify({'error': 'Incident not found'}), 404
        
        return jsonify({
            'incident_id': incident.incident_id,
            'title': incident.title,
            'description': incident.description,
            'severity': incident.severity.value,
            'status': incident.status.value,
            'created_at': incident.created_at.isoformat(),
            'resolved_at': incident.resolved_at.isoformat() if incident.resolved_at else None,
            'resolved_by': incident.resolved_by,
            'resolution': incident.resolution,
            'assigned_to': incident.assigned_to,
            'affected_services': incident.affected_services,
            'timeline': incident.timeline
        })
    except Exception as e:
        logger.exception("Failed to get incident")
        return jsonify({'error': str(e)}), 500


@incidents_bp.route('/<incident_id>/resolve', methods=['POST'])
@require_any_role(['Admin'])
def resolve_incident(incident_id):
    """Resolve an incident."""
    try:
        from config.incident_management import incident_manager
        
        data = request.get_json()
        resolved_by = data.get('resolved_by', 'system')
        resolution = data.get('resolution', '')
        
        success = incident_manager.resolve_incident(incident_id, resolved_by, resolution)
        
        if not success:
            return jsonify({'error': 'Incident not found'}), 404
        
        return jsonify({'message': 'Incident resolved'})
    except Exception as e:
        logger.exception("Failed to resolve incident")
        return jsonify({'error': str(e)}), 500


@incidents_bp.route('/oncall', methods=['GET'])
@require_any_role(['Admin', 'Viewer'])
def get_oncall():
    """Get current on-call information."""
    try:
        from config.incident_management import incident_manager
        
        rotations = {}
        for rotation_id, rotation in incident_manager.on_call_rotations.items():
            current = incident_manager.get_current_on_call(rotation_id)
            rotations[rotation_id] = {
                'name': rotation.name,
                'members': rotation.members,
                'current_on_call': current
            }
        
        return jsonify({
            'rotations': rotations,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.exception("Failed to get on-call info")
        return jsonify({'error': str(e)}), 500

