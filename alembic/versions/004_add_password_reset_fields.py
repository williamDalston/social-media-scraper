"""Add password reset fields to users table

Revision ID: 004_password_reset
Revises: 003_add_mfa
Create Date: 2024-01-15 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004_password_reset'
down_revision = '003_add_mfa'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add password reset fields to users table
    op.add_column('users', sa.Column('password_reset_token', sa.String(255), nullable=True))
    op.add_column('users', sa.Column('password_reset_expires', sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Remove password reset fields
    op.drop_column('users', 'password_reset_expires')
    op.drop_column('users', 'password_reset_token')

