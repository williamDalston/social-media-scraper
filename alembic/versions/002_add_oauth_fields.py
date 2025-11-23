"""Add OAuth fields to users table

Revision ID: 002_add_oauth
Revises: 001_initial
Create Date: 2024-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_add_oauth'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add OAuth fields to users table
    op.add_column('users', sa.Column('oauth_provider', sa.String(50), nullable=True))
    op.add_column('users', sa.Column('oauth_id', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('display_name', sa.String(255), nullable=True))
    
    # Make password_hash nullable for OAuth users
    op.alter_column('users', 'password_hash', nullable=True)


def downgrade() -> None:
    # Remove OAuth fields
    op.drop_column('users', 'display_name')
    op.drop_column('users', 'oauth_id')
    op.drop_column('users', 'oauth_provider')
    
    # Make password_hash required again (note: this may fail if OAuth users exist)
    op.alter_column('users', 'password_hash', nullable=False)

