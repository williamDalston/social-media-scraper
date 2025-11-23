"""
Production monitoring API endpoints.
Provides endpoints for SLO/SLA tracking, anomaly detection, and production metrics.
"""
import logging
from flask import Blueprint, jsonify, request
from auth.decorators import require_auth, require_any_role
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

production_bp = Blueprint('production_monitoring', __name__, url_prefix='/api/production')


@production_bp.route('/slo', methods=['GET'])
@require_any_role(['Admin', 'Viewer'])
def get_slo_status():
    """Get SLO/SLA status."""
    try:
        from config.slo_sla_tracking import get_slo_status, slo_tracker
        
        status = get_slo_status()
        
        # Get compliance for each SLO
        compliance = {}
        for slo_name in status.get('slos', {}).keys():
            try:
                compliance[slo_name] = slo_tracker.get_slo_compliance(slo_name, days=30)
            except Exception:
                pass
        
        return jsonify({
            'slo_status': status,
            'compliance': compliance,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.exception("Failed to get SLO status")
        return jsonify({'error': str(e)}), 500


@production_bp.route('/anomalies', methods=['GET'])
@require_any_role(['Admin', 'Viewer'])
def get_anomalies():
    """Get recent anomalies."""
    try:
        from config.anomaly_detection import anomaly_detector
        
        hours = request.args.get('hours', 24, type=int)
        severity = request.args.get('severity', type=str)
        
        anomalies = anomaly_detector.get_recent_anomalies(hours=hours, severity=severity)
        
        return jsonify({
            'anomalies': [
                {
                    'metric_name': a.metric_name,
                    'value': a.value,
                    'expected_range': a.expected_range,
                    'severity': a.severity,
                    'description': a.description,
                    'timestamp': a.timestamp.isoformat(),
                    'context': a.context
                }
                for a in anomalies
            ],
            'count': len(anomalies),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.exception("Failed to get anomalies")
        return jsonify({'error': str(e)}), 500


@production_bp.route('/metrics/business', methods=['GET'])
@require_any_role(['Admin', 'Viewer'])
def get_business_metrics():
    """Get business metrics summary."""
    try:
        from config.business_metrics import get_business_metrics_summary
        
        summary = get_business_metrics_summary()
        
        return jsonify({
            'metrics': summary,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.exception("Failed to get business metrics")
        return jsonify({'error': str(e)}), 500


@production_bp.route('/status', methods=['GET'])
@require_any_role(['Admin', 'Viewer'])
def get_production_status():
    """Get comprehensive production status."""
    try:
        from config.slo_sla_tracking import get_slo_status
        from config.anomaly_detection import anomaly_detector
        from config.business_metrics import get_business_metrics_summary
        from config.incident_management import incident_manager
        from config.health_checks import run_all_health_checks
        import os
        
        # Gather all status information
        slo_status = get_slo_status()
        recent_anomalies = anomaly_detector.get_recent_anomalies(hours=24)
        business_metrics = get_business_metrics_summary()
        open_incidents = incident_manager.get_open_incidents()
        health_checks = run_all_health_checks(os.getenv('DATABASE_PATH', 'social_media.db'))
        
        # Calculate overall status
        critical_anomalies = [a for a in recent_anomalies if a.severity == 'critical']
        critical_incidents = [i for i in open_incidents if i.severity.value == 'critical']
        
        overall_status = 'healthy'
        if critical_incidents or critical_anomalies:
            overall_status = 'critical'
        elif open_incidents or recent_anomalies:
            overall_status = 'warning'
        
        return jsonify({
            'overall_status': overall_status,
            'slo_status': slo_status,
            'anomalies': {
                'recent': len(recent_anomalies),
                'critical': len(critical_anomalies),
                'list': [
                    {
                        'metric_name': a.metric_name,
                        'severity': a.severity,
                        'timestamp': a.timestamp.isoformat()
                    }
                    for a in recent_anomalies[:10]
                ]
            },
            'incidents': {
                'open': len(open_incidents),
                'critical': len(critical_incidents),
                'list': [
                    {
                        'incident_id': i.incident_id,
                        'title': i.title,
                        'severity': i.severity.value,
                        'status': i.status.value,
                        'created_at': i.created_at.isoformat()
                    }
                    for i in open_incidents[:10]
                ]
            },
            'business_metrics': business_metrics,
            'health_checks': {
                name: {
                    'status': result.status,
                    'message': result.message
                }
                for name, result in health_checks.items()
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.exception("Failed to get production status")
        return jsonify({'error': str(e)}), 500

