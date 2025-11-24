#!/usr/bin/env python3
"""Export all data to CSV for static hosting."""
import sys
import os
import csv
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.schema import init_db, DimAccount, FactFollowersSnapshot
from sqlalchemy.orm import sessionmaker


def export_to_csv(db_path="social_media.db", output_file="hhs_social_media_data.csv"):
    """Export all data to CSV."""
    # Ensure output directory exists
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        query = (
            session.query(
                DimAccount.platform,
                DimAccount.handle,
                DimAccount.org_name,
                FactFollowersSnapshot.snapshot_date,
                FactFollowersSnapshot.followers_count,
                FactFollowersSnapshot.following_count,
                FactFollowersSnapshot.posts_count,
                FactFollowersSnapshot.engagements_total,
                FactFollowersSnapshot.likes_count,
                FactFollowersSnapshot.comments_count,
                FactFollowersSnapshot.shares_count,
            )
            .join(
                FactFollowersSnapshot,
                DimAccount.account_key == FactFollowersSnapshot.account_key,
            )
            .order_by(
                FactFollowersSnapshot.snapshot_date.desc(),
                DimAccount.platform,
                DimAccount.handle,
            )
            .all()
        )

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "Platform",
                    "Handle",
                    "Organization",
                    "Date",
                    "Followers",
                    "Following",
                    "Posts",
                    "Engagement Total",
                    "Likes",
                    "Comments",
                    "Shares",
                ]
            )

            for row in query:
                writer.writerow(
                    [
                        row.platform,
                        row.handle,
                        row.org_name,
                        row.snapshot_date.isoformat() if row.snapshot_date else "",
                        row.followers_count or 0,
                        row.following_count or 0,
                        row.posts_count or 0,
                        row.engagements_total or 0,
                        row.likes_count or 0,
                        row.comments_count or 0,
                        row.shares_count or 0,
                    ]
                )

        print(f"✅ Exported {len(query)} records to {output_file}")
        return len(query)

    finally:
        session.close()


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "social_media.db"
    output_file = sys.argv[2] if len(sys.argv) > 2 else "hhs_social_media_data.csv"
    export_to_csv(db_path, output_file)
