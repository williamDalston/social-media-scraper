"""
Accounts API namespace.

Endpoints for managing social media accounts.
"""

from flask_restx import Namespace, Resource, fields
from flask import request
from sqlalchemy.orm import sessionmaker
from scraper.schema import DimAccount, init_db
import io
import csv
import os
from api.errors import BadRequestError, ValidationError
from api.schemas import AccountSchema, CSVUploadResponseSchema
from api.validators import validate_file_upload, serialize_response
from auth.decorators import require_any_role

ns = Namespace('accounts', description='Account management operations')

# Flask-RESTX models for documentation
upload_response_model = ns.model('UploadResponse', {
    'message': fields.String(description='Response message'),
    'count': fields.Integer(description='Number of accounts added', required=False)
})

error_model = ns.model('Error', {
    'error': fields.Nested(ns.model('ErrorDetail', {
        'code': fields.String(description='Error code'),
        'message': fields.String(description='Error message'),
        'details': fields.Raw(description='Additional error details')
    }))
})

account_model = ns.model('Account', {
    'account_key': fields.Integer(description='Account ID'),
    'platform': fields.String(description='Social media platform'),
    'handle': fields.String(description='Account handle'),
    'org_name': fields.String(description='Organization name'),
    'org_id': fields.String(description='Organization ID'),
    'account_display_name': fields.String(description='Display name'),
    'account_url': fields.String(description='Account URL'),
    'is_core_account': fields.Boolean(description='Is core account'),
    'account_type': fields.String(description='Account type')
})

# Helper function
def get_db_session():
    db_path = os.getenv('DATABASE_PATH', 'social_media.db')
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    return Session()


@ns.route('/upload')
@ns.doc(security='Bearer Auth')
class Upload(Resource):
    """Upload accounts via CSV file."""
    
    upload_parser = ns.parser()
    upload_parser.add_argument('file', type='file', location='files', required=True,
                              help='CSV file with columns: Platform, Handle, Organization')
    
    @ns.doc('upload_csv')
    @ns.expect(upload_parser)
    @ns.marshal_with(upload_response_model)
    @ns.response(200, 'Success')
    @ns.response(400, 'Bad Request', error_model)
    @ns.response(401, 'Unauthorized', error_model)
    @ns.response(403, 'Forbidden', error_model)
    @require_any_role(['Admin', 'Editor'])
    @validate_file_upload(allowed_extensions=['csv'], max_size=10 * 1024 * 1024)  # 10MB
    def post(self):
        """
        Upload accounts from CSV file.
        
        Expected CSV format:
        - Platform: Social media platform (X, Instagram, Facebook, etc.)
        - Handle: Account handle/username
        - Organization: Organization name
        
        Only Admin and Editor roles can upload accounts.
        """
        if 'file' not in request.files:
            raise BadRequestError('No file part')
        
        file = request.validated_file if hasattr(request, 'validated_file') else request.files['file']
        
        if file.filename == '':
            raise BadRequestError('No selected file')
        
        # Validate file extension
        if not file.filename.lower().endswith('.csv'):
            raise BadRequestError('File must be a CSV file')
        
        try:
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_input = csv.DictReader(stream)
            
            session = get_db_session()
            count = 0
            errors = []
            
            try:
                for row_num, row in enumerate(csv_input, start=2):  # Start at 2 (1 is header)
                    platform = row.get('Platform', '').strip()
                    handle = row.get('Handle', '').strip()
                    org = row.get('Organization', '').strip()
                    
                    if not platform or not handle:
                        errors.append(f'Row {row_num}: Missing Platform or Handle')
                        continue
                    
                    # Validate platform
                    valid_platforms = ['X', 'Instagram', 'Facebook', 'LinkedIn', 'YouTube', 'Truth Social']
                    if platform not in valid_platforms:
                        errors.append(f'Row {row_num}: Invalid platform "{platform}". Valid platforms: {", ".join(valid_platforms)}"')
                        continue
                    
                    # Check if exists
                    existing = session.query(DimAccount).filter_by(
                        platform=platform, handle=handle
                    ).first()
                    
                    if not existing:
                        account = DimAccount(
                            platform=platform,
                            handle=handle,
                            org_name=org,
                            account_display_name=f"{org} on {platform}",
                            account_url=f"https://{platform.lower()}.com/{handle}"
                        )
                        session.add(account)
                        count += 1
                
                session.commit()
                
                message = f'Successfully added {count} accounts'
                if errors:
                    message += f'. {len(errors)} rows had errors: {"; ".join(errors[:5])}'
                
                return {
                    'message': message,
                    'count': count
                }
            except Exception as e:
                session.rollback()
                raise BadRequestError(f'Error processing CSV: {str(e)}')
            finally:
                session.close()
        except UnicodeDecodeError:
            raise BadRequestError('File encoding error. Please ensure the file is UTF-8 encoded.')
        except Exception as e:
            raise BadRequestError(f'Error reading file: {str(e)}')


@ns.route('')
@ns.doc(security='Bearer Auth')
class AccountList(Resource):
    """List all accounts with pagination."""
    
    @ns.doc('list_accounts')
    @ns.param('page', 'Page number', _in='query', type='integer', default=1)
    @ns.param('per_page', 'Items per page', _in='query', type='integer', default=100, maximum=500)
    @ns.param('platform', 'Filter by platform', _in='query', type='string', enum=['X', 'Instagram', 'Facebook', 'LinkedIn', 'YouTube', 'Truth Social'])
    @ns.marshal_list_with(account_model)
    @ns.response(200, 'Success')
    @ns.response(401, 'Unauthorized', error_model)
    @require_any_role(['Admin', 'Editor', 'Viewer'])
    def get(self):
        """
        Get list of all accounts with pagination.
        
        Returns all social media accounts in the system with optional filtering by platform.
        """
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 100, type=int)
        platform_filter = request.args.get('platform', type=str)
        
        # Validate pagination parameters
        page = max(1, page)
        per_page = min(max(1, per_page), 500)  # Limit between 1 and 500
        
        session = get_db_session()
        
        try:
            # Base query
            query = session.query(DimAccount)
            
            # Apply platform filter if provided
            if platform_filter:
                query = query.filter(DimAccount.platform == platform_filter)
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            accounts = query.order_by(
                DimAccount.platform,
                DimAccount.handle
            ).offset((page - 1) * per_page).limit(per_page).all()
            
            data = []
            for account in accounts:
                data.append({
                    'account_key': account.account_key,
                    'platform': account.platform,
                    'handle': account.handle,
                    'org_name': account.org_name,
                    'org_id': account.org_id,
                    'account_display_name': account.account_display_name,
                    'account_url': account.account_url,
                    'is_core_account': account.is_core_account,
                    'account_type': account.account_type
                })
            
            # Add pagination metadata to response headers
            from flask import make_response
            response = make_response(data)
            response.headers['X-Page'] = str(page)
            response.headers['X-Per-Page'] = str(per_page)
            response.headers['X-Total'] = str(total)
            response.headers['X-Total-Pages'] = str((total + per_page - 1) // per_page if total > 0 else 0)
            response.headers['X-API-Version'] = '1.0'
            
            return response
        finally:
            session.close()

