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
        try:
            latest_date = session.query(
                func.max(FactFollowersSnapshot.snapshot_date)
            ).scalar()
        except Exception as query_error:
            logger.error(f"Error querying latest snapshot date: {query_error}")
            from api.errors import InternalServerError
            raise InternalServerError("Failed to retrieve summary data")
        
        if not latest_date:
            return jsonify([])
        
        # Optimized query with eager loading to avoid N+1
        try:
            results = session.query(DimAccount, FactFollowersSnapshot).join(
                FactFollowersSnapshot,
                DimAccount.account_key == FactFollowersSnapshot.account_key
            ).filter(
                FactFollowersSnapshot.snapshot_date == latest_date
            ).options(
                joinedload(DimAccount)  # Eager load account data
            ).all()
        except Exception as query_error:
            logger.error(f"Error querying summary data: {query_error}")
            from api.errors import InternalServerError
            raise InternalServerError("Failed to retrieve summary data")
        
        data = []
        for account, snapshot in results:
            try:
                data.append({
                    'platform': account.platform or '',
                    'handle': account.handle or '',
                    'org_name': account.org_name or '',
                    'followers': int(snapshot.followers_count or 0),
                    'engagement': int(snapshot.engagements_total or 0),
                    'posts': int(snapshot.posts_count or 0)
                })
            except (ValueError, TypeError, AttributeError) as data_error:
                logger.warning(
                    f"Error processing account data: {data_error}",
                    extra={'account_key': getattr(account, 'account_key', None)}
                )
                # Skip this account but continue processing others
                continue
        
        return jsonify(data)
    except Exception as e:
        logger.exception("Error in api_summary endpoint")
        from api.errors import InternalServerError
        if isinstance(e, InternalServerError):
            raise
        raise InternalServerError(f"Failed to retrieve summary: {str(e)}")
    finally:
        if session:
            try:
                session.close()
            except Exception as close_error:
                logger.error(f"Error closing session in api_summary: {close_error}")

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
        try:
            account = session.query(DimAccount).filter(
                func.lower(DimAccount.platform) == func.lower(platform),
                func.lower(DimAccount.handle) == func.lower(handle)
            ).first()
        except Exception as query_error:
            logger.error(f"Error querying account: {query_error}", extra={'platform': platform, 'handle': handle})
            from api.errors import InternalServerError
            raise InternalServerError("Failed to retrieve account")
        
        if not account:
            from api.errors import NotFoundError
            raise NotFoundError('Account', f"{platform}/{handle}")
        
        # Optimized query - use index on account_key
        try:
            history = session.query(FactFollowersSnapshot).filter_by(
                account_key=account.account_key
            ).order_by(FactFollowersSnapshot.snapshot_date).all()
        except Exception as query_error:
            logger.error(f"Error querying history: {query_error}", extra={'account_key': account.account_key})
            from api.errors import InternalServerError
            raise InternalServerError("Failed to retrieve account history")
        
        try:
            data = {
                'dates': [h.snapshot_date.isoformat() if h.snapshot_date else '' for h in history],
                'followers': [int(h.followers_count or 0) for h in history],
                'engagement': [int(h.engagements_total or 0) for h in history]
            }
        except (ValueError, TypeError, AttributeError) as data_error:
            logger.error(f"Error processing history data: {data_error}", extra={'account_key': account.account_key})
            from api.errors import InternalServerError
            raise InternalServerError("Failed to process history data")
        
        return jsonify(data)
    except Exception as e:
        logger.exception("Error in api_history endpoint", extra={'platform': platform, 'handle': handle})
        from api.errors import InternalServerError, NotFoundError
        if isinstance(e, (InternalServerError, NotFoundError)):
            raise
        raise InternalServerError(f"Failed to retrieve history: {str(e)}")
    finally:
        if session:
            try:
                session.close()
            except Exception as close_error:
                logger.error(f"Error closing session in api_history: {close_error}")

