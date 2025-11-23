"""
Marshmallow schemas for request/response validation and serialization.
"""

from marshmallow import Schema, fields, validate, validates_schema, ValidationError as MarshmallowValidationError
from datetime import datetime


class ErrorResponseSchema(Schema):
    """Schema for error responses."""
    
    error = fields.Dict(required=True)
    error_code = fields.Str()
    error_message = fields.Str()
    error_details = fields.Dict()


class AccountSchema(Schema):
    """Schema for account data."""
    
    account_key = fields.Int(dump_only=True)
    platform = fields.Str(required=True, validate=validate.OneOf(['X', 'Instagram', 'Facebook', 'LinkedIn', 'YouTube', 'Truth Social']))
    handle = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    account_id = fields.Str(allow_none=True)
    account_display_name = fields.Str(allow_none=True)
    account_url = fields.Str(allow_none=True)
    org_id = fields.Str(allow_none=True)
    org_name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    owner_team = fields.Str(allow_none=True)
    is_core_account = fields.Bool(missing=False)
    account_type = fields.Str(allow_none=True, validate=validate.OneOf(['official dept', 'sub-brand', 'campaign', 'leader/personal']))
    is_leader_account = fields.Bool(missing=False)
    requires_preclearance = fields.Bool(missing=False)
    sensitivity_level = fields.Str(allow_none=True, validate=validate.OneOf(['Low', 'Medium', 'High']))
    verified_status = fields.Str(allow_none=True)


class AccountCreateSchema(Schema):
    """Schema for creating a new account."""
    
    platform = fields.Str(required=True, validate=validate.OneOf(['X', 'Instagram', 'Facebook', 'LinkedIn', 'YouTube', 'Truth Social']))
    handle = fields.Str(required=True, validate=validate.Length(min=1, max=100))
    org_name = fields.Str(required=True, validate=validate.Length(min=1, max=200))
    org_id = fields.Str(allow_none=True)
    owner_team = fields.Str(allow_none=True)
    is_core_account = fields.Bool(missing=False)
    account_type = fields.Str(allow_none=True)


class AccountUpdateSchema(Schema):
    """Schema for updating an account."""
    
    platform = fields.Str(validate=validate.OneOf(['X', 'Instagram', 'Facebook', 'LinkedIn', 'YouTube', 'Truth Social']))
    handle = fields.Str(validate=validate.Length(min=1, max=100))
    org_name = fields.Str(validate=validate.Length(min=1, max=200))
    org_id = fields.Str(allow_none=True)
    owner_team = fields.Str(allow_none=True)
    is_core_account = fields.Bool()
    account_type = fields.Str(allow_none=True)


class MetricsSnapshotSchema(Schema):
    """Schema for follower snapshot metrics."""
    
    snapshot_id = fields.Int(dump_only=True)
    account_key = fields.Int(required=True)
    snapshot_date = fields.Date(required=True)
    followers_count = fields.Int(allow_none=True)
    following_count = fields.Int(allow_none=True)
    listed_count = fields.Int(allow_none=True)
    subscribers_count = fields.Int(allow_none=True)
    posts_count = fields.Int(allow_none=True)
    stories_count = fields.Int(allow_none=True)
    videos_count = fields.Int(allow_none=True)
    live_streams_count = fields.Int(allow_none=True)
    likes_count = fields.Int(allow_none=True)
    comments_count = fields.Int(allow_none=True)
    shares_count = fields.Int(allow_none=True)
    video_views = fields.Int(allow_none=True)
    engagements_total = fields.Int(allow_none=True)


class SummaryItemSchema(Schema):
    """Schema for summary response items."""
    
    platform = fields.Str()
    handle = fields.Str()
    followers = fields.Int(attribute='followers_count', allow_none=True)
    engagement = fields.Int(attribute='engagements_total', allow_none=True)
    posts = fields.Int(attribute='posts_count', allow_none=True)


class HistoryDataSchema(Schema):
    """Schema for history response."""
    
    dates = fields.List(fields.Date(), required=True)
    followers = fields.List(fields.Int(allow_none=True), required=True)
    engagement = fields.List(fields.Int(allow_none=True), required=True)


class GridRowSchema(Schema):
    """Schema for grid data rows."""
    
    platform = fields.Str()
    handle = fields.Str()
    org_name = fields.Str()
    snapshot_date = fields.Date()
    followers_count = fields.Int(allow_none=True)
    engagements_total = fields.Int(allow_none=True)
    posts_count = fields.Int(allow_none=True)
    likes_count = fields.Int(allow_none=True)
    comments_count = fields.Int(allow_none=True)
    shares_count = fields.Int(allow_none=True)


class ScraperRunRequestSchema(Schema):
    """Schema for scraper run request."""
    
    mode = fields.Str(validate=validate.OneOf(['simulated', 'real']), missing='simulated')


class CSVUploadResponseSchema(Schema):
    """Schema for CSV upload response."""
    
    message = fields.Str(required=True)
    count = fields.Int(allow_none=True)


class SuccessResponseSchema(Schema):
    """Schema for success responses."""
    
    message = fields.Str(required=True)
    data = fields.Dict(allow_none=True)


class PaginationSchema(Schema):
    """Schema for pagination metadata."""
    
    page = fields.Int(missing=1, validate=validate.Range(min=1))
    per_page = fields.Int(missing=10, validate=validate.Range(min=1, max=100))
    total = fields.Int(dump_only=True)
    pages = fields.Int(dump_only=True)


class PaginatedResponseSchema(Schema):
    """Schema for paginated responses."""
    
    items = fields.List(fields.Dict(), required=True)
    pagination = fields.Nested(PaginationSchema, required=True)


# Platform and handle path parameters
class PlatformHandleParamsSchema(Schema):
    """Schema for platform and handle path parameters."""
    
    platform = fields.Str(required=True, validate=validate.OneOf(['X', 'Instagram', 'Facebook', 'LinkedIn', 'YouTube', 'Truth Social']))
    handle = fields.Str(required=True, validate=validate.Length(min=1, max=100))


# Pagination schemas
class PaginationQuerySchema(Schema):
    """Schema for pagination query parameters."""
    
    page = fields.Int(missing=1, validate=validate.Range(min=1))
    per_page = fields.Int(missing=10, validate=validate.Range(min=1, max=500))


class PaginatedResponseSchema(Schema):
    """Schema for paginated responses."""
    
    items = fields.List(fields.Dict(), required=True)
    pagination = fields.Dict(required=True, keys=fields.Str(), values=fields.Int())


# Auth schemas
class LoginSchema(Schema):
    """Schema for login request."""
    
    username = fields.Str(required=True, validate=validate.Length(min=1))
    password = fields.Str(required=True, validate=validate.Length(min=1))


class RegisterSchema(Schema):
    """Schema for registration request."""
    
    username = fields.Str(required=True, validate=validate.Length(min=3, max=50))
    email = fields.Email(required=True)
    password = fields.Str(required=True, validate=validate.Length(min=8, max=128))
    role = fields.Str(validate=validate.OneOf(['Admin', 'Editor', 'Viewer']), missing='Viewer')


class RefreshTokenSchema(Schema):
    """Schema for refresh token request."""
    
    refresh_token = fields.Str(required=True, validate=validate.Length(min=1))

