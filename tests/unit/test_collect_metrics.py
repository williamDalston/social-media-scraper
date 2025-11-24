import pytest
from unittest.mock import patch, MagicMock
from datetime import date
from scraper.collect_metrics import simulate_metrics
from scraper.schema import DimAccount, FactFollowersSnapshot, init_db
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine


class TestSimulateMetrics:
    """Test the simulate_metrics function."""

    def test_simulate_metrics_creates_snapshots(self, test_db_path):
        """Test that simulate_metrics creates snapshots for accounts."""
        # Set up database with accounts
        engine = create_engine(f"sqlite:///{test_db_path}")
        init_db(test_db_path)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Create test accounts
        account1 = DimAccount(
            platform="X",
            handle="test1",
            org_name="HHS",
            account_url="https://x.com/test1",
        )
        account2 = DimAccount(
            platform="Instagram",
            handle="test2",
            org_name="NIH",
            account_url="https://instagram.com/test2",
        )
        session.add(account1)
        session.add(account2)
        session.commit()
        session.close()

        # Run simulate_metrics
        simulate_metrics(db_path=test_db_path, mode="simulated")

        # Verify snapshots were created
        session = Session()
        snapshots = session.query(FactFollowersSnapshot).all()
        assert len(snapshots) == 2

        # Verify snapshot data
        for snapshot in snapshots:
            assert snapshot.snapshot_date == date.today()
            assert snapshot.followers_count > 0
            assert snapshot.engagements_total >= 0

        session.close()

    def test_simulate_metrics_prevents_duplicate_snapshots(self, test_db_path):
        """Test that simulate_metrics doesn't create duplicate snapshots for same date."""
        # Set up database with account and existing snapshot
        engine = create_engine(f"sqlite:///{test_db_path}")
        init_db(test_db_path)
        Session = sessionmaker(bind=engine)
        session = Session()

        account = DimAccount(
            platform="X",
            handle="test",
            org_name="HHS",
            account_url="https://x.com/test",
        )
        session.add(account)
        session.commit()

        # Create existing snapshot for today
        existing_snapshot = FactFollowersSnapshot(
            account_key=account.account_key,
            snapshot_date=date.today(),
            followers_count=1000,
        )
        session.add(existing_snapshot)
        session.commit()
        session.close()

        # Run simulate_metrics
        simulate_metrics(db_path=test_db_path, mode="simulated")

        # Verify only one snapshot exists for today
        session = Session()
        snapshots = (
            session.query(FactFollowersSnapshot)
            .filter_by(account_key=account.account_key, snapshot_date=date.today())
            .all()
        )
        assert len(snapshots) == 1
        session.close()

    def test_simulate_metrics_calculates_engagements_total(self, test_db_path):
        """Test that simulate_metrics calculates engagements_total correctly."""
        engine = create_engine(f"sqlite:///{test_db_path}")
        init_db(test_db_path)
        Session = sessionmaker(bind=engine)
        session = Session()

        account = DimAccount(
            platform="X",
            handle="test",
            org_name="HHS",
            account_url="https://x.com/test",
        )
        session.add(account)
        session.commit()
        session.close()

        simulate_metrics(db_path=test_db_path, mode="simulated")

        session = Session()
        snapshot = (
            session.query(FactFollowersSnapshot)
            .filter_by(account_key=account.account_key)
            .first()
        )

        assert snapshot is not None
        expected_total = (
            snapshot.likes_count + snapshot.comments_count + snapshot.shares_count
        )
        assert snapshot.engagements_total == expected_total
        session.close()

    def test_simulate_metrics_handles_missing_accounts(self, test_db_path):
        """Test that simulate_metrics handles case with no accounts."""
        engine = create_engine(f"sqlite:///{test_db_path}")
        init_db(test_db_path)

        # Run with no accounts - should not error
        simulate_metrics(db_path=test_db_path, mode="simulated")

        Session = sessionmaker(bind=engine)
        session = Session()
        snapshots = session.query(FactFollowersSnapshot).all()
        assert len(snapshots) == 0
        session.close()

    @patch("scraper.collect_metrics.get_scraper")
    def test_simulate_metrics_uses_scraper_mode(self, mock_get_scraper, test_db_path):
        """Test that simulate_metrics uses the correct scraper mode."""
        mock_scraper = MagicMock()
        mock_scraper.scrape.return_value = {
            "followers_count": 1000,
            "following_count": 100,
            "posts_count": 5,
            "likes_count": 500,
            "comments_count": 50,
            "shares_count": 100,
        }
        mock_get_scraper.return_value = mock_scraper

        engine = create_engine(f"sqlite:///{test_db_path}")
        init_db(test_db_path)
        Session = sessionmaker(bind=engine)
        session = Session()

        account = DimAccount(
            platform="X",
            handle="test",
            org_name="HHS",
            account_url="https://x.com/test",
        )
        session.add(account)
        session.commit()
        session.close()

        simulate_metrics(db_path=test_db_path, mode="real")

        # Verify scraper was called with correct mode
        mock_get_scraper.assert_called_once_with("real")
        mock_scraper.scrape.assert_called_once()
        session.close()

    @patch("scraper.collect_metrics.get_scraper")
    def test_simulate_metrics_handles_scraper_failure(
        self, mock_get_scraper, test_db_path
    ):
        """Test that simulate_metrics handles scraper returning None."""
        mock_scraper = MagicMock()
        mock_scraper.scrape.return_value = None  # Simulate scraper failure

        mock_get_scraper.return_value = mock_scraper

        engine = create_engine(f"sqlite:///{test_db_path}")
        init_db(test_db_path)
        Session = sessionmaker(bind=engine)
        session = Session()

        account = DimAccount(
            platform="X",
            handle="test",
            org_name="HHS",
            account_url="https://x.com/test",
        )
        session.add(account)
        session.commit()
        session.close()

        # Should not raise error, just skip account
        simulate_metrics(db_path=test_db_path, mode="real")

        session = Session()
        snapshots = session.query(FactFollowersSnapshot).all()
        assert len(snapshots) == 0  # No snapshot created due to scraper failure
        session.close()

    def test_simulate_metrics_creates_snapshots_for_all_accounts(self, test_db_path):
        """Test that simulate_metrics processes all accounts."""
        engine = create_engine(f"sqlite:///{test_db_path}")
        init_db(test_db_path)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Create multiple accounts
        for i in range(5):
            account = DimAccount(
                platform="X",
                handle=f"test{i}",
                org_name="HHS",
                account_url=f"https://x.com/test{i}",
            )
            session.add(account)
        session.commit()
        session.close()

        simulate_metrics(db_path=test_db_path, mode="simulated")

        session = Session()
        snapshots = session.query(FactFollowersSnapshot).all()
        assert len(snapshots) == 5
        session.close()