@app.route('/api/download')
@limiter.limit("10 per hour")
@require_auth
@track_performance('api_download')
def download_csv():
    """Download all data as CSV. Not cached as it's a download endpoint."""
    session = None
    output = None
    
    try:
        session = get_db_session()
        
        # Optimized query with eager loading
        try:
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
        except Exception as query_error:
            logger.error(f"Error querying data for CSV download: {query_error}")
            from api.errors import InternalServerError
            raise InternalServerError("Failed to retrieve data for download")
        
        # Convert to CSV
        try:
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Platform', 'Handle', 'Organization', 'Date', 'Followers', 'Engagement Total', 'Posts', 'Likes', 'Comments', 'Shares'])
            
            for row in query:
                try:
                    # Safely convert row data
                    safe_row = [
                        str(row.platform) if row.platform else '',
                        str(row.handle) if row.handle else '',
                        str(row.org_name) if row.org_name else '',
                        row.snapshot_date.isoformat() if row.snapshot_date else '',
                        int(row.followers_count or 0),
                        int(row.engagements_total or 0),
                        int(row.posts_count or 0),
                        int(row.likes_count or 0),
                        int(row.comments_count or 0),
                        int(row.shares_count or 0)
                    ]
                    writer.writerow(safe_row)
                except (ValueError, TypeError, AttributeError) as row_error:
                    logger.warning(f"Error processing row for CSV: {row_error}")
                    # Skip this row but continue
                    continue
            
            output.seek(0)
        except Exception as csv_error:
            logger.error(f"Error creating CSV: {csv_error}")
            from api.errors import InternalServerError
            raise InternalServerError("Failed to generate CSV file")
        
        try:
            csv_bytes = output.getvalue().encode('utf-8')
        except UnicodeEncodeError as encode_error:
            logger.error(f"Error encoding CSV: {encode_error}")
            from api.errors import InternalServerError
            raise InternalServerError("Failed to encode CSV file")
        
        return send_file(
            io.BytesIO(csv_bytes),
            mimetype='text/csv',
            as_attachment=True,
            download_name='hhs_social_media_data.csv'
        )
    except Exception as e:
        logger.exception("Error in download_csv endpoint")
        from api.errors import InternalServerError, APIError
        if isinstance(e, APIError):
            raise
        raise InternalServerError(f"Failed to generate download: {str(e)}")
    finally:
        if output:
            try:
                output.close()
            except Exception:
                pass
        if session:
            try:
                session.close()
            except Exception as close_error:
                logger.error(f"Error closing session in download_csv: {close_error}")

@app.route('/api/grid')
@limiter.limit("100 per minute")
@require_auth
@cache.cached(timeout=300, key_prefix='grid')  # 5 minutes cache
@track_performance('api_grid')
def api_grid():
    """Get grid data with pagination. Cached for 5 minutes."""
    session = None
    
    try:
        # Pagination parameters with validation
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 50, type=int)
            
            # Validate pagination parameters
            if page < 1:
                page = 1
            if per_page < 1:
                per_page = 50
            
            # Limit per_page to prevent abuse
            per_page = min(per_page, 1000)
            per_page = max(per_page, 1)
        except (ValueError, TypeError) as param_error:
            logger.warning(f"Invalid pagination parameters: {param_error}")
            page = 1
            per_page = 50
        
        session = get_db_session()
        
        # Base query
        try:
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
        except Exception as query_error:
            logger.error(f"Error building grid query: {query_error}")
            from api.errors import InternalServerError
            raise InternalServerError("Failed to build query")
        
        # Get total count
        try:
            total = base_query.count()
        except Exception as count_error:
            logger.error(f"Error counting grid results: {count_error}")
            from api.errors import InternalServerError
            raise InternalServerError("Failed to count results")
        
        # Apply pagination
        try:
            paginated_query = base_query.offset((page - 1) * per_page).limit(per_page)
            results = paginated_query.all()
        except Exception as pagination_error:
            logger.error(f"Error applying pagination: {pagination_error}")
            from api.errors import InternalServerError
            raise InternalServerError("Failed to paginate results")
        
        # Process results
        data = []
        for row in results:
            try:
                data.append([
                    str(row.platform) if row.platform else '',
                    str(row.handle) if row.handle else '',
                    str(row.org_name) if row.org_name else '',
                    row.snapshot_date.isoformat() if row.snapshot_date else '',
                    int(row.followers_count or 0),
                    int(row.engagements_total or 0),
                    int(row.posts_count or 0),
                    int(row.likes_count or 0),
                    int(row.comments_count or 0),
                    int(row.shares_count or 0)
                ])
            except (ValueError, TypeError, AttributeError) as row_error:
                logger.warning(f"Error processing grid row: {row_error}")
                # Skip this row but continue
                continue
        
        return jsonify({
            'data': data,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page if total > 0 else 0
            }
        })
    except Exception as e:
        logger.exception("Error in api_grid endpoint")
        from api.errors import InternalServerError, APIError
        if isinstance(e, APIError):
            raise
        raise InternalServerError(f"Failed to retrieve grid data: {str(e)}")
    finally:
        if session:
            try:
                session.close()
            except Exception as close_error:
                logger.error(f"Error closing session in api_grid: {close_error}")

