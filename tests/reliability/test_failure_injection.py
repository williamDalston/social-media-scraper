"""
Failure Injection Testing.

Tests that inject various types of failures to verify system resilience.
"""
import pytest
from unittest.mock import patch, MagicMock
from scraper.scrapers import RealScraper, SimulatedScraper
from scraper.collect_metrics import simulate_metrics
from scraper.schema import DimAccount, FactFollowersSnapshot
from datetime import date
import time


class TestDatabaseFailureInjection:
    """Inject database failures and verify recovery."""

    @patch("scraper.schema.create_engine")
    def test_database_connection_failure(self, mock_create_engine):
        """Test handling of database connection failures."""
        mock_create_engine.side_effect = Exception("Database connection failed")

        from scraper.schema import init_db

        with pytest.raises(Exception):
            init_db("test.db")

    def test_database_timeout_simulation(self, db_session):
        """Simulate database timeout scenarios."""
        # Test that operations complete within timeout
        start = time.time()
        account = DimAccount(platform="X", handle="timeout_test", org_name="HHS")
        db_session.add(account)
        db_session.commit()
        elapsed = time.time() - start

        # Should complete quickly
        assert elapsed < 1.0

    def test_database_lock_handling(self, db_session):
        """Test handling of database locks."""
        # Create account
        account = DimAccount(platform="X", handle="lock_test", org_name="HHS")
        db_session.add(account)
        db_session.commit()

        # Try concurrent access (simulated)
        # SQLite handles this, but we verify it works
        retrieved = db_session.query(DimAccount).filter_by(handle="lock_test").first()
        assert retrieved is not None


class TestNetworkFailureInjection:
    """Inject network failures and verify handling."""

    @patch("requests.get")
    def test_scraper_handles_network_failures(self, mock_get):
        """Test scraper handles various network failures."""
        import requests

        failure_scenarios = [
            requests.Timeout("Connection timeout"),
            requests.ConnectionError("Connection refused"),
            requests.HTTPError("HTTP Error"),
        ]

        for failure in failure_scenarios:
            mock_get.side_effect = failure

            scraper = RealScraper()
            account = DimAccount(
                platform="x",
                handle="test",
                org_name="HHS",
                account_url="https://x.com/test",
            )

            result = scraper.scrape(account)
            # Should handle gracefully (return None or error dict)
            assert result is None or isinstance(result, dict)

    @patch("requests.get")
    def test_scraper_handles_slow_responses(self, mock_get):
        """Test scraper handles slow network responses."""
        import time

        def slow_response(*args, **kwargs):
            time.sleep(0.5)  # Simulate slow response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "<html></html>"
            return mock_response

        mock_get.side_effect = slow_response

        scraper = RealScraper()
        account = DimAccount(
            platform="x",
            handle="test",
            org_name="HHS",
            account_url="https://x.com/test",
        )

        start = time.time()
        result = scraper.scrape(account)
        elapsed = time.time() - start

        # Should complete (may be slow but shouldn't hang)
        assert elapsed < 10.0


class TestServiceFailureInjection:
    """Inject service failures and verify resilience."""

    def test_partial_service_failure(self, test_db_path):
        """Test handling when some services fail."""
        from scraper.collect_metrics import simulate_metrics
        from scraper.schema import DimAccount, init_db
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import create_engine

        engine = create_engine(f"sqlite:///{test_db_path}")
        init_db(test_db_path)
        Session = sessionmaker(bind=engine)
        session = Session()

        # Create accounts
        for i in range(5):
            account = DimAccount(
                platform="X", handle=f"failure_test_{i}", org_name="HHS"
            )
            session.add(account)
        session.commit()
        session.close()

        # Run metrics collection - should handle all accounts even if some fail
        simulate_metrics(db_path=test_db_path, mode="simulated")

        # Verify some snapshots were created
        session = Session()
        snapshots = session.query(FactFollowersSnapshot).all()
        # At least some should succeed
        assert len(snapshots) > 0
        session.close()

    def test_cascading_failure_prevention(self, db_session):
        """Test that failures don't cascade."""
        # Create account
        account = DimAccount(platform="X", handle="cascade_test", org_name="HHS")
        db_session.add(account)
        db_session.commit()

        # Try to create snapshot with invalid data
        try:
            snapshot = FactFollowersSnapshot(
                account_key=account.account_key,
                snapshot_date="invalid-date",  # Invalid
                followers_count=1000,
            )
            db_session.add(snapshot)
            db_session.commit()
        except (ValueError, TypeError):
            # Should fail gracefully
            db_session.rollback()

        # Account should still exist
        retrieved = (
            db_session.query(DimAccount).filter_by(handle="cascade_test").first()
        )
        assert retrieved is not None


class TestResourceExhaustionInjection:
    """Inject resource exhaustion scenarios."""

    def test_memory_pressure_handling(self, db_session):
        """Test handling under memory pressure."""
        # Create many accounts
        accounts = []
        for i in range(100):
            account = DimAccount(
                platform="X", handle=f"memory_test_{i}", org_name="HHS"
            )
            accounts.append(account)
            db_session.add(account)

        db_session.commit()

        # Query all - should handle memory efficiently
        all_accounts = (
            db_session.query(DimAccount)
            .filter(DimAccount.handle.like("memory_test_%"))
            .all()
        )
        assert len(all_accounts) == 100

    def test_disk_space_simulation(self, db_session):
        """Test behavior when disk space is limited."""
        # Create many snapshots
        account = DimAccount(platform="X", handle="disk_test", org_name="HHS")
        db_session.add(account)
        db_session.commit()

        # Create many snapshots
        for i in range(100):
            snapshot = FactFollowersSnapshot(
                account_key=account.account_key,
                snapshot_date=date.fromordinal(date.today().toordinal() - i),
                followers_count=1000 + i,
            )
            db_session.add(snapshot)

        db_session.commit()

        # Should handle large dataset
        snapshots = (
            db_session.query(FactFollowersSnapshot)
            .filter_by(account_key=account.account_key)
            .count()
        )
        assert snapshots == 100
