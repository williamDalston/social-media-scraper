from flask import Flask, render_template, jsonify, send_file, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy import func
from scraper.schema import DimAccount, FactFollowersSnapshot, init_db, Base
from cache import init_cache, cache, invalidate_summary_cache, invalidate_history_cache, invalidate_grid_cache, invalidate_accounts_list_cache, get_metrics
from flask_compress import Compress
import pandas as pd
import io
import csv
import time
import functools
import os
from dotenv import load_dotenv

# Import auth modules
from auth.routes import auth_bp
from auth.decorators import require_auth, require_any_role
from auth.validators import validate_csv_file, sanitize_string
from middleware.security import setup_security_headers

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-jwt-secret-key-change-in-production')

# CORS Configuration
cors_origins = os.getenv('CORS_ORIGINS', 'http://localhost:5000,http://127.0.0.1:5000').split(',')
CORS(app, origins=cors_origins, supports_credentials=True)

# CSRF Protection
csrf = CSRFProtect(app)

# Rate Limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Security Headers
setup_security_headers(app)

# Register auth blueprint
app.register_blueprint(auth_bp)

# Apply rate limiting to auth routes after blueprint registration
# Login endpoint: 5 requests per minute per IP
if 'login' in auth_bp.view_functions:
    limiter.limit("5 per minute", key_func=get_remote_address)(auth_bp.view_functions['login'])
# Register endpoint: 3 requests per hour per IP
if 'register' in auth_bp.view_functions:
    limiter.limit("3 per hour", key_func=get_remote_address)(auth_bp.view_functions['register'])

db_path = os.getenv('DATABASE_PATH', 'social_media.db')

# Initialize caching
init_cache(app)

# Initialize response compression
Compress(app)

# Performance tracking decorator
def track_performance(endpoint_name=None):
    """Decorator to track API performance metrics."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            endpoint = endpoint_name or func.__name__
            error = False
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                error = True
                raise
            finally:
                duration = time.time() - start_time
                metrics = get_metrics()
                metrics.record_api_request(endpoint, duration, error)
        return wrapper
    return decorator

def get_db_session():
    engine = init_db(db_path)
    # Ensure all tables exist (including User table)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/summary')
@limiter.limit("100 per minute")
@require_auth
@cache.cached(timeout=300, key_prefix='summary:latest')  # 5 minutes cache
@track_performance('api_summary')
def api_summary():
    """Get summary of all accounts with latest metrics. Cached for 5 minutes."""
    session = get_db_session()
    try:
        # Get latest snapshot date - optimized query
        latest_date = session.query(
            func.max(FactFollowersSnapshot.snapshot_date)
        ).scalar()
        
        if not latest_date:
            return jsonify([])
        
        # Optimized query with eager loading to avoid N+1
        results = session.query(DimAccount, FactFollowersSnapshot).join(
            FactFollowersSnapshot,
            DimAccount.account_key == FactFollowersSnapshot.account_key
        ).filter(
            FactFollowersSnapshot.snapshot_date == latest_date
        ).options(
            joinedload(DimAccount)  # Eager load account data
        ).all()
        
        data = []
        for account, snapshot in results:
            data.append({
                'platform': account.platform,
                'handle': account.handle,
                'followers': snapshot.followers_count or 0,
                'engagement': snapshot.engagements_total or 0,
                'posts': snapshot.posts_count or 0
            })
        
        return jsonify(data)
    finally:
        session.close()

@app.route('/api/history/<platform>/<handle>')
@limiter.limit("100 per minute")
@require_auth
@cache.cached(timeout=600, key_prefix='history')  # 10 minutes cache
@track_performance('api_history')
def api_history(platform, handle):
    """Get history for a specific account. Cached for 10 minutes."""
    # Sanitize input to prevent injection attacks
    platform = sanitize_string(platform, 50)
    handle = sanitize_string(handle, 100)
    
    session = get_db_session()
    try:
        # Optimized query with index on platform and handle
        account = session.query(DimAccount).filter_by(
            platform=platform,
            handle=handle
        ).first()
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Optimized query - use index on account_key
        history = session.query(FactFollowersSnapshot).filter_by(
            account_key=account.account_key
        ).order_by(FactFollowersSnapshot.snapshot_date).all()
        
        data = {
            'dates': [h.snapshot_date.isoformat() for h in history],
            'followers': [h.followers_count or 0 for h in history],
            'engagement': [h.engagements_total or 0 for h in history]
        }
        
        return jsonify(data)
    finally:
        session.close()

@app.route('/api/download')
@limiter.limit("10 per hour")
@require_auth
@track_performance('api_download')
def download_csv():
    """Download all data as CSV. Not cached as it's a download endpoint."""
    session = get_db_session()
    try:
        # Optimized query with eager loading
        query = session.query(
            DimAccount.platform,
            DimAccount.handle,
            DimAccount.org_name,
            FactFollowersSnapshot.snapshot_date,
            FactFollowersSnapshot.followers_count,
            FactFollowersSnapshot.engagements_total,
            FactFollowersSnapshot.posts_count,
            FactFollowersSnapshot.likes_count,
            FactFollowersSnapshot.comments_count,
            FactFollowersSnapshot.shares_count
        ).join(
            FactFollowersSnapshot,
            DimAccount.account_key == FactFollowersSnapshot.account_key
        ).order_by(
            FactFollowersSnapshot.snapshot_date.desc(),
            DimAccount.platform,
            DimAccount.handle
        ).all()
        
        # Convert to CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Platform', 'Handle', 'Organization', 'Date', 'Followers', 'Engagement Total', 'Posts', 'Likes', 'Comments', 'Shares'])
        
        for row in query:
            writer.writerow(row)
        
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name='hhs_social_media_data.csv'
        )
    finally:
        session.close()

