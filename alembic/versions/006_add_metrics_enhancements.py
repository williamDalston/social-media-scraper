"""Add metrics enhancements to dim_account and fact_followers_snapshot

Revision ID: 006_add_metrics_enhancements
Revises: 005_add_is_active
Create Date: 2024-01-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "006_add_metrics_enhancements"
down_revision = "005_add_is_active"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add account metadata fields to dim_account
    op.add_column(
        "dim_account", sa.Column("account_created_date", sa.Date(), nullable=True)
    )
    op.add_column(
        "dim_account", sa.Column("account_category", sa.String(), nullable=True)
    )
    op.add_column("dim_account", sa.Column("bio_text", sa.Text(), nullable=True))
    op.add_column("dim_account", sa.Column("bio_link", sa.String(), nullable=True))
    op.add_column(
        "dim_account", sa.Column("profile_image_url", sa.String(), nullable=True)
    )

    # Add calculated metrics to fact_followers_snapshot
    op.add_column(
        "fact_followers_snapshot",
        sa.Column("engagement_rate", sa.Float(), nullable=True),
    )
    op.add_column(
        "fact_followers_snapshot",
        sa.Column("follower_growth_rate", sa.Float(), nullable=True),
    )
    op.add_column(
        "fact_followers_snapshot",
        sa.Column("follower_growth_absolute", sa.Integer(), nullable=True),
    )
    op.add_column(
        "fact_followers_snapshot", sa.Column("posts_per_day", sa.Float(), nullable=True)
    )

    # Add YouTube-specific video metrics
    op.add_column(
        "fact_followers_snapshot",
        sa.Column("total_video_views", sa.Integer(), nullable=True),
    )
    op.add_column(
        "fact_followers_snapshot",
        sa.Column("average_views_per_video", sa.Float(), nullable=True),
    )

    # Create indexes for new fields
    op.create_index(
        "ix_dim_account_created_date", "dim_account", ["account_created_date"]
    )
    op.create_index(
        "ix_fact_snapshot_engagement_rate",
        "fact_followers_snapshot",
        ["engagement_rate"],
    )
    op.create_index(
        "ix_fact_snapshot_growth_rate",
        "fact_followers_snapshot",
        ["follower_growth_rate"],
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_fact_snapshot_growth_rate", table_name="fact_followers_snapshot")
    op.drop_index(
        "ix_fact_snapshot_engagement_rate", table_name="fact_followers_snapshot"
    )
    op.drop_index("ix_dim_account_created_date", table_name="dim_account")

    # Drop columns from fact_followers_snapshot
    op.drop_column("fact_followers_snapshot", "average_views_per_video")
    op.drop_column("fact_followers_snapshot", "total_video_views")
    op.drop_column("fact_followers_snapshot", "posts_per_day")
    op.drop_column("fact_followers_snapshot", "follower_growth_absolute")
    op.drop_column("fact_followers_snapshot", "follower_growth_rate")
    op.drop_column("fact_followers_snapshot", "engagement_rate")

    # Drop columns from dim_account
    op.drop_column("dim_account", "profile_image_url")
    op.drop_column("dim_account", "bio_link")
    op.drop_column("dim_account", "bio_text")
    op.drop_column("dim_account", "account_category")
    op.drop_column("dim_account", "account_created_date")
