"""
Regression Test Suite.

Tests to prevent regressions in existing functionality.
"""
import pytest
from datetime import date
from scraper.schema import DimAccount, FactFollowersSnapshot


class TestRegressionSuite:
    """Comprehensive regression test suite."""
    
    def test_account_creation_regression(self, db_session):
        """Regression: Account creation should always work."""
        account = DimAccount(
            platform='X',
            handle='regression_account',
            org_name='HHS'
        )
        db_session.add(account)
        db_session.commit()
        
        # Should always succeed
        assert account.account_key is not None
    
    def test_snapshot_creation_regression(self, db_session, sample_account):
        """Regression: Snapshot creation should always work."""
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            followers_count=1000
        )
        db_session.add(snapshot)
        db_session.commit()
        
        # Should always succeed
        assert snapshot.snapshot_id is not None
    
    def test_api_endpoints_regression(self, client):
        """Regression: API endpoints should maintain compatibility."""
        endpoints = [
            '/api/summary',
            '/api/grid',
            '/api/history/X/test',
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            # Should not return 500 (internal error)
            assert response.status_code != 500
    
    def test_data_relationships_regression(self, db_session, sample_account):
        """Regression: Data relationships should always work."""
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            followers_count=1000
        )
        db_session.add(snapshot)
        db_session.commit()
        
        # Relationship should always work
        assert snapshot.account is not None
        assert snapshot.account.account_key == sample_account.account_key


class TestBackwardCompatibility:
    """Test backward compatibility."""
    
    def test_api_response_format_compatibility(self, client, db_session, sample_account):
        """Verify API response formats remain compatible."""
        from scraper.schema import FactFollowersSnapshot
        
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            followers_count=1000
        )
        db_session.add(snapshot)
        db_session.commit()
        
        response = client.get('/api/summary')
        if response.status_code == 200:
            data = response.get_json()
            # Should maintain expected structure
            assert isinstance(data, list)
            if len(data) > 0:
                item = data[0]
                assert 'platform' in item
                assert 'handle' in item
                assert 'followers' in item
    
    def test_database_schema_compatibility(self, db_session):
        """Verify database schema remains compatible."""
        # Test that all expected columns exist
        account = DimAccount(platform='X', handle='schema_test', org_name='HHS')
        db_session.add(account)
        db_session.commit()
        
        # Should have all expected fields
        assert hasattr(account, 'account_key')
        assert hasattr(account, 'platform')
        assert hasattr(account, 'handle')

