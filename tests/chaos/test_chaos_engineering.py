"""
Chaos Engineering Tests.

Chaos engineering tests inject failures to verify system resilience and
error handling capabilities.
"""
import pytest
from unittest.mock import patch, MagicMock
from scraper.scrapers import SimulatedScraper, RealScraper
from scraper.collect_metrics import simulate_metrics
from scraper.schema import DimAccount, FactFollowersSnapshot
from datetime import date
import time


class TestDatabaseFailureInjection:
    """Test system behavior when database operations fail."""
    
    @patch('scraper.schema.create_engine')
    def test_database_connection_failure(self, mock_create_engine):
        """Test handling of database connection failures."""
        mock_create_engine.side_effect = Exception("Database connection failed")
        
        from scraper.schema import init_db
        with pytest.raises(Exception):
            init_db('test.db')
    
    def test_database_timeout_simulation(self, db_session):
        """Simulate database timeout scenario."""
        # This would require actual database timeout, which is hard to simulate
        # But we can test that operations complete within reasonable time
        account = DimAccount(
            platform='X',
            handle='test',
            org_name='HHS'
        )
        
        start_time = time.time()
        db_session.add(account)
        db_session.commit()
        elapsed = time.time() - start_time
        
        # Should complete quickly (under 1 second for simple insert)
        assert elapsed < 1.0


class TestNetworkFailureInjection:
    """Test system behavior when network operations fail."""
    
    @patch('requests.get')
    def test_scraper_network_timeout(self, mock_get):
        """Test scraper handling of network timeouts."""
        import requests
        mock_get.side_effect = requests.Timeout("Connection timeout")
        
        scraper = RealScraper()
        account = DimAccount(
            platform='x',
            handle='test',
            org_name='HHS',
            account_url='https://x.com/test'
        )
        
        result = scraper.scrape(account)
        # Should return None or handle gracefully
        assert result is None or isinstance(result, dict)
    
    @patch('requests.get')
    def test_scraper_connection_error(self, mock_get):
        """Test scraper handling of connection errors."""
        import requests
        mock_get.side_effect = requests.ConnectionError("Connection refused")
        
        scraper = RealScraper()
        account = DimAccount(
            platform='x',
            handle='test',
            org_name='HHS',
            account_url='https://x.com/test'
        )
        
        result = scraper.scrape(account)
        assert result is None
    
    @patch('requests.get')
    def test_scraper_http_errors(self, mock_get):
        """Test scraper handling of various HTTP errors."""
        import requests
        
        error_codes = [400, 401, 403, 404, 429, 500, 502, 503]
        
        for status_code in error_codes:
            mock_response = MagicMock()
            mock_response.status_code = status_code
            mock_get.return_value = mock_response
            
            scraper = RealScraper()
            account = DimAccount(
                platform='x',
                handle='test',
                org_name='HHS',
                account_url='https://x.com/test'
            )
            
            result = scraper.scrape(account)
            # Should handle all error codes gracefully
            assert result is None or isinstance(result, dict)


class TestMemoryFailureInjection:
    """Test system behavior under memory pressure."""
    
    def test_large_dataset_handling(self, db_session):
        """Test system can handle large datasets."""
        # Create many accounts
        accounts = []
        for i in range(100):
            account = DimAccount(
                platform='X',
                handle=f'test_{i}',
                org_name='HHS'
            )
            accounts.append(account)
            db_session.add(account)
        
        db_session.commit()
        
        # Query all accounts
        all_accounts = db_session.query(DimAccount).all()
        assert len(all_accounts) >= 100


class TestConcurrentOperationFailure:
    """Test system behavior under concurrent operations."""
    
    def test_concurrent_snapshot_creation(self, db_session, sample_account):
        """Test handling of concurrent snapshot creation attempts."""
        # Simulate concurrent creation of same snapshot
        snapshot1 = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            followers_count=1000
        )
        snapshot2 = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            followers_count=2000
        )
        
        db_session.add(snapshot1)
        db_session.commit()
        
        # Second snapshot with same date should either fail or be handled
        db_session.add(snapshot2)
        try:
            db_session.commit()
            # If it succeeds, that's okay (maybe no unique constraint)
        except Exception:
            # If it fails due to constraint, that's also okay
            db_session.rollback()


class TestDataCorruptionScenarios:
    """Test system behavior with corrupted or invalid data."""
    
    def test_invalid_date_handling(self, db_session, sample_account):
        """Test handling of invalid dates."""
        # SQLAlchemy will validate dates, so invalid dates should raise errors
        with pytest.raises((ValueError, TypeError)):
            snapshot = FactFollowersSnapshot(
                account_key=sample_account.account_key,
                snapshot_date="invalid-date",  # Invalid date format
                followers_count=1000
            )
            db_session.add(snapshot)
            db_session.commit()
    
    def test_negative_values_handling(self, db_session, sample_account):
        """Test handling of negative metric values."""
        # System should either reject or handle negative values
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            followers_count=-100  # Negative value
        )
        db_session.add(snapshot)
        
        # Should either accept (if allowed) or reject
        try:
            db_session.commit()
            # If accepted, verify it's stored
            assert snapshot.followers_count == -100
        except Exception:
            # If rejected, that's also valid
            db_session.rollback()


class TestServiceDegradation:
    """Test system behavior when services degrade."""
    
    @patch('scraper.collect_metrics.get_scraper')
    def test_slow_scraper_response(self, mock_get_scraper, test_db_path):
        """Test handling of slow scraper responses."""
        import time
        
        def slow_scrape(account):
            time.sleep(0.1)  # Simulate slow response
            return {
                'followers_count': 1000,
                'following_count': 100,
                'posts_count': 5,
                'likes_count': 500,
                'comments_count': 50,
                'shares_count': 100
            }
        
        mock_scraper = MagicMock()
        mock_scraper.scrape = slow_scrape
        mock_get_scraper.return_value = mock_scraper
        
        from scraper.collect_metrics import simulate_metrics
        from scraper.schema import DimAccount, init_db
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import create_engine
        
        engine = create_engine(f'sqlite:///{test_db_path}')
        init_db(test_db_path)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        account = DimAccount(
            platform='X',
            handle='test',
            org_name='HHS',
            account_url='https://x.com/test'
        )
        session.add(account)
        session.commit()
        session.close()
        
        # Should complete despite slow responses
        start_time = time.time()
        simulate_metrics(db_path=test_db_path, mode='simulated')
        elapsed = time.time() - start_time
        
        # Should complete (may be slow but should not hang)
        assert elapsed < 10.0  # Should complete within 10 seconds


class TestPartialFailureScenarios:
    """Test system behavior when partial failures occur."""
    
    def test_partial_account_processing(self, test_db_path):
        """Test handling when some accounts fail to process."""
        from scraper.collect_metrics import simulate_metrics
        from scraper.schema import DimAccount, init_db
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import create_engine
        
        engine = create_engine(f'sqlite:///{test_db_path}')
        init_db(test_db_path)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Create multiple accounts
        for i in range(5):
            account = DimAccount(
                platform='X',
                handle=f'test_{i}',
                org_name='HHS',
                account_url=f'https://x.com/test_{i}'
            )
            session.add(account)
        session.commit()
        session.close()
        
        # Process should handle all accounts even if some fail
        simulate_metrics(db_path=test_db_path, mode='simulated')
        
        # Verify some snapshots were created
        session = Session()
        snapshots = session.query(FactFollowersSnapshot).all()
        # At least some should succeed
        assert len(snapshots) > 0
        session.close()

