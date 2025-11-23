"""
Data insights and reporting API endpoints.
"""
import logging
from flask import Blueprint, jsonify, request
from auth.decorators import require_auth, require_any_role
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

insights_bp = Blueprint('insights', __name__, url_prefix='/api/insights')


@insights_bp.route('/', methods=['GET'])
@require_any_role(['Admin', 'Viewer'])
def get_insights():
    """Get data insights and recommendations."""
    try:
        from config.data_insights import insights_engine
        
        category = request.args.get('category', type=str)
        hours = request.args.get('hours', 24, type=int)
        
        insights = insights_engine.get_recent_insights(hours=hours, category=category)
        
        return jsonify({
            'insights': [
                {
                    'insight_id': i.insight_id,
                    'category': i.category,
                    'title': i.title,
                    'description': i.description,
                    'severity': i.severity,
                    'confidence': i.confidence,
                    'recommendation': i.recommendation,
                    'timestamp': i.timestamp.isoformat(),
                    'metadata': i.metadata
                }
                for i in insights
            ],
            'count': len(insights),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.exception("Failed to get insights")
        return jsonify({'error': str(e)}), 500


@insights_bp.route('/generate', methods=['POST'])
@require_any_role(['Admin'])
def generate_insights():
    """Generate new insights."""
    try:
        from config.data_insights import insights_engine
        
        insights = insights_engine.generate_all_insights()
        
        return jsonify({
            'insights_generated': len(insights),
            'insights': [
                {
                    'insight_id': i.insight_id,
                    'category': i.category,
                    'title': i.title,
                    'severity': i.severity,
                    'recommendation': i.recommendation
                }
                for i in insights
            ],
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.exception("Failed to generate insights")
        return jsonify({'error': str(e)}), 500


@insights_bp.route('/reports', methods=['GET'])
@require_any_role(['Admin', 'Viewer'])
def get_reports():
    """Get generated reports."""
    try:
        from config.reporting import report_generator
        
        report_type = request.args.get('type', type=str)
        limit = request.args.get('limit', 10, type=int)
        
        reports = report_generator.get_recent_reports(report_type=report_type, limit=limit)
        
        return jsonify({
            'reports': [
                {
                    'report_id': r.report_id,
                    'report_type': r.report_type,
                    'title': r.title,
                    'generated_at': r.generated_at.isoformat(),
                    'period_start': r.period_start.isoformat(),
                    'period_end': r.period_end.isoformat(),
                    'insights_count': len(r.insights),
                    'recommendations_count': len(r.recommendations)
                }
                for r in reports
            ],
            'count': len(reports),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.exception("Failed to get reports")
        return jsonify({'error': str(e)}), 500


@insights_bp.route('/reports/generate', methods=['POST'])
@require_any_role(['Admin'])
def generate_report():
    """Generate a new report."""
    try:
        from config.reporting import report_generator
        
        report_type = request.json.get('type', 'performance')
        period_days = request.json.get('period_days', 7)
        
        if report_type == 'performance':
            report = report_generator.generate_performance_report(period_days=period_days)
        elif report_type == 'trend':
            metric_name = request.json.get('metric_name', 'api_latency')
            report = report_generator.generate_trend_report(metric_name, period_days=period_days)
        elif report_type == 'executive':
            report = report_generator.generate_executive_report(period_days=period_days)
        elif report_type == 'usage':
            report = report_generator.generate_usage_report(period_days=period_days)
        else:
            return jsonify({'error': 'Invalid report type'}), 400
        
        return jsonify({
            'report_id': report.report_id,
            'report_type': report.report_type,
            'title': report.title,
            'generated_at': report.generated_at.isoformat(),
            'insights': report.insights,
            'recommendations': report.recommendations,
            'data_summary': {
                'keys': list(report.data.keys()) if isinstance(report.data, dict) else []
            }
        })
    except Exception as e:
        logger.exception("Failed to generate report")
        return jsonify({'error': str(e)}), 500


@insights_bp.route('/reports/<report_id>', methods=['GET'])
@require_any_role(['Admin', 'Viewer'])
def get_report(report_id):
    """Get a specific report."""
    try:
        from config.reporting import report_generator
        
        # Get all reports and find the one with matching ID
        reports = report_generator.get_recent_reports(limit=1000)
        report = next((r for r in reports if r.report_id == report_id), None)
        
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        return jsonify({
            'report_id': report.report_id,
            'report_type': report.report_type,
            'title': report.title,
            'generated_at': report.generated_at.isoformat(),
            'period_start': report.period_start.isoformat(),
            'period_end': report.period_end.isoformat(),
            'data': report.data,
            'insights': report.insights,
            'recommendations': report.recommendations
        })
    except Exception as e:
        logger.exception("Failed to get report")
        return jsonify({'error': str(e)}), 500

