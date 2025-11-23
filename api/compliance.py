"""
Compliance API endpoints for GDPR, SOC 2, etc.
"""
from flask import Blueprint, request, jsonify, send_file
from auth.decorators import require_auth, require_any_role
from auth.jwt_utils import get_current_user
from security.compliance import get_compliance_manager
import json
import io

compliance_bp = Blueprint('compliance', __name__, url_prefix='/api/compliance')

@compliance_bp.route('/export-data', methods=['POST'])
@require_auth
def export_user_data():
    """Export user data (GDPR Right to Data Portability)."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    compliance = get_compliance_manager()
    export_data = compliance.export_user_data(user.id)
    
    if 'error' in export_data:
        return jsonify(export_data), 404
    
    # Return as JSON download
    json_str = json.dumps(export_data, indent=2)
    return send_file(
        io.BytesIO(json_str.encode('utf-8')),
        mimetype='application/json',
        as_attachment=True,
        download_name=f'user_data_export_{user.id}.json'
    )

@compliance_bp.route('/delete-data', methods=['POST'])
@require_auth
def delete_user_data():
    """Delete user data (GDPR Right to be Forgotten)."""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.get_json()
    confirm = data.get('confirm', False)
    
    if not confirm:
        return jsonify({
            'error': 'Confirmation required',
            'message': 'This action cannot be undone. Set "confirm": true to proceed.'
        }), 400
    
    compliance = get_compliance_manager()
    success = compliance.delete_user_data(user.id)
    
    if success:
        return jsonify({
            'message': 'User data has been deleted successfully'
        }), 200
    else:
        return jsonify({'error': 'Failed to delete user data'}), 500

@compliance_bp.route('/report', methods=['GET'])
@require_auth
@require_any_role(['Admin'])
def get_compliance_report():
    """Get compliance report (Admin only)."""
    compliance = get_compliance_manager()
    report = compliance.get_compliance_report()
    return jsonify(report), 200

@compliance_bp.route('/retention-policy/apply', methods=['POST'])
@require_auth
@require_any_role(['Admin'])
def apply_retention_policy():
    """Apply data retention policy (Admin only)."""
    compliance = get_compliance_manager()
    deleted_count = compliance.apply_data_retention_policy()
    return jsonify({
        'message': f'Data retention policy applied',
        'records_anonymized': deleted_count
    }), 200

