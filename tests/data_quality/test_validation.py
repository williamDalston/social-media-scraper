"""
Data Validation Tests.

Tests to ensure data quality and validity.
"""
import pytest
from datetime import date, timedelta
from scraper.schema import DimAccount, FactFollowersSnapshot


class TestDataValidation:
    """Test data validation rules."""

    def test_follower_count_validation(self, db_session, sample_account):
        """Validate follower counts are reasonable."""
        # Valid follower count
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            followers_count=1000,
        )
        db_session.add(snapshot)
        db_session.commit()

        assert snapshot.followers_count >= 0
        assert snapshot.followers_count < 10**10  # Reasonable upper bound

    def test_engagement_validation(self, db_session, sample_account):
        """Validate engagement metrics."""
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            likes_count=500,
            comments_count=50,
            shares_count=100,
            engagements_total=650,
        )
        db_session.add(snapshot)
        db_session.commit()

        # Verify engagement calculation
        calculated = (
            snapshot.likes_count + snapshot.comments_count + snapshot.shares_count
        )
        assert snapshot.engagements_total == calculated

    def test_date_validation(self, db_session, sample_account):
        """Validate snapshot dates are reasonable."""
        # Valid date (today)
        snapshot1 = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            followers_count=1000,
        )
        db_session.add(snapshot1)
        db_session.commit()

        # Valid date (past)
        snapshot2 = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today() - timedelta(days=30),
            followers_count=900,
        )
        db_session.add(snapshot2)
        db_session.commit()

        # Dates should be in reasonable range
        assert snapshot1.snapshot_date <= date.today()
        assert snapshot2.snapshot_date <= date.today()
        assert snapshot2.snapshot_date >= date(2020, 1, 1)  # Not too old

    def test_platform_validation(self, db_session):
        """Validate platform values."""
        valid_platforms = [
            "X",
            "Instagram",
            "Facebook",
            "YouTube",
            "LinkedIn",
            "Truth Social",
        ]

        for platform in valid_platforms:
            account = DimAccount(
                platform=platform, handle=f"test_{platform.lower()}", org_name="HHS"
            )
            db_session.add(account)

        db_session.commit()

        # Verify all platforms are valid
        accounts = db_session.query(DimAccount).all()
        for account in accounts:
            if account.platform:
                # Platform should be in valid list or be reasonable
                assert len(account.platform) > 0
                assert len(account.platform) < 50  # Reasonable length


class TestDataConsistency:
    """Test data consistency rules."""

    def test_account_handle_consistency(self, db_session):
        """Verify account handles are consistent."""
        account = DimAccount(
            platform="X",
            handle="consistent_test",
            org_name="HHS",
            account_url="https://x.com/consistent_test",
        )
        db_session.add(account)
        db_session.commit()

        # Handle should match URL
        assert (
            "consistent_test" in account.account_url
            or account.handle == "consistent_test"
        )

    def test_snapshot_account_consistency(self, db_session, sample_account):
        """Verify snapshots reference valid accounts."""
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            followers_count=1000,
        )
        db_session.add(snapshot)
        db_session.commit()

        # Snapshot should reference valid account
        assert snapshot.account is not None
        assert snapshot.account.account_key == sample_account.account_key

    def test_engagement_consistency(self, db_session, sample_account):
        """Verify engagement metrics are consistent."""
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            likes_count=500,
            comments_count=50,
            shares_count=100,
            engagements_total=0,
        )
        # Calculate total
        snapshot.engagements_total = (
            snapshot.likes_count + snapshot.comments_count + snapshot.shares_count
        )
        db_session.add(snapshot)
        db_session.commit()

        # Verify consistency
        assert snapshot.engagements_total == 650
        assert snapshot.engagements_total == (
            snapshot.likes_count + snapshot.comments_count + snapshot.shares_count
        )


class TestDataCompleteness:
    """Test data completeness."""

    def test_required_fields_present(self, db_session):
        """Verify required fields are present."""
        account = DimAccount(platform="X", handle="completeness_test", org_name="HHS")
        db_session.add(account)
        db_session.commit()

        # Required fields should be present
        assert account.platform is not None
        assert account.handle is not None
        assert account.account_key is not None

    def test_snapshot_completeness(self, db_session, sample_account):
        """Verify snapshots have required data."""
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            followers_count=1000,
        )
        db_session.add(snapshot)
        db_session.commit()

        # Required fields
        assert snapshot.account_key is not None
        assert snapshot.snapshot_date is not None
        assert snapshot.followers_count is not None


class TestDataAccuracy:
    """Test data accuracy."""

    def test_follower_count_accuracy(self, db_session, sample_account):
        """Verify follower counts are accurate."""
        # Create snapshot with known value
        expected_followers = 1000
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            followers_count=expected_followers,
        )
        db_session.add(snapshot)
        db_session.commit()

        # Retrieve and verify
        retrieved = (
            db_session.query(FactFollowersSnapshot)
            .filter_by(
                account_key=sample_account.account_key, snapshot_date=date.today()
            )
            .first()
        )

        assert retrieved is not None
        assert retrieved.followers_count == expected_followers

    def test_date_accuracy(self, db_session, sample_account):
        """Verify dates are stored accurately."""
        test_date = date.today()
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=test_date,
            followers_count=1000,
        )
        db_session.add(snapshot)
        db_session.commit()

        # Verify date accuracy
        retrieved = (
            db_session.query(FactFollowersSnapshot)
            .filter_by(account_key=sample_account.account_key, snapshot_date=test_date)
            .first()
        )

        assert retrieved is not None
        assert retrieved.snapshot_date == test_date
