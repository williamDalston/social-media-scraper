"""
Metrics calculation utilities for social media snapshots.
Calculates engagement_rate, growth_rate, posting frequency, etc.
"""

import logging
from typing import Dict, Any, Optional
from datetime import date, timedelta
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """
    Class-based wrapper for metrics calculation functions.
    Maintains compatibility with existing code that expects a class.
    """

    def calculate_snapshot_metrics(
        self,
        snapshot: Any,
        session: Session,
        account: Any,
        scraped_data: Dict[str, Any],
    ) -> None:
        """Wrapper for calculate_snapshot_metrics function."""
        return calculate_snapshot_metrics(snapshot, session, account, scraped_data)

    def update_account_metadata(
        self, account: Any, scraped_data: Dict[str, Any]
    ) -> None:
        """Wrapper for update_account_metadata function."""
        return update_account_metadata(account, scraped_data)


# Singleton instance
_metrics_calculator = None


def get_metrics_calculator() -> MetricsCalculator:
    """Get singleton instance of MetricsCalculator."""
    global _metrics_calculator
    if _metrics_calculator is None:
        _metrics_calculator = MetricsCalculator()
    return _metrics_calculator


def calculate_snapshot_metrics(
    snapshot: Any, session: Session, account: Any, scraped_data: Dict[str, Any]
) -> None:
    """
    Calculate and set metrics for a FactFollowersSnapshot.

    This function calculates:
    - engagement_rate: (engagements / followers) * 100
    - follower_growth_rate: Percentage change from previous snapshot
    - follower_growth_absolute: Net follower change
    - posts_per_day: Average posting frequency
    - Video-specific metrics for YouTube

    Args:
        snapshot: FactFollowersSnapshot object to calculate metrics for
        session: Database session for querying previous snapshots
        account: DimAccount object
        scraped_data: Raw scraped data dictionary
    """
    from scraper.schema import FactFollowersSnapshot
    from datetime import datetime, timedelta

    # Calculate engagement rate
    if snapshot.followers_count and snapshot.followers_count > 0:
        if snapshot.engagements_total:
            snapshot.engagement_rate = round(
                (snapshot.engagements_total / snapshot.followers_count) * 100, 4
            )
        else:
            snapshot.engagement_rate = 0.0
    else:
        snapshot.engagement_rate = 0.0

    # Calculate follower growth (need previous snapshot)
    try:
        # Get the most recent previous snapshot (not including today)
        previous_snapshot = (
            session.query(FactFollowersSnapshot)
            .filter(
                FactFollowersSnapshot.account_key == account.account_key,
                FactFollowersSnapshot.snapshot_date < snapshot.snapshot_date,
            )
            .order_by(FactFollowersSnapshot.snapshot_date.desc())
            .first()
        )

        if (
            previous_snapshot
            and previous_snapshot.followers_count
            and previous_snapshot.followers_count > 0
        ):
            current_followers = snapshot.followers_count or 0
            previous_followers = previous_snapshot.followers_count

            # Calculate absolute growth
            snapshot.follower_growth_absolute = current_followers - previous_followers

            # Calculate percentage growth rate
            snapshot.follower_growth_rate = round(
                ((current_followers - previous_followers) / previous_followers) * 100, 4
            )
        else:
            # First snapshot for this account
            snapshot.follower_growth_absolute = 0
            snapshot.follower_growth_rate = 0.0

    except Exception as e:
        logger.debug(f"Error calculating growth rate: {e}")
        snapshot.follower_growth_absolute = 0
        snapshot.follower_growth_rate = 0.0

    # Calculate posting frequency (posts per day)
    if account.account_created_date:
        days_active = (snapshot.snapshot_date - account.account_created_date).days
        if days_active > 0 and snapshot.posts_count:
            snapshot.posts_per_day = round(snapshot.posts_count / days_active, 2)
        else:
            snapshot.posts_per_day = 0.0
    else:
        # If account_created_date not available, use snapshot date as approximation
        snapshot.posts_per_day = None

    # YouTube-specific video metrics
    if account.platform.lower() == "youtube":
        # Total video views (lifetime)
        total_video_views = (
            scraped_data.get("total_video_views")
            or scraped_data.get("view_count")
            or scraped_data.get("video_views", 0)
        )
        snapshot.total_video_views = (
            int(total_video_views) if total_video_views else None
        )

        # Average views per video
        video_count = (
            snapshot.videos_count
            or snapshot.posts_count
            or scraped_data.get("video_count", 0)
            or 0
        )
        if video_count > 0 and snapshot.total_video_views:
            snapshot.average_views_per_video = round(
                snapshot.total_video_views / video_count, 2
            )
        else:
            snapshot.average_views_per_video = None
    else:
        snapshot.total_video_views = None
        snapshot.average_views_per_video = None


def calculate_account_age(account: Any, snapshot_date: date) -> Optional[int]:
    """
    Calculate account age in days.

    Args:
        account: DimAccount object
        snapshot_date: Date to calculate age from

    Returns:
        Number of days active, or None if account_created_date not available
    """
    if account.account_created_date:
        return (snapshot_date - account.account_created_date).days
    return None


def update_account_metadata(account: Any, scraped_data: Dict[str, Any]) -> None:
    """
    Update account metadata from scraped data.

    Updates:
    - bio_text
    - bio_link
    - verified_status
    - account_created_date (if not already set)
    - account_category
    - profile_image_url

    Args:
        account: DimAccount object to update
        scraped_data: Scraped data dictionary
    """
    # Update bio_text if provided and not already set (or if updating existing)
    if "bio_text" in scraped_data and scraped_data["bio_text"]:
        account.bio_text = scraped_data["bio_text"]

    # Update bio_link if provided
    if "bio_link" in scraped_data and scraped_data["bio_link"]:
        account.bio_link = scraped_data["bio_link"]

    # Update verified_status if provided
    if "verified_status" in scraped_data and scraped_data["verified_status"]:
        account.verified_status = scraped_data["verified_status"]

    # Update account_created_date if provided and not already set
    if "account_created_date" in scraped_data and scraped_data["account_created_date"]:
        if not account.account_created_date:
            account.account_created_date = scraped_data["account_created_date"]

    # Update account_category if provided
    if "account_category" in scraped_data and scraped_data["account_category"]:
        account.account_category = scraped_data["account_category"]

    # Update profile_image_url if provided
    if "profile_image_url" in scraped_data and scraped_data["profile_image_url"]:
        account.profile_image_url = scraped_data["profile_image_url"]

    # Update account_type if provided
    if "account_type" in scraped_data and scraped_data["account_type"]:
        account.account_type = scraped_data["account_type"]
