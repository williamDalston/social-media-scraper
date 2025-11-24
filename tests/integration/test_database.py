import pytest
from datetime import date
from sqlalchemy.exc import IntegrityError
from scraper.schema import DimAccount, FactFollowersSnapshot, FactSocialPost


class TestAccountCreation:
    """Test account creation and retrieval."""

    def test_create_account(self, db_session):
        """Test creating a new account."""
        account = DimAccount(
            platform="X",
            handle="new_account",
            org_name="HHS",
            account_url="https://x.com/new_account",
        )
        db_session.add(account)
        db_session.commit()

        # Verify account was created
        retrieved = db_session.query(DimAccount).filter_by(handle="new_account").first()
        assert retrieved is not None
        assert retrieved.platform == "X"
        assert retrieved.org_name == "HHS"

    def test_query_account_by_platform_and_handle(self, db_session, sample_account):
        """Test querying account by platform and handle."""
        account = (
            db_session.query(DimAccount)
            .filter_by(platform="X", handle="test_handle")
            .first()
        )

        assert account is not None
        assert account.account_key == sample_account.account_key

    def test_query_all_accounts(self, db_session, multiple_accounts):
        """Test querying all accounts."""
        accounts = db_session.query(DimAccount).all()
        assert len(accounts) == 4  # 4 accounts from multiple_accounts fixture


class TestSnapshotCreation:
    """Test snapshot creation and retrieval."""

    def test_create_snapshot(self, db_session, sample_account):
        """Test creating a new snapshot."""
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            followers_count=2000,
            engagements_total=1000,
        )
        db_session.add(snapshot)
        db_session.commit()

        # Verify snapshot was created
        retrieved = (
            db_session.query(FactFollowersSnapshot)
            .filter_by(
                account_key=sample_account.account_key, snapshot_date=date.today()
            )
            .first()
        )

        assert retrieved is not None
        assert retrieved.followers_count == 2000
        assert retrieved.engagements_total == 1000

    def test_query_snapshots_by_account(self, db_session, sample_account):
        """Test querying snapshots for a specific account."""
        # Create multiple snapshots
        for i in range(3):
            snapshot = FactFollowersSnapshot(
                account_key=sample_account.account_key,
                snapshot_date=date.fromordinal(date.today().toordinal() - i),
                followers_count=1000 + i * 100,
            )
            db_session.add(snapshot)
        db_session.commit()

        snapshots = (
            db_session.query(FactFollowersSnapshot)
            .filter_by(account_key=sample_account.account_key)
            .all()
        )

        assert len(snapshots) == 3

    def test_query_latest_snapshot(self, db_session, sample_account):
        """Test querying the latest snapshot for an account."""
        # Create snapshots for different dates
        dates = [date.fromordinal(date.today().toordinal() - i) for i in range(3)]
        for snapshot_date in dates:
            snapshot = FactFollowersSnapshot(
                account_key=sample_account.account_key,
                snapshot_date=snapshot_date,
                followers_count=1000,
            )
            db_session.add(snapshot)
        db_session.commit()

        latest = (
            db_session.query(FactFollowersSnapshot)
            .filter_by(account_key=sample_account.account_key)
            .order_by(FactFollowersSnapshot.snapshot_date.desc())
            .first()
        )

        assert latest is not None
        assert latest.snapshot_date == date.today()


class TestJoins:
    """Test database joins between tables."""

    def test_join_account_and_snapshot(self, db_session, sample_account):
        """Test joining DimAccount and FactFollowersSnapshot."""
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            followers_count=1000,
        )
        db_session.add(snapshot)
        db_session.commit()

        # Query with join
        results = (
            db_session.query(DimAccount, FactFollowersSnapshot)
            .join(FactFollowersSnapshot)
            .filter(FactFollowersSnapshot.snapshot_date == date.today())
            .all()
        )

        assert len(results) == 1
        account, snapshot_result = results[0]
        assert account.account_key == sample_account.account_key
        assert snapshot_result.followers_count == 1000

    def test_join_multiple_accounts(self, db_session, multiple_accounts):
        """Test joining multiple accounts with their snapshots."""
        today = date.today()
        for account in multiple_accounts:
            snapshot = FactFollowersSnapshot(
                account_key=account.account_key,
                snapshot_date=today,
                followers_count=1000,
            )
            db_session.add(snapshot)
        db_session.commit()

        results = (
            db_session.query(DimAccount, FactFollowersSnapshot)
            .join(FactFollowersSnapshot)
            .filter(FactFollowersSnapshot.snapshot_date == today)
            .all()
        )

        assert len(results) == 4
        for account, snapshot in results:
            assert account.account_key == snapshot.account_key


class TestDataIntegrity:
    """Test data integrity constraints."""

    def test_foreign_key_constraint(self, db_session):
        """Test that foreign key constraint is enforced."""
        snapshot = FactFollowersSnapshot(
            account_key=99999,  # Non-existent account_key
            snapshot_date=date.today(),
            followers_count=1000,
        )
        db_session.add(snapshot)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_unique_constraint_on_account_platform_handle(self, db_session):
        """Test that we can have same handle on different platforms."""
        account1 = DimAccount(platform="X", handle="same_handle", org_name="HHS")
        account2 = DimAccount(
            platform="Instagram", handle="same_handle", org_name="HHS"
        )
        db_session.add(account1)
        db_session.add(account2)
        db_session.commit()

        # Should succeed - same handle, different platforms
        accounts = db_session.query(DimAccount).filter_by(handle="same_handle").all()
        assert len(accounts) == 2


class TestTransactions:
    """Test transaction rollback on errors."""

    def test_transaction_rollback_on_error(self, db_session):
        """Test that transaction rolls back on error."""
        account = DimAccount(platform="X", handle="test", org_name="HHS")
        db_session.add(account)
        db_session.commit()

        # Try to create snapshot with invalid foreign key
        snapshot = FactFollowersSnapshot(
            account_key=99999, snapshot_date=date.today(), followers_count=1000
        )
        db_session.add(snapshot)

        try:
            db_session.commit()
        except IntegrityError:
            db_session.rollback()

        # Account should still exist (was committed before error)
        account_check = db_session.query(DimAccount).filter_by(handle="test").first()
        assert account_check is not None

        # Snapshot should not exist (rollback)
        snapshot_check = (
            db_session.query(FactFollowersSnapshot).filter_by(account_key=99999).first()
        )
        assert snapshot_check is None


class TestPostCreation:
    """Test post creation and relationships."""

    def test_create_post(self, db_session, sample_account):
        """Test creating a social media post."""
        from datetime import datetime

        post = FactSocialPost(
            account_key=sample_account.account_key,
            platform="X",
            post_id="12345",
            post_url="https://x.com/test/status/12345",
            post_datetime_utc=datetime.now(),
            likes_count=100,
        )
        db_session.add(post)
        db_session.commit()

        retrieved = db_session.query(FactSocialPost).filter_by(post_id="12345").first()
        assert retrieved is not None
        assert retrieved.account_key == sample_account.account_key
        assert retrieved.likes_count == 100

    def test_post_relationship_to_account(self, db_session, sample_account):
        """Test that post has relationship to account."""
        from datetime import datetime

        post = FactSocialPost(
            account_key=sample_account.account_key,
            platform="X",
            post_id="12345",
            post_datetime_utc=datetime.now(),
        )
        db_session.add(post)
        db_session.commit()

        assert post.account is not None
        assert post.account.handle == sample_account.handle
