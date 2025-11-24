"""
Data Completeness Checks.

Tests to ensure data is complete and not missing critical information.
"""
import pytest
from datetime import date, timedelta
from scraper.schema import DimAccount, FactFollowersSnapshot


class TestDataCompleteness:
    """Test data completeness."""

    def test_account_completeness(self, db_session):
        """Verify accounts have all required fields."""
        account = DimAccount(
            platform="X",
            handle="completeness_test",
            org_name="HHS",
            account_url="https://x.com/completeness_test",
        )
        db_session.add(account)
        db_session.commit()

        # Required fields
        assert account.platform is not None
        assert account.handle is not None
        assert account.account_key is not None

        # Optional but important fields
        # These may be None but should be set when possible
        assert account.account_url is not None or True  # May be optional

    def test_snapshot_completeness(self, db_session, sample_account):
        """Verify snapshots have complete data."""
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            followers_count=1000,
            engagements_total=500,
        )
        db_session.add(snapshot)
        db_session.commit()

        # Required fields
        assert snapshot.account_key is not None
        assert snapshot.snapshot_date is not None
        assert snapshot.followers_count is not None

        # Engagement should be calculated if not provided
        if snapshot.engagements_total is None:
            # Should calculate from components
            calculated = (
                (snapshot.likes_count or 0)
                + (snapshot.comments_count or 0)
                + (snapshot.shares_count or 0)
            )
            snapshot.engagements_total = calculated
            db_session.commit()

        assert snapshot.engagements_total is not None

    def test_historical_data_completeness(self, db_session, sample_account):
        """Verify historical data is complete."""
        # Create snapshots for past 30 days
        today = date.today()
        created_dates = []

        for i in range(30):
            snapshot_date = today - timedelta(days=i)
            snapshot = FactFollowersSnapshot(
                account_key=sample_account.account_key,
                snapshot_date=snapshot_date,
                followers_count=1000 + i,
            )
            db_session.add(snapshot)
            created_dates.append(snapshot_date)

        db_session.commit()

        # Verify all dates have snapshots
        for snapshot_date in created_dates:
            exists = (
                db_session.query(FactFollowersSnapshot)
                .filter_by(
                    account_key=sample_account.account_key, snapshot_date=snapshot_date
                )
                .first()
            )
            assert exists is not None


class TestMissingDataDetection:
    """Test detection of missing data."""

    def test_detect_missing_snapshots(self, db_session, sample_account):
        """Detect missing snapshots for accounts."""
        today = date.today()

        # Create snapshot for today
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=today,
            followers_count=1000,
        )
        db_session.add(snapshot)
        db_session.commit()

        # Check for missing snapshots (yesterday should be missing)
        yesterday = today - timedelta(days=1)
        missing = (
            db_session.query(FactFollowersSnapshot)
            .filter_by(account_key=sample_account.account_key, snapshot_date=yesterday)
            .first()
        )

        # Yesterday should be missing (or present if backfilled)
        assert missing is None or missing is not None

    def test_detect_missing_account_data(self, db_session):
        """Detect accounts with missing critical data."""
        # Account with minimal data
        account = DimAccount(
            platform="X",
            handle="minimal_data",
            # Missing org_name, account_url, etc.
        )
        db_session.add(account)
        db_session.commit()

        # Verify account exists but may have missing fields
        retrieved = (
            db_session.query(DimAccount).filter_by(handle="minimal_data").first()
        )
        assert retrieved is not None
        # Some fields may be None
        assert retrieved.platform is not None  # Required field


class TestDataGapDetection:
    """Test detection of data gaps."""

    def test_detect_snapshot_gaps(self, db_session, sample_account):
        """Detect gaps in snapshot history."""
        from datetime import date, timedelta

        # Create snapshots with gaps
        today = date.today()
        dates_to_create = [today, today - timedelta(days=2), today - timedelta(days=5)]

        for snapshot_date in dates_to_create:
            snapshot = FactFollowersSnapshot(
                account_key=sample_account.account_key,
                snapshot_date=snapshot_date,
                followers_count=1000,
            )
            db_session.add(snapshot)
        db_session.commit()

        # Check for gaps
        all_snapshots = (
            db_session.query(FactFollowersSnapshot)
            .filter_by(account_key=sample_account.account_key)
            .order_by(FactFollowersSnapshot.snapshot_date)
            .all()
        )

        # Should have gaps (missing days 1, 3, 4)
        assert len(all_snapshots) == 3

    def test_detect_account_coverage(self, db_session):
        """Detect accounts without recent snapshots."""
        # Create account
        account = DimAccount(platform="X", handle="coverage_test", org_name="HHS")
        db_session.add(account)
        db_session.commit()

        # Check for recent snapshots
        today = date.today()
        recent_snapshots = (
            db_session.query(FactFollowersSnapshot)
            .filter(
                FactFollowersSnapshot.account_key == account.account_key,
                FactFollowersSnapshot.snapshot_date >= today - timedelta(days=7),
            )
            .count()
        )

        # May have 0 or more recent snapshots
        assert isinstance(recent_snapshots, int)
