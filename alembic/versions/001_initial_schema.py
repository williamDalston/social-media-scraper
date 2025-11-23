"""Initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create dim_account table
    op.create_table(
        'dim_account',
        sa.Column('account_key', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(), nullable=False),
        sa.Column('handle', sa.String(), nullable=False),
        sa.Column('account_id', sa.String(), nullable=True),
        sa.Column('account_display_name', sa.String(), nullable=True),
        sa.Column('account_url', sa.String(), nullable=True),
        sa.Column('org_id', sa.String(), nullable=True),
        sa.Column('org_name', sa.String(), nullable=True),
        sa.Column('owner_team', sa.String(), nullable=True),
        sa.Column('is_core_account', sa.Boolean(), nullable=True, server_default='0'),
        sa.Column('account_type', sa.String(), nullable=True),
        sa.Column('is_leader_account', sa.Boolean(), nullable=True, server_default='0'),
        sa.Column('requires_preclearance', sa.Boolean(), nullable=True, server_default='0'),
        sa.Column('sensitivity_level', sa.String(), nullable=True),
        sa.Column('verified_status', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('account_key')
    )
    
    # Create fact_followers_snapshot table
    op.create_table(
        'fact_followers_snapshot',
        sa.Column('snapshot_id', sa.Integer(), nullable=False),
        sa.Column('account_key', sa.Integer(), nullable=False),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('followers_count', sa.Integer(), nullable=True),
        sa.Column('following_count', sa.Integer(), nullable=True),
        sa.Column('listed_count', sa.Integer(), nullable=True),
        sa.Column('subscribers_count', sa.Integer(), nullable=True),
        sa.Column('posts_count', sa.Integer(), nullable=True),
        sa.Column('stories_count', sa.Integer(), nullable=True),
        sa.Column('videos_count', sa.Integer(), nullable=True),
        sa.Column('live_streams_count', sa.Integer(), nullable=True),
        sa.Column('likes_count', sa.Integer(), nullable=True),
        sa.Column('comments_count', sa.Integer(), nullable=True),
        sa.Column('shares_count', sa.Integer(), nullable=True),
        sa.Column('video_views', sa.Integer(), nullable=True),
        sa.Column('engagements_total', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['account_key'], ['dim_account.account_key'], ),
        sa.PrimaryKeyConstraint('snapshot_id')
    )
    
    # Create fact_social_post table
    op.create_table(
        'fact_social_post',
        sa.Column('post_key', sa.Integer(), nullable=False),
        sa.Column('account_key', sa.Integer(), nullable=False),
        sa.Column('platform', sa.String(), nullable=True),
        sa.Column('post_id', sa.String(), nullable=False),
        sa.Column('post_url', sa.String(), nullable=True),
        sa.Column('post_datetime_utc', sa.DateTime(), nullable=True),
        sa.Column('post_type', sa.String(), nullable=True),
        sa.Column('caption_text', sa.Text(), nullable=True),
        sa.Column('hashtags', sa.Text(), nullable=True),
        sa.Column('mentions', sa.Text(), nullable=True),
        sa.Column('is_reply', sa.Boolean(), nullable=True, server_default='0'),
        sa.Column('is_retweet', sa.Boolean(), nullable=True, server_default='0'),
        sa.Column('likes_count', sa.Integer(), nullable=True),
        sa.Column('comments_count', sa.Integer(), nullable=True),
        sa.Column('shares_count', sa.Integer(), nullable=True),
        sa.Column('views_count', sa.Integer(), nullable=True),
        sa.Column('impressions', sa.Integer(), nullable=True),
        sa.Column('clicks', sa.Integer(), nullable=True),
        sa.Column('topic_primary', sa.String(), nullable=True),
        sa.Column('topic_secondary', sa.String(), nullable=True),
        sa.Column('priority_area', sa.String(), nullable=True),
        sa.Column('tone', sa.String(), nullable=True),
        sa.Column('has_sensitive_topic_flag', sa.Boolean(), nullable=True, server_default='0'),
        sa.Column('fact_checked', sa.Boolean(), nullable=True, server_default='0'),
        sa.ForeignKeyConstraint(['account_key'], ['dim_account.account_key'], ),
        sa.PrimaryKeyConstraint('post_key')
    )
    
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=80), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False, server_default='Viewer'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create job table
    op.create_table(
        'job',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.String(), nullable=False),
        sa.Column('job_type', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='pending'),
        sa.Column('progress', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('account_key', sa.Integer(), nullable=True),
        sa.Column('platform', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_dim_account_platform', 'dim_account', ['platform'])
    op.create_index('ix_dim_account_handle', 'dim_account', ['handle'])
    op.create_index('ix_fact_followers_snapshot_account_key', 'fact_followers_snapshot', ['account_key'])
    op.create_index('ix_fact_followers_snapshot_snapshot_date', 'fact_followers_snapshot', ['snapshot_date'])
    op.create_index('ix_fact_social_post_account_key', 'fact_social_post', ['account_key'])
    op.create_index('ix_fact_social_post_platform', 'fact_social_post', ['platform'])
    op.create_index('ix_fact_social_post_post_datetime_utc', 'fact_social_post', ['post_datetime_utc'])
    op.create_index('ix_users_username', 'users', ['username'])
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_job_job_id', 'job', ['job_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_job_job_id', table_name='job')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_username', table_name='users')
    op.drop_index('ix_fact_social_post_post_datetime_utc', table_name='fact_social_post')
    op.drop_index('ix_fact_social_post_platform', table_name='fact_social_post')
    op.drop_index('ix_fact_social_post_account_key', table_name='fact_social_post')
    op.drop_index('ix_fact_followers_snapshot_snapshot_date', table_name='fact_followers_snapshot')
    op.drop_index('ix_fact_followers_snapshot_account_key', table_name='fact_followers_snapshot')
    op.drop_index('ix_dim_account_handle', table_name='dim_account')
    op.drop_index('ix_dim_account_platform', table_name='dim_account')
    
    # Drop tables
    op.drop_table('job')
    op.drop_table('users')
    op.drop_table('fact_social_post')
    op.drop_table('fact_followers_snapshot')
    op.drop_table('dim_account')