def process_csv_data(csv_data, user=None):
    """Process CSV data (from file or text) and add accounts."""
    session = None
    
    try:
        # Validate input
        if not csv_data:
            return None, "No CSV data provided", 0
        
        # Validate CSV file (type, size, content)
        try:
            if isinstance(csv_data, bytes):
                csv_bytes = csv_data
            else:
                csv_bytes = csv_data.encode('utf-8')
        except (UnicodeEncodeError, AttributeError) as encode_error:
            return None, f"Error encoding CSV data: {encode_error}", 0
        
        try:
            is_valid, error_message, validated_rows = validate_csv_file(csv_bytes, max_size_mb=10)
        except Exception as validation_error:
            logger.error(f"Error validating CSV file: {validation_error}")
            return None, f"Error validating CSV file: {validation_error}", 0
        
        if not is_valid:
            return None, error_message or "CSV validation failed", 0
        
        if not validated_rows:
            return None, "No valid rows found in CSV", 0
        
        # Process validated rows
        session = get_db_session()
        count = 0
        errors = []
        
        try:
            for row_num, row in enumerate(validated_rows, start=1):
                try:
                    platform = row.get('Platform', '').strip()
                    handle = row.get('Handle', '').strip()
                    org = row.get('Organization', '').strip()
                    
                    # Validate required fields
                    if not platform:
                        errors.append(f"Row {row_num}: Missing Platform")
                        continue
                    if not handle:
                        errors.append(f"Row {row_num}: Missing Handle")
                        continue
                    
                    # Sanitize organization name
                    try:
                        org = sanitize_string(org, 255)
                    except Exception as sanitize_error:
                        logger.warning(f"Error sanitizing org name for row {row_num}: {sanitize_error}")
                        org = org[:255] if org else ''
                    
                    # Check if exists - optimized query with case-insensitive matching
                    try:
                        existing = session.query(DimAccount).filter(
                            func.lower(DimAccount.platform) == func.lower(platform),
                            func.lower(DimAccount.handle) == func.lower(handle)
                        ).first()
                    except Exception as query_error:
                        logger.error(f"Error querying existing account: {query_error}", extra={'row_num': row_num})
                        errors.append(f"Row {row_num}: Database query error")
                        continue
                    
                    if not existing:
                        try:
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
                        except Exception as create_error:
                            logger.error(f"Error creating account: {create_error}", extra={'row_num': row_num})
                            errors.append(f"Row {row_num}: Error creating account")
                            continue
                except Exception as row_error:
                    logger.error(f"Error processing row {row_num}: {row_error}")
                    errors.append(f"Row {row_num}: {str(row_error)}")
                    continue
            
            # Commit all changes
            try:
                session.commit()
            except Exception as commit_error:
                logger.error(f"Error committing CSV data: {commit_error}")
                session.rollback()
                return None, f"Error saving accounts to database: {commit_error}", count
            
            # Invalidate relevant caches
            try:
                invalidate_summary_cache()
                invalidate_grid_cache()
                invalidate_accounts_list_cache()
            except Exception as cache_error:
                logger.warning(f"Error invalidating caches: {cache_error}")
                # Don't fail if cache invalidation fails
            
            # Log file upload
            if user:
                try:
                    log_security_event(
                        AuditEventType.FILE_UPLOAD,
                        user_id=user.id,
                        username=user.username,
                        resource_type='csv',
                        action='upload',
                        details={'accounts_added': count, 'errors': len(errors)},
                        success=True
                    )
                except Exception as audit_error:
                    logger.warning(f"Error logging security event: {audit_error}")
                    # Don't fail if audit logging fails
            
            # Return success with any errors as warnings
            if errors:
                error_message = f"Processed {count} accounts with {len(errors)} errors: {'; '.join(errors[:5])}"
                return True, error_message, count
            
            return True, None, count
            
        except Exception as process_error:
            logger.exception("Error processing CSV rows")
            if session:
                try:
                    session.rollback()
                except Exception as rollback_error:
                    logger.error(f"Error during rollback: {rollback_error}")
            return None, f"Error processing CSV data: {process_error}", count
            
    except Exception as e:
        logger.exception("Unexpected error in process_csv_data")
        if session:
            try:
                session.rollback()
            except Exception:
                pass
        return None, f"Unexpected error: {str(e)}", 0
    finally:
        if session:
            try:
                session.close()
            except Exception as close_error:
                logger.error(f"Error closing session in process_csv_data: {close_error}")

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