@app.route('/api/grid')
@limiter.limit("100 per minute")
@require_auth
@cache.cached(timeout=300, key_prefix='grid')  # 5 minutes cache
@track_performance('api_grid')
def api_grid():
    """Get grid data with pagination. Cached for 5 minutes."""
    session = get_db_session()
    try:
        # Pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        # Limit per_page to prevent abuse
        per_page = min(per_page, 1000)
        per_page = max(per_page, 1)
        
        # Base query
        base_query = session.query(
            DimAccount.platform,
            DimAccount.handle,
            DimAccount.org_name,
            FactFollowersSnapshot.snapshot_date,
            FactFollowersSnapshot.followers_count,
            FactFollowersSnapshot.engagements_total,
            FactFollowersSnapshot.posts_count,
            FactFollowersSnapshot.likes_count,
            FactFollowersSnapshot.comments_count,
            FactFollowersSnapshot.shares_count
        ).join(
            FactFollowersSnapshot,
            DimAccount.account_key == FactFollowersSnapshot.account_key
        ).order_by(
            FactFollowersSnapshot.snapshot_date.desc(),
            DimAccount.platform,
            DimAccount.handle
        )
        
        # Get total count
        total = base_query.count()
        
        # Apply pagination
        paginated_query = base_query.offset((page - 1) * per_page).limit(per_page)
        results = paginated_query.all()
        
        data = []
        for row in results:
            data.append([
                row.platform,
                row.handle,
                row.org_name,
                row.snapshot_date.isoformat() if row.snapshot_date else None,
                row.followers_count or 0,
                row.engagements_total or 0,
                row.posts_count or 0,
                row.likes_count or 0,
                row.comments_count or 0,
                row.shares_count or 0
            ])
        
        return jsonify({
            'data': data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page if total > 0 else 0
            }
        })
    finally:
        session.close()

