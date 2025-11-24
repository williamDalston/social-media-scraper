import random
import logging
import sys
import os
from datetime import date, timedelta
from sqlalchemy.orm import sessionmaker
from scraper.schema import DimAccount, FactFollowersSnapshot, init_db

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.logging_config import setup_logging, get_logger

# Set up logging if not already configured
try:
    logger = logging.getLogger(__name__)
    if not logger.handlers:
        setup_logging()
    logger = get_logger(__name__)
except:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


def backfill_history(db_path="social_media.db", days_back=365):
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()

    accounts = session.query(DimAccount).all()
    today = date.today()

    logger.info(
        "Starting backfill operation",
        extra={
            "days_back": days_back,
            "account_count": len(accounts),
            "db_path": db_path,
        },
    )

    total_records = 0

    for account in accounts:
        # Base followers 1 year ago
        current_followers = 10000
        if account.org_name == "HHS":
            current_followers = 500000

        # Start from 1 year ago
        start_followers = int(current_followers * 0.8)  # 20% growth over year
        daily_growth = (current_followers - start_followers) / days_back

        current_count = start_followers

        for i in range(days_back):
            target_date = today - timedelta(days=days_back - i)

            # Check if exists
            existing = (
                session.query(FactFollowersSnapshot)
                .filter_by(account_key=account.account_key, snapshot_date=target_date)
                .first()
            )

            if existing:
                continue

            # Add some noise to growth
            noise = random.randint(-5, 15)
            current_count += daily_growth + noise

            # Seasonality for engagement
            is_weekend = target_date.weekday() >= 5
            engagement_multiplier = 0.5 if is_weekend else 1.0

            snapshot = FactFollowersSnapshot(
                account_key=account.account_key,
                snapshot_date=target_date,
                followers_count=int(current_count),
                following_count=random.randint(10, 500),
                posts_count=random.randint(0, 3) if not is_weekend else 0,
                likes_count=int(random.randint(50, 2000) * engagement_multiplier),
                comments_count=int(random.randint(5, 200) * engagement_multiplier),
                shares_count=int(random.randint(10, 500) * engagement_multiplier),
                engagements_total=0,
            )
            snapshot.engagements_total = (
                snapshot.likes_count + snapshot.comments_count + snapshot.shares_count
            )

            session.add(snapshot)
            total_records += 1

    session.commit()
    logger.info(
        "Backfill operation complete",
        extra={
            "total_records_added": total_records,
            "days_back": days_back,
            "account_count": len(accounts),
        },
    )
    session.close()


if __name__ == "__main__":
    backfill_history()
