"""Add is_active field to dim_account

Revision ID: 005_add_is_active
Revises: 004_add_password_reset_fields
Create Date: 2024-01-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "005_add_is_active"
down_revision = "004_password_reset"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_active column to dim_account table
    op.add_column(
        "dim_account",
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="1"),
    )

    # Create index for is_active for better query performance
    op.create_index("ix_dim_account_is_active", "dim_account", ["is_active"])


def downgrade() -> None:
    # Drop index
    op.drop_index("ix_dim_account_is_active", table_name="dim_account")

    # Drop column
    op.drop_column("dim_account", "is_active")
