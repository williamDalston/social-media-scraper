"""
Script to add database indexes for performance optimization.
Run this script to add indexes to the existing database.
"""
import sqlite3
import os
import sys


def add_indexes(db_path="social_media.db"):
    """
    Add performance indexes to the database.

    Args:
        db_path: Path to the SQLite database file
    """
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    indexes = [
        # DimAccount indexes
        (
            "CREATE INDEX IF NOT EXISTS ix_dim_account_platform ON dim_account(platform)",
        ),
        ("CREATE INDEX IF NOT EXISTS ix_dim_account_handle ON dim_account(handle)",),
        (
            "CREATE INDEX IF NOT EXISTS ix_dim_account_platform_handle ON dim_account(platform, handle)",
        ),
        # FactFollowersSnapshot indexes
        (
            "CREATE INDEX IF NOT EXISTS ix_fact_snapshot_account_key ON fact_followers_snapshot(account_key)",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_fact_snapshot_snapshot_date ON fact_followers_snapshot(snapshot_date)",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_fact_snapshot_account_date ON fact_followers_snapshot(account_key, snapshot_date)",
        ),
        # FactSocialPost indexes (if table exists)
        (
            "CREATE INDEX IF NOT EXISTS ix_fact_post_account_key ON fact_social_post(account_key)",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_fact_post_datetime ON fact_social_post(post_datetime_utc)",
        ),
        (
            "CREATE INDEX IF NOT EXISTS ix_fact_post_account_datetime ON fact_social_post(account_key, post_datetime_utc)",
        ),
    ]

    print("Adding database indexes...")
    for (index_sql,) in indexes:
        try:
            cursor.execute(index_sql)
            print(f"✓ Created index: {index_sql.split('ON')[1].strip()}")
        except sqlite3.OperationalError as e:
            # Table might not exist yet, skip
            if "no such table" in str(e).lower():
                print(
                    f"⚠ Skipped (table doesn't exist): {index_sql.split('ON')[1].strip()}"
                )
            else:
                print(f"✗ Error creating index: {e}")

    conn.commit()
    conn.close()
    print("\n✓ Database indexes added successfully!")


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "social_media.db"
    add_indexes(db_path)
