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
from datetime import datetime
from dotenv import load_dotenv

# Import logging configuration
from config.logging_config import setup_logging, get_logger

# Set up logging
setup_logging()
logger = get_logger(__name__)

# Import auth modules
from auth.routes import auth_bp
from auth.decorators import require_auth, require_any_role
from auth.validators import validate_csv_file, sanitize_string
from auth.audit import log_security_event, AuditEventType, get_audit_logs
from auth.api_keys import create_api_key, revoke_api_key
from auth.ip_filter import add_ip_to_whitelist, add_ip_to_blacklist
from middleware.security import setup_security_headers

# Try to import optional OAuth and MFA modules
try:
    from auth.oauth import oauth_bp, init_oauth
    OAUTH_AVAILABLE = True
except ImportError:
    OAUTH_AVAILABLE = False
    oauth_bp = None
    init_oauth = lambda x: None

try:
    from auth.mfa import mfa_bp
    MFA_AVAILABLE = True
except ImportError:
    MFA_AVAILABLE = False
    mfa_bp = None

try:
    from auth.password_reset import password_reset_bp
    PASSWORD_RESET_AVAILABLE = True
except ImportError:
    PASSWORD_RESET_AVAILABLE = False
    password_reset_bp = None

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

# Security Middleware (bot detection, fraud detection, policy enforcement)
try:
    from middleware.security_middleware import setup_security_middleware
    setup_security_middleware(app)
except ImportError:
    pass  # Security middleware is optional

# Production Security Hardening
try:
    from security.production_hardening import setup_production_security
    setup_production_security(app)
except ImportError:
    pass  # Security middleware is optional

# Register honeypot blueprint
try:
    from security.honeypot import honeypot_bp
    app.register_blueprint(honeypot_bp)
except ImportError:
    pass  # Honeypot is optional

# Register auth blueprints
app.register_blueprint(auth_bp)
if OAUTH_AVAILABLE and oauth_bp:
    app.register_blueprint(oauth_bp)
    init_oauth(app)
if MFA_AVAILABLE and mfa_bp:
    app.register_blueprint(mfa_bp)

# Register log viewer blueprint
try:
    from api.log_viewer import log_viewer_bp
    app.register_blueprint(log_viewer_bp)
except ImportError:
    pass  # Log viewer is optional
if PASSWORD_RESET_AVAILABLE and password_reset_bp:
    app.register_blueprint(password_reset_bp)

# Register Phase 3 observability blueprints
try:
    from api.production_monitoring import production_bp
    app.register_blueprint(production_bp)
except ImportError:
    pass

try:
    from api.analytics import analytics_bp
    app.register_blueprint(analytics_bp)
except ImportError:
    pass

try:
    from api.insights import insights_bp
    app.register_blueprint(insights_bp)
except ImportError:
    pass

try:
    from api.incidents import incidents_bp
    app.register_blueprint(incidents_bp)
except ImportError:
    pass

# Register compliance blueprint
try:
    from api.compliance import compliance_bp
    app.register_blueprint(compliance_bp)
except ImportError:
    pass

# Register system health blueprint
try:
    from api.system_health import system_health_bp
    app.register_blueprint(system_health_bp)
except ImportError:
    pass

# Register performance SLA blueprint
try:
    from api.performance_slas import performance_sla_bp
    app.register_blueprint(performance_sla_bp)
