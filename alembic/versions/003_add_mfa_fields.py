"""Add MFA fields to users table

Revision ID: 003_add_mfa
Revises: 002_add_oauth
Create Date: 2024-01-15 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003_add_mfa'
down_revision = '002_add_oauth'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add MFA fields to users table
    op.add_column('users', sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('mfa_secret', sa.String(32), nullable=True))
    op.add_column('users', sa.Column('backup_codes', sa.String(500), nullable=True))


def downgrade() -> None:
    # Remove MFA fields
    op.drop_column('users', 'backup_codes')
    op.drop_column('users', 'mfa_secret')
    op.drop_column('users', 'mfa_enabled')