@app.route('/upload', methods=['POST'])
@limiter.limit("10 per hour")
@require_any_role(['Admin', 'Editor'])
@csrf.exempt  # CSRF exempt for API endpoints, but still requires auth
@track_performance('api_upload')
def upload_csv():
    """Upload CSV file to add accounts. Invalidates cache on success."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Validate file extension
    if not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'Only CSV files are allowed'}), 400
    
    # Read file content
    file_content = file.read()
    
    # Validate CSV file (type, size, content)
    is_valid, error_message, validated_rows = validate_csv_file(file_content, max_size_mb=10)
    
    if not is_valid:
        return jsonify({'error': error_message}), 400
    
    # Process validated rows
    session = get_db_session()
    try:
        count = 0
        for row in validated_rows:
            platform = row['Platform']
            handle = row['Handle']
            org = row.get('Organization', '')
            
            # Sanitize organization name
            org = sanitize_string(org, 255)
            
            # Check if exists - optimized query
            existing = session.query(DimAccount).filter_by(
                platform=platform,
                handle=handle
            ).first()
            if not existing:
                account = DimAccount(
                    platform=platform,
                    handle=handle,
                    org_name=org,
                    account_display_name=f"{org} on {platform}" if org else f"{handle} on {platform}",
                    account_url=f"https://{platform.lower()}.com/{handle}"
                )
                session.add(account)
                count += 1
        
        session.commit()
        
        # Invalidate relevant caches
        invalidate_summary_cache()
        invalidate_grid_cache()
        invalidate_accounts_list_cache()
        
        return jsonify({'message': f'Successfully added {count} accounts'})
    finally:
        session.close()

@app.route('/api/run-scraper', methods=['POST'])
@limiter.limit("5 per hour")
@require_any_role(['Admin', 'Editor'])
@csrf.exempt  # CSRF exempt for API endpoints, but still requires auth
@track_performance('api_run_scraper')
def run_scraper():
    """Run scraper. Invalidates cache on completion."""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.get_json()
    mode = data.get('mode', 'simulated') if data else 'simulated'
    
    # Validate mode
    allowed_modes = ['simulated', 'real']
    if mode not in allowed_modes:
        return jsonify({'error': f'Invalid mode. Must be one of: {", ".join(allowed_modes)}'}), 400
    try:
        from scraper.collect_metrics import simulate_metrics
        start_time = time.time()
        simulate_metrics(db_path=db_path, mode=mode, parallel=True, max_workers=5)
        elapsed_time = time.time() - start_time
        
        # Record scraper metrics
        metrics = get_metrics()
        metrics.record_scraper_execution(elapsed_time, success=True)
        
        # Invalidate all caches after scraping
        invalidate_summary_cache()
        invalidate_grid_cache()
        invalidate_accounts_list_cache()
        
        return jsonify({
            'message': 'Scraper finished successfully',
            'execution_time': round(elapsed_time, 2)
        })
    except Exception as e:
        metrics = get_metrics()
        metrics.record_scraper_execution(0, success=False)
        return jsonify({'error': str(e)}), 500

@app.route('/api/accounts')
@limiter.limit("100 per minute")
@require_auth
@cache.cached(timeout=900, key_prefix='accounts:list')  # 15 minutes cache
@track_performance('api_accounts')
def api_accounts():
    """Get list of all accounts. Cached for 15 minutes."""
    session = get_db_session()
    try:
        # Pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 100, type=int)
        
        per_page = min(per_page, 500)
        per_page = max(per_page, 1)
        
        # Base query
        base_query = session.query(DimAccount).order_by(
            DimAccount.platform,
            DimAccount.handle
        )
        
        total = base_query.count()
        
        # Apply pagination
        accounts = base_query.offset((page - 1) * per_page).limit(per_page).all()
        
        data = []
        for account in accounts:
            data.append({
                'account_key': account.account_key,
                'platform': account.platform,
                'handle': account.handle,
                'org_name': account.org_name,
                'account_display_name': account.account_display_name,
                'is_core_account': account.is_core_account or False
            })
        
        return jsonify({
            'data': data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page if total > 0 else 0
            }
        })
    finally:
        session.close()

@app.route('/api/performance')
@require_auth
def api_performance():
    """Get performance metrics."""
    try:
        metrics = get_metrics()
        return jsonify(metrics.get_all_stats())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Error handlers for security
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429

@app.errorhandler(401)
def unauthorized_handler(e):
    return jsonify({'error': 'Authentication required'}), 401

@app.errorhandler(403)
def forbidden_handler(e):
    return jsonify({'error': 'Insufficient permissions'}), 403

if __name__ == '__main__':
    # Initialize database and create all tables (including User table)
    engine = init_db(db_path)
    Base.metadata.create_all(engine)
    
    # Ensure at least one admin user exists (creates default if none exist)
    from auth.utils import ensure_admin_exists
    ensure_admin_exists()
    
    app.run(debug=True, port=5000)
