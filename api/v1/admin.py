"""
Admin API namespace.

Endpoints for administrative operations.
"""

from flask_restx import Namespace, Resource, fields
from auth.decorators import require_role

ns = Namespace('admin', description='Administrative operations')

# Flask-RESTX models for documentation
error_model = ns.model('Error', {
    'error': fields.Nested(ns.model('ErrorDetail', {
        'code': fields.String(description='Error code'),
        'message': fields.String(description='Error message'),
        'details': fields.Raw(description='Additional error details')
    }))
})


@ns.route('/info')
@ns.doc(security='Bearer Auth')
class AdminInfo(Resource):
    """Get admin information."""
    
    @ns.doc('get_admin_info')
    @ns.response(200, 'Success')
    @ns.response(401, 'Unauthorized', error_model)
    @ns.response(403, 'Forbidden', error_model)
    @require_role('Admin')
    def get(self):
        """
        Get admin information.
        
        Admin-only endpoint for administrative data.
        """
        return {
            'message': 'Admin information',
            'version': '1.0',
            'note': 'Admin endpoints will be expanded in future versions'
        }