@app.route('/api/job-status/<job_id>', methods=['GET'])
@limiter.limit("100 per minute")
@csrf.exempt
def get_job_status(job_id):
    """Get status and progress of a running job."""
    try:
        from models.job import Job
        from sqlalchemy.orm import sessionmaker
        from scraper.schema import init_db
        import os
        
        db_path = os.getenv('DATABASE_PATH', 'social_media.db')
        engine = init_db(db_path)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            job = session.query(Job).filter_by(job_id=job_id).first()
            
            if not job:
                # Try to get status from Celery directly
                try:
                    from celery_app import celery_app
                    task = celery_app.AsyncResult(job_id)
                    
                    if task.state == 'PENDING':
                        return jsonify({
                            'job_id': job_id,
                            'status': 'pending',
                            'progress': 0,
                            'message': 'Job is pending...'
                        })
                    elif task.state == 'PROGRESS':
                        info = task.info if task.info else {}
                        return jsonify({
                            'job_id': job_id,
                            'status': 'running',
                            'progress': info.get('progress', 0),
                            'message': info.get('message', 'Running...'),
                            'processed': info.get('processed', 0),
                            'total': info.get('total', 0),
                            'speed': info.get('speed', 0),
                            'eta': info.get('eta', '--')
                        })
                    elif task.state == 'SUCCESS':
                        return jsonify({
                            'job_id': job_id,
                            'status': 'completed',
                            'progress': 100,
                            'message': 'Job completed successfully',
                            'result': task.result if task.result else {}
                        })
                    elif task.state == 'FAILURE':
                        return jsonify({
                            'job_id': job_id,
                            'status': 'failed',
                            'progress': 0,
                            'message': str(task.info) if task.info else 'Job failed'
                        })
                except ImportError:
                    pass
            
            # Return database job status
            result_data = {}
            if job.result:
                try:
                    import json
                    result_data = json.loads(job.result) if isinstance(job.result, str) else job.result
                except:
                    result_data = {'raw': str(job.result)}
            
            return jsonify({
                'job_id': job.job_id,
                'status': job.status,
                'progress': job.progress or 0,
                'message': result_data.get('message', job.status),
                'error_message': job.error_message,
                'result': result_data,
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'started_at': job.started_at.isoformat() if job.started_at else None,
                'completed_at': job.completed_at.isoformat() if job.completed_at else None
            })
        finally:
            session.close()
            engine.dispose()
    except Exception as e:
        logger.exception("Error getting job status")
        return jsonify({
            'error': f'Error getting job status: {str(e)}',
            'job_id': job_id
        }), 500


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
        preflight_results = None
    except Exception as e:
        # Don't fail on preflight check errors - log and continue
        logger.warning(f"Pre-flight checks encountered an error (continuing anyway): {str(e)}")
        preflight_results = None
    
    # Use Celery async job for background processing
    try:
        from tasks.scraper_tasks import scrape_all_accounts
        from tasks.utils import create_job_record
        
        # Trigger async Celery task
        task = scrape_all_accounts.delay(mode=mode, db_path=db_path)
        job_id = task.id
        
        # Create job record for tracking
        try:
            create_job_record(job_id, 'scrape_all', db_path=db_path)
        except Exception as e:
            logger.warning(f"Could not create job record: {e}")
        
        return jsonify({
            'message': 'Scraper job started successfully',
            'job_id': job_id,
            'status': 'pending',
            'success': True,
            'account_count': preflight_results.get('account_count', 0) if preflight_results else None,
            'checks': preflight_results.get('checks', []) if preflight_results else None
        })
    except ImportError:
        # Celery not available - fall back to synchronous execution
        logger.warning("Celery not available, running scraper synchronously")
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
                pass
            
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
                    pass
            
            # Invalidate all caches after scraping (if available)
            try:
                invalidate_summary_cache()
                invalidate_grid_cache()
                invalidate_accounts_list_cache()
            except:
                pass
            
            return jsonify({
                'message': 'Scraper finished successfully',
                'execution_time': round(elapsed_time, 2),
                'success': True,
                'job_id': None,  # No job ID for sync execution
                'status': 'completed',
                'account_count': preflight_results.get('account_count', 0) if preflight_results else None,
                'checks': preflight_results.get('checks', []) if preflight_results else None
            })
        except Exception as sync_error:
            logger.exception("Error running scraper synchronously")
            return jsonify({
                'error': f'Error running scraper: {str(sync_error)}',
                'success': False
            }), 500
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

# Error handlers for security and API errors
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429

@app.errorhandler(401)
def unauthorized_handler(e):
    return jsonify({'error': 'Authentication required'}), 401

@app.errorhandler(403)
def forbidden_handler(e):
    return jsonify({'error': 'Insufficient permissions'}), 403

# Global error handler for API errors
@app.errorhandler(Exception)
def global_error_handler(error):
    """Global error handler for unhandled exceptions."""
    from api.errors import APIError
    
    # If it's already an APIError, use its status code and message
    if isinstance(error, APIError):
        response = error.to_dict()
        return jsonify(response), error.status_code
    
    # Log the error with full context
    logger.exception(
        "Unhandled exception in application",
        extra={
            'error_type': type(error).__name__,
            'error_message': str(error),
            'path': request.path if request else None,
            'method': request.method if request else None
        }
    )
    
    # Return generic error message (don't expose internal details)
    return jsonify({
        'error': {
            'code': 'INTERNAL_SERVER_ERROR',
            'message': 'An internal server error occurred. Please try again later.'
        }
    }), 500

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