except ImportError:
    pass

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
                
                # Record for SLA tracking
                try:
                    from config.production_performance import record_performance_metric
                    record_performance_metric('api_response', duration)
                    
                    # Check alerts
                    from config.performance_alerting import check_performance_alerts
                    alerts = check_performance_alerts('api_response', duration)
                    if alerts:
                        logger.warning(
                            f"Performance alerts for {endpoint}: {alerts}",
                            extra={'endpoint': endpoint, 'duration': duration, 'alerts': alerts}
                        )
                except Exception as e:
                    logger.debug(f"Performance tracking error: {e}")
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
    # Log data access
    user = getattr(request, 'current_user', None)
    if user:
        log_security_event(
            AuditEventType.DATA_ACCESS,
            user_id=user.id,
            username=user.username,
            resource_type='summary',
            action='view',
            success=True
        )
    
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
                'org_name': account.org_name or '',
                'followers': int(snapshot.followers_count or 0),
                'engagement': int(snapshot.engagements_total or 0),
                'posts': int(snapshot.posts_count or 0)
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
        # Use case-insensitive matching to handle any case variations
        # SQLite uses NOCASE collation by default for most operations, but be explicit
        account = session.query(DimAccount).filter(
            func.lower(DimAccount.platform) == func.lower(platform),
            func.lower(DimAccount.handle) == func.lower(handle)
        ).first()
        
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Optimized query - use index on account_key
        history = session.query(FactFollowersSnapshot).filter_by(
            account_key=account.account_key
        ).order_by(FactFollowersSnapshot.snapshot_date).all()
        
        data = {
            'dates': [h.snapshot_date.isoformat() for h in history],
            'followers': [int(h.followers_count or 0) for h in history],
            'engagement': [int(h.engagements_total or 0) for h in history]
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
                row.platform or '',
                row.handle or '',
                row.org_name or '',
                row.snapshot_date.isoformat() if row.snapshot_date else '',
                int(row.followers_count or 0),
                int(row.engagements_total or 0),
                int(row.posts_count or 0),
                int(row.likes_count or 0),
                int(row.comments_count or 0),
                int(row.shares_count or 0)
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

def process_csv_data(csv_data, user=None):
    """Process CSV data (from file or text) and add accounts."""
    # Validate CSV file (type, size, content)
    if isinstance(csv_data, bytes):
        csv_bytes = csv_data
    else:
        csv_bytes = csv_data.encode('utf-8')
    
    is_valid, error_message, validated_rows = validate_csv_file(csv_bytes, max_size_mb=10)
    
    if not is_valid:
        return None, error_message, 0
    
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
            
            # Check if exists - optimized query with case-insensitive matching
            existing = session.query(DimAccount).filter(
                func.lower(DimAccount.platform) == func.lower(platform),
                func.lower(DimAccount.handle) == func.lower(handle)
            ).first()
            if not existing:
                account = DimAccount(
                    platform=platform,
                    handle=handle,
                    org_name=org,
                    account_display_name=f"{org} on {platform}" if org else f"{handle} on {platform}",
                    account_url=f"https://{platform.lower()}.com/{handle}",
                    is_active=True
                )
                session.add(account)
                count += 1
        
        session.commit()
        
        # Invalidate relevant caches
        invalidate_summary_cache()
        invalidate_grid_cache()
        invalidate_accounts_list_cache()
        
        # Log file upload
        if user:
            log_security_event(
                AuditEventType.FILE_UPLOAD,
                user_id=user.id,
                username=user.username,
                resource_type='csv',
                action='upload',
                details={'accounts_added': count},
                success=True
            )
        
        return True, None, count
    except Exception as e:
        session.rollback()
        return None, str(e), 0
    finally:
        session.close()

@app.route('/upload', methods=['POST'])
@limiter.limit("10 per hour")
@require_any_role(['Admin', 'Editor'])
@csrf.exempt  # CSRF exempt for API endpoints, but still requires auth
@track_performance('api_upload')
def upload_csv():
    """Upload CSV file to add accounts. Invalidates cache on success."""
    user = getattr(request, 'current_user', None)
    
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
    
    # Process CSV data
    success, error_message, count = process_csv_data(file_content, user)
    
    if not success:
        return jsonify({'error': error_message}), 400
    
    return jsonify({'message': f'Successfully added {count} accounts', 'count': count})

@app.route('/api/upload-bulk', methods=['POST'])
@limiter.limit("10 per hour")
@require_any_role(['Admin', 'Editor'])
@csrf.exempt  # CSRF exempt for API endpoints, but still requires auth
@track_performance('api_upload_bulk')
def upload_bulk():
    """Upload accounts via pasted CSV text. Invalidates cache on success."""
    user = getattr(request, 'current_user', None)
    
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.get_json()
    csv_text = data.get('csv_data', '').strip()
    
    if not csv_text:
        return jsonify({'error': 'No CSV data provided'}), 400
    
    # Process CSV data
    success, error_message, count = process_csv_data(csv_text, user)
    
    if not success:
        return jsonify({'error': error_message}), 400
    
    return jsonify({'message': f'Successfully added {count} accounts', 'count': count})

@app.route('/api/run-scraper', methods=['POST'])
@limiter.limit("5 per hour")
@csrf.exempt  # CSRF exempt for API endpoints
@track_performance('api_run_scraper')
def run_scraper():
    """Run scraper. Invalidates cache on completion. Can run without auth for local use."""
    user = getattr(request, 'current_user', None)
    
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 400
    
    data = request.get_json() or {}
    # Default to 'real' mode - no simulations
    mode = data.get('mode', 'real')
    
    # Only allow 'real' mode - simulations disabled
    if mode != 'real':
        return jsonify({'error': 'Only real mode is supported. Simulations are disabled.'}), 400
    
    # Get database path
    db_path = os.getenv('DATABASE_PATH', 'social_media.db')
    
    # Run pre-flight checks to catch errors before starting
    try:
        from scraper.utils.preflight_checks import run_preflight_checks
        
        logger.info("Running pre-flight checks before scraper execution...")
        preflight_results = run_preflight_checks(db_path=db_path, include_network=False)
        
        if not preflight_results['all_passed']:
            error_summary = '\n'.join(preflight_results['errors'])
            logger.error(f"Pre-flight checks failed:\n{error_summary}")
            return jsonify({
                'error': 'Pre-flight checks failed',
                'details': preflight_results['errors'],
                'checks': preflight_results['checks'],
                'success': False
            }), 400
        
        logger.info(f"✓ All pre-flight checks passed. {preflight_results['account_count']} accounts ready to scrape.")
    except ImportError:
        # Preflight checks module not available - continue anyway
        logger.warning("Pre-flight checks module not available, skipping validation")
    except Exception as e:
        # Don't fail on preflight check errors - log and continue
        logger.warning(f"Pre-flight checks encountered an error (continuing anyway): {str(e)}")
    
    try:
        from scraper.collect_metrics import simulate_metrics
        import time
        start_time = time.time()
        simulate_metrics(db_path=db_path, mode=mode, parallel=True, max_workers=5)
        elapsed_time = time.time() - start_time
        
        # Record scraper metrics (if available)
        try:
            metrics = get_metrics()
            metrics.record_scraper_execution(elapsed_time, success=True)
        except:
            pass  # Metrics not required for basic functionality
        
        # Log scraper run (if user is authenticated)
        if user:
            try:
                log_security_event(
                    AuditEventType.SCRAPER_RUN,
                    user_id=user.id,
                    username=user.username,
                    resource_type='scraper',
                    action='run',
                    details={'mode': mode, 'execution_time': elapsed_time},
                    success=True
                )
            except:
                pass  # Logging not required for basic functionality
        
        # Invalidate all caches after scraping (if available)
        try:
            invalidate_summary_cache()
            invalidate_grid_cache()
            invalidate_accounts_list_cache()
        except:
            pass  # Cache invalidation not required for basic functionality
        
        return jsonify({
            'message': 'Scraper finished successfully',
            'execution_time': round(elapsed_time, 2),
            'success': True,
            'account_count': preflight_results.get('account_count', 0) if preflight_results else None,
            'checks': preflight_results.get('checks', []) if preflight_results else None
        })
    except Exception as e:
        # Record failure (if metrics available)
        try:
            metrics = get_metrics()
            metrics.record_scraper_execution(0, success=False)
        except:
            pass
        
        # Log failed scraper run (if user is authenticated)
        if user:
            try:
                log_security_event(
                    AuditEventType.SCRAPER_RUN,
                    user_id=user.id,
                    username=user.username,
                    resource_type='scraper',
                    action='run',
                    details={'mode': mode, 'error': str(e)},
                    success=False
                )
            except:
                pass
        
        # Log error
        try:
            logger.exception("Error running scraper")
        except:
            pass
        
        return jsonify({
            'error': f'Error running scraper: {str(e)}',
            'success': False
        }), 500

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
        stats = metrics.get_all_stats()
        
        # Add SLA status
        try:
            from config.production_performance import get_performance_summary, get_sla_status
            stats['sla_summary'] = get_performance_summary()
            stats['sla_status'] = get_sla_status()
        except Exception as e:
            logger.debug(f"Could not load SLA data: {e}")
            stats['sla_summary'] = {'error': 'SLA tracking not available'}
        
        # Add alert summary
        try:
            from config.performance_alerting import get_alert_summary
            stats['alerts'] = get_alert_summary()
        except Exception as e:
            logger.debug(f"Could not load alert data: {e}")
            stats['alerts'] = {'error': 'Alert tracking not available'}
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance/sla')
@require_auth
def api_performance_sla():
    """Get SLA status."""
    try:
        from config.production_performance import get_sla_status, get_performance_summary
        return jsonify({
            'summary': get_performance_summary(),
            'slas': get_sla_status()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance/alerts')
@require_auth
def api_performance_alerts():
    """Get performance alerts."""
    try:
        from config.performance_alerting import (
            get_alert_summary, get_alert_history, get_alert_manager
        )
        from config.performance_alerting import AlertSeverity
        
        return jsonify({
            'summary': get_alert_summary(),
            'active_alerts': get_alert_manager().get_active_alerts(),
            'recent_history': get_alert_history(limit=50),
            'critical_alerts': get_alert_history(limit=20, severity=AlertSeverity.CRITICAL)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance/recommendations')
@require_auth
def api_performance_recommendations():
    """Get performance optimization recommendations."""
    try:
        from config.performance_tuning import PerformanceTuner
        from cache.metrics import get_metrics
        
        metrics = get_metrics()
        stats = metrics.get_all_stats()
        
        tuner = PerformanceTuner()
        recommendations = tuner.get_performance_recommendations(stats)
        
        return jsonify({
            'recommendations': recommendations,
            'count': len(recommendations),
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance/tuning')
@require_auth
@require_any_role(['admin'])
def api_performance_tuning():
    """Get performance tuning configuration."""
    try:
        from config.performance_tuning import get_performance_tuning_config
        return jsonify(get_performance_tuning_config())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance/cache')
@require_auth
def api_cache_performance():
    """Get cache performance statistics."""
    try:
        from cache.production_monitoring import (
            get_cache_performance_stats,
            get_cache_recommendations,
            get_cache_monitor
        )
        
        monitor = get_cache_monitor()
        stats = monitor.get_overall_stats()
        recommendations = monitor.get_recommendations()
        key_stats = monitor.get_key_stats(limit=20)
        recent_errors = monitor.get_recent_errors(limit=20)
        trends = monitor.get_trends(hours=24)
        
        return jsonify({
            'stats': stats,
            'recommendations': recommendations,
            'top_keys': key_stats,
            'recent_errors': recent_errors,
            'trends': trends,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.exception("Failed to get cache performance stats")
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance/database')
@require_auth
def api_database_performance():
    """Get database performance statistics."""
    try:
        from config.database_performance import (
            get_db_performance_stats,
            get_db_recommendations,
            get_db_monitor
        )
        
        monitor = get_db_monitor()
        stats = monitor.get_overall_stats()
        recommendations = monitor.get_recommendations()
        slow_queries = monitor.get_slow_queries(limit=20)
        query_patterns = monitor.get_query_patterns(limit=20)
        recent_errors = monitor.get_recent_errors(limit=20)
        trends = monitor.get_trends(hours=24)
        
        return jsonify({
            'stats': stats,
            'recommendations': recommendations,
            'slow_queries': slow_queries,
            'query_patterns': query_patterns,
            'recent_errors': recent_errors,
            'trends': trends,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.exception("Failed to get database performance stats")
        return jsonify({'error': str(e)}), 500

@app.route('/api/performance/frontend', methods=['POST'])
def api_frontend_performance():
    """Receive frontend performance metrics."""
    try:
        data = request.get_json()
        # Store metrics (could be persisted to database or metrics system)
        logger.info("Frontend performance metrics received", extra=data)
        return jsonify({'status': 'received'}), 200
    except Exception as e:
        logger.exception("Failed to receive frontend metrics")
        return jsonify({'error': str(e)}), 500

# Admin dashboard route
@app.route('/admin')
@require_any_role(['Admin', 'Viewer'])
def admin_dashboard():
    """Admin monitoring dashboard."""
    return render_template('admin_dashboard.html')

# Admin status endpoint
@app.route('/api/admin/status')
@require_any_role(['Admin', 'Viewer'])
def admin_status():
    """Get comprehensive admin status for dashboard."""
    try:
        from config.health_checks import run_all_health_checks
        from config.business_metrics import get_business_metrics_summary
        from config.slo_sla_tracking import get_slo_status
        from config.anomaly_detection import anomaly_detector
        from config.incident_management import incident_manager
        from config.usage_analytics import usage_analytics
        from config.data_insights import insights_engine
        from config.performance_benchmarking import performance_benchmarker
        from config.metrics_config import (
            http_requests_total, scraper_runs_total,
            active_jobs, accounts_total
        )
        from sqlalchemy.orm import sessionmaker
        from scraper.schema import DimAccount, FactFollowersSnapshot, init_db
        import psutil
        import os
        
        # System health
        health_checks = run_all_health_checks(db_path)
        
        # Business metrics
        business_metrics = get_business_metrics_summary()
        
        # SLO status
        try:
            slo_status = get_slo_status()
        except Exception:
            slo_status = {}
        
        # Recent anomalies
        try:
            recent_anomalies = anomaly_detector.get_recent_anomalies(hours=24)
        except Exception:
            recent_anomalies = []
        
        # Open incidents
        try:
            open_incidents = incident_manager.get_open_incidents()
        except Exception:
            open_incidents = []
        
        # Usage analytics
        try:
            usage_summary = usage_analytics.get_usage_summary(hours=24)
        except Exception:
            usage_summary = {}
        
        # Recent insights
        try:
            recent_insights = insights_engine.get_recent_insights(hours=24)
        except Exception:
            recent_insights = []
        
        # Performance benchmarks
        try:
            benchmarks = performance_benchmarker.get_benchmark_summary()
        except Exception:
            benchmarks = {}
        
        # Database stats
        engine = init_db(db_path)
        Session = sessionmaker(bind=engine)
        session = Session()
        try:
            total_accounts = session.query(func.count(DimAccount.account_key)).scalar() or 0
            total_snapshots = session.query(func.count(FactFollowersSnapshot.snapshot_key)).scalar() or 0
            latest_snapshot = session.query(func.max(FactFollowersSnapshot.snapshot_date)).scalar()
        finally:
            session.close()
        
        # System resources
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return jsonify({
            'system': {
                'health': {
                    name: {
                        'status': result.status,
                        'message': result.message
                    }
                    for name, result in health_checks.items()
                },
                'resources': {
                    'cpu_percent': cpu_percent,
                    'memory': {
                        'total_mb': memory.total / (1024 * 1024),
                        'used_mb': memory.used / (1024 * 1024),
                        'percent': memory.percent
                    },
                    'disk': {
                        'total_gb': disk.total / (1024 * 1024 * 1024),
                        'used_gb': disk.used / (1024 * 1024 * 1024),
                        'percent': (disk.used / disk.total * 100) if disk.total > 0 else 0
                    }
                }
            },
            'business': {
                'metrics': business_metrics,
                'database': {
                    'total_accounts': total_accounts,
                    'total_snapshots': total_snapshots,
                    'latest_snapshot': latest_snapshot.isoformat() if latest_snapshot else None
                }
            },
            'observability': {
                'slo_status': slo_status,
                'anomalies': {
                    'recent_count': len(recent_anomalies),
                    'critical_count': len([a for a in recent_anomalies if a.severity == 'critical']),
                    'recent': [
                        {
                            'metric_name': a.metric_name,
                            'severity': a.severity,
                            'value': a.value,
                            'timestamp': a.timestamp.isoformat()
                        }
                        for a in recent_anomalies[:10]
                    ]
                },
                'incidents': {
                    'open_count': len(open_incidents),
                    'critical_count': len([i for i in open_incidents if i.severity.value == 'critical']),
                    'open': [
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
                'insights': {
                    'recent_count': len(recent_insights),
                    'recent': [
                        {
                            'insight_id': i.insight_id,
                            'category': i.category,
                            'title': i.title,
                            'severity': i.severity,
                            'recommendation': i.recommendation
                        }
                        for i in recent_insights[:10]
                    ]
                },
                'benchmarks': benchmarks
            },
            'usage': usage_summary,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.exception("Failed to get admin status")
        return jsonify({'error': str(e)}), 500

# Health check endpoints
@app.route('/health')
def health():
    """Comprehensive health check endpoint."""
    try:
        from config.health_checks import run_health_checks, get_overall_health
        
        results = run_health_checks(db_path=db_path, include_optional=True, use_cache=True)
        overall_status = get_overall_health(results)
        
        status_code = 200 if overall_status == 'healthy' else (503 if overall_status == 'unhealthy' else 200)
        
        return jsonify({
            'status': overall_status,
            'checks': {name: result.to_dict() for name, result in results.items()},
            'timestamp': datetime.utcnow().isoformat(),
            'version': os.getenv('RELEASE_VERSION', 'unknown')
        }), status_code
    except Exception as e:
        logger.exception("Health check failed")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 503


@app.route('/health/ready')
def health_ready():
    """Readiness probe for Kubernetes."""
    try:
        from config.health_checks import check_database
        
        result = check_database(db_path)
        if result.status == 'healthy':
            return jsonify({'status': 'ready'}), 200
        else:
            return jsonify({'status': 'not ready', 'reason': result.message}), 503
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return jsonify({'status': 'not ready', 'error': str(e)}), 503


@app.route('/health/live')
def health_live():
    """Liveness probe for Kubernetes."""
    return jsonify({'status': 'alive'}), 200

# Admin endpoints for IP management
@app.route('/api/admin/ip/whitelist', methods=['POST'])
@require_any_role(['Admin'])
@csrf.exempt
def add_whitelist_ip():
    """Add IP to whitelist (Admin only)."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    ip = data.get('ip', '').strip()
    reason = data.get('reason', '').strip()
    
    if not ip:
        return jsonify({'error': 'IP address is required'}), 400
    
    success = add_ip_to_whitelist(ip, reason)
    
    if success:
        user = getattr(request, 'current_user', None)
        if user:
            log_security_event(
                AuditEventType.DATA_MODIFICATION,
                user_id=user.id,
                username=user.username,
                resource_type='ip_filter',
                action='whitelist_add',
                details={'ip': ip, 'reason': reason},
                success=True
            )
        return jsonify({'message': f'IP {ip} added to whitelist'}), 200
    else:
        return jsonify({'error': 'Invalid IP address or CIDR range'}), 400

@app.route('/api/admin/ip/blacklist', methods=['POST'])
@require_any_role(['Admin'])
@csrf.exempt
def add_blacklist_ip():
    """Add IP to blacklist (Admin only)."""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    ip = data.get('ip', '').strip()
    reason = data.get('reason', '').strip()
    
    if not ip:
        return jsonify({'error': 'IP address is required'}), 400
    
    success = add_ip_to_blacklist(ip, reason)
    
    if success:
        user = getattr(request, 'current_user', None)
        if user:
            log_security_event(
                AuditEventType.DATA_MODIFICATION,
                user_id=user.id,
                username=user.username,
                resource_type='ip_filter',
                action='blacklist_add',
                details={'ip': ip, 'reason': reason},
                success=True
            )
        return jsonify({'message': f'IP {ip} added to blacklist'}), 200
    else:
        return jsonify({'error': 'Invalid IP address or CIDR range'}), 400

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
    
    # Run system validation on startup
    try:
        from config.system_validation import validate_system_on_startup
        logger.info("Running system validation...")
        # In production, this will exit on critical failures
        # In development, it will log warnings but continue
        validate_system_on_startup(skip_optional=False)
        logger.info("System validation passed")
    except SystemExit:
        logger.error("System validation failed with critical errors. Exiting.")
        raise
    except Exception as e:
        logger.warning(f"System validation error: {e}")
    
    # Initialize distributed tracing with app
    try:
        from config.tracing_config import init_tracing
        init_tracing(app, service_name='hhs-social-media-scraper')
    except:
        pass
    
    # Start continuous monitoring
    try:
        from config.continuous_monitoring import start_monitoring
        start_monitoring()
        logger.info("Continuous monitoring started")
    except Exception as e:
        logger.warning(f"Could not start continuous monitoring: {e}")
    
    # Set up periodic critical issue checking
    try:
        from config.critical_alerting import alert_manager
        import threading
        import time
        
        def check_critical_issues_periodically():
            """Background thread to check for critical issues every 5 minutes."""
            while True:
                try:
                    alert_manager.check_all()
                except Exception as e:
                    logger.exception("Error checking critical issues")
                time.sleep(300)  # Check every 5 minutes
        
        # Start background thread for critical issue checking
        check_thread = threading.Thread(target=check_critical_issues_periodically, daemon=True)
        check_thread.start()
        logger.info("Critical issue checking thread started")
    except Exception as e:
        logger.warning(f"Could not start critical issue checking: {e}")
    
    app.run(debug=True, port=5000)
