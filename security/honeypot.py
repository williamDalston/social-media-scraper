"""
Honeypot endpoints for attack detection.
These endpoints appear legitimate but are traps for attackers.
"""
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import sessionmaker
from scraper.schema import init_db
from models.audit_log import AuditLog
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

db_path = os.getenv('DATABASE_PATH', 'social_media.db')

def get_db_session():
    """Get database session."""
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    return Session()

honeypot_bp = Blueprint('honeypot', __name__)

def log_honeypot_access(endpoint_name: str, details: dict = None):
    """
    Log access to honeypot endpoint.
    
    Args:
        endpoint_name: Name of honeypot endpoint
        details: Additional details about the request
    """
    session = get_db_session()
    try:
        audit_entry = AuditLog(
            event_type='honeypot_accessed',
            ip_address=request.remote_addr if request else None,
            user_agent=request.headers.get('User-Agent') if request else None,
            resource_type='honeypot',
            resource_id=endpoint_name,
            action='access',
            details=str(details) if details else None,
            success='false',  # Honeypot access is always suspicious
            error_message=f'Honeypot endpoint accessed: {endpoint_name}',
            timestamp=datetime.utcnow()
        )
        session.add(audit_entry)
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()

# Honeypot endpoints - these look like legitimate admin endpoints
# but are actually traps for attackers

@honeypot_bp.route('/admin/login.php', methods=['GET', 'POST'])
def honeypot_admin_login():
    """Honeypot: Fake admin login page."""
    log_honeypot_access('admin_login.php', {
        'method': request.method,
        'path': request.path,
        'referer': request.headers.get('Referer')
    })
    # Return a fake login page (in production, this could be a real-looking page)
    return jsonify({'error': 'Not found'}), 404

@honeypot_bp.route('/wp-admin', methods=['GET', 'POST'])
def honeypot_wp_admin():
    """Honeypot: Fake WordPress admin."""
    log_honeypot_access('wp-admin', {
        'method': request.method,
        'path': request.path
    })
    return jsonify({'error': 'Not found'}), 404

@honeypot_bp.route('/.env', methods=['GET'])
def honeypot_env():
    """Honeypot: Attempt to access .env file."""
    log_honeypot_access('.env', {
        'method': request.method,
        'path': request.path
    })
    return jsonify({'error': 'Not found'}), 404

@honeypot_bp.route('/config.php', methods=['GET'])
def honeypot_config():
    """Honeypot: Attempt to access config file."""
    log_honeypot_access('config.php', {
        'method': request.method,
        'path': request.path
    })
    return jsonify({'error': 'Not found'}), 404

@honeypot_bp.route('/api/admin/debug', methods=['GET', 'POST'])
def honeypot_debug():
    """Honeypot: Fake debug endpoint."""
    log_honeypot_access('debug', {
        'method': request.method,
        'path': request.path,
        'params': dict(request.args) if request.args else None
    })
    return jsonify({'error': 'Not found'}), 404

@honeypot_bp.route('/api/test/sql', methods=['GET', 'POST'])
def honeypot_sql_test():
    """Honeypot: SQL injection test endpoint."""
    log_honeypot_access('sql_test', {
        'method': request.method,
        'path': request.path,
        'params': dict(request.args) if request.args else None,
        'data': request.get_json() if request.is_json else None
    })
    return jsonify({'error': 'Not found'}), 404

