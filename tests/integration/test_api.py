import pytest
import json
from datetime import date
from scraper.schema import DimAccount, FactFollowersSnapshot


class TestDashboardRoute:
    """Test the dashboard route."""
    
    def test_index_route_returns_dashboard(self, client):
        """Test that GET / returns the dashboard page."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'html' in response.data.lower() or response.content_type == 'text/html; charset=utf-8'


class TestSummaryAPI:
    """Test the /api/summary endpoint."""
    
    def test_summary_returns_empty_when_no_data(self, client, app):
        """Test that summary returns empty list when no snapshots exist."""
        response = client.get('/api/summary')
        assert response.status_code == 200
        data = response.get_json()
        assert data == []
    
    def test_summary_returns_latest_metrics(self, client, app, db_session, sample_account):
        """Test that summary returns latest snapshot data."""
        # Create snapshots for different dates
        today = date.today()
        yesterday = date.fromordinal(today.toordinal() - 1)
        
        old_snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=yesterday,
            followers_count=900,
            engagements_total=500
        )
        latest_snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=today,
            followers_count=1000,
            engagements_total=650
        )
        db_session.add(old_snapshot)
        db_session.add(latest_snapshot)
        db_session.commit()
        
        response = client.get('/api/summary')
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data) == 1
        assert data[0]['platform'] == 'X'
        assert data[0]['handle'] == 'test_handle'
        assert data[0]['followers'] == 1000
        assert data[0]['engagement'] == 650
    
    def test_summary_returns_multiple_accounts(self, client, app, db_session, multiple_accounts):
        """Test that summary returns data for all accounts."""
        today = date.today()
        for account in multiple_accounts:
            snapshot = FactFollowersSnapshot(
                account_key=account.account_key,
                snapshot_date=today,
                followers_count=1000,
                engagements_total=500
            )
            db_session.add(snapshot)
        db_session.commit()
        
        response = client.get('/api/summary')
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data) == 4


class TestHistoryAPI:
    """Test the /api/history/<platform>/<handle> endpoint."""
    
    def test_history_returns_404_for_nonexistent_account(self, client, app):
        """Test that history returns 404 for account that doesn't exist."""
        response = client.get('/api/history/X/nonexistent')
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
    
    def test_history_returns_account_history(self, client, app, db_session, sample_account):
        """Test that history returns all snapshots for an account."""
        # Create multiple snapshots
        today = date.today()
        dates = [date.fromordinal(today.toordinal() - i) for i in range(5)]
        
        for i, snapshot_date in enumerate(dates):
            snapshot = FactFollowersSnapshot(
                account_key=sample_account.account_key,
                snapshot_date=snapshot_date,
                followers_count=1000 + i * 10,
                engagements_total=500 + i * 5
            )
            db_session.add(snapshot)
        db_session.commit()
        
        response = client.get(f'/api/history/{sample_account.platform}/{sample_account.handle}')
        assert response.status_code == 200
        data = response.get_json()
        
        assert 'dates' in data
        assert 'followers' in data
        assert 'engagement' in data
        assert len(data['dates']) == 5
        assert len(data['followers']) == 5
        assert len(data['engagement']) == 5
    
    def test_history_returns_empty_when_no_snapshots(self, client, app, db_session, sample_account):
        """Test that history returns empty arrays when account has no snapshots."""
        response = client.get(f'/api/history/{sample_account.platform}/{sample_account.handle}')
        assert response.status_code == 200
        data = response.get_json()
        
        assert data['dates'] == []
        assert data['followers'] == []
        assert data['engagement'] == []


class TestGridAPI:
    """Test the /api/grid endpoint."""
    
    def test_grid_returns_all_data(self, client, app, db_session, sample_account):
        """Test that grid returns all snapshot data."""
        today = date.today()
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=today,
            followers_count=1000,
            engagements_total=650,
            posts_count=5,
            likes_count=500,
            comments_count=50,
            shares_count=100
        )
        db_session.add(snapshot)
        db_session.commit()
        
        response = client.get('/api/grid')
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data) == 1
        assert len(data[0]) == 10  # All fields
        assert data[0][0] == 'X'  # platform
        assert data[0][1] == 'test_handle'  # handle
        assert data[0][4] == 1000  # followers_count
    
    def test_grid_returns_empty_when_no_data(self, client, app):
        """Test that grid returns empty list when no data exists."""
        response = client.get('/api/grid')
        assert response.status_code == 200
        data = response.get_json()
        assert data == []


class TestDownloadAPI:
    """Test the /api/download endpoint."""
    
    def test_download_returns_csv(self, client, app, db_session, sample_account):
        """Test that download returns CSV file."""
        today = date.today()
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=today,
            followers_count=1000,
            engagements_total=650,
            posts_count=5,
            likes_count=500,
            comments_count=50,
            shares_count=100
        )
        db_session.add(snapshot)
        db_session.commit()
        
        response = client.get('/api/download')
        assert response.status_code == 200
        assert response.content_type == 'text/csv; charset=utf-8'
        assert 'attachment' in response.headers.get('Content-Disposition', '')
        assert 'hhs_social_media_data.csv' in response.headers.get('Content-Disposition', '')
        
        # Verify CSV content
        csv_data = response.data.decode('utf-8')
        assert 'Platform' in csv_data
        assert 'Handle' in csv_data
        assert 'test_handle' in csv_data
    
    def test_download_returns_empty_csv_when_no_data(self, client, app):
        """Test that download returns CSV with headers only when no data."""
        response = client.get('/api/download')
        assert response.status_code == 200
        
        csv_data = response.data.decode('utf-8')
        lines = csv_data.strip().split('\n')
        assert len(lines) == 1  # Header only
        assert 'Platform' in lines[0]


class TestRunScraperAPI:
    """Test the /api/run-scraper endpoint."""
    
    def test_run_scraper_with_simulated_mode(self, client, app, db_session, sample_account):
        """Test running scraper in simulated mode."""
        response = client.post(
            '/api/run-scraper',
            json={'mode': 'simulated'},
            content_type='application/json'
        )
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data
        
        # Verify snapshot was created
        today = date.today()
        snapshot = db_session.query(FactFollowersSnapshot).filter_by(
            account_key=sample_account.account_key,
            snapshot_date=today
        ).first()
        assert snapshot is not None
    
    def test_run_scraper_with_real_mode(self, client, app, db_session, sample_account):
        """Test running scraper in real mode."""
        response = client.post(
            '/api/run-scraper',
            json={'mode': 'real'},
            content_type='application/json'
        )
        # May succeed or fail depending on network, but should not crash
        assert response.status_code in [200, 500]
    
    def test_run_scraper_defaults_to_simulated(self, client, app, db_session, sample_account):
        """Test that scraper defaults to simulated mode."""
        response = client.post(
            '/api/run-scraper',
            json={},
            content_type='application/json'
        )
        assert response.status_code == 200
    
    @pytest.mark.slow
    def test_run_scraper_handles_errors_gracefully(self, client, app):
        """Test that scraper handles errors gracefully."""
        # This test might be slow if it actually tries to scrape
        response = client.post(
            '/api/run-scraper',
            json={'mode': 'real'},
            content_type='application/json'
        )
        # Should return either success or error, not crash
        assert response.status_code in [200, 500]
        if response.status_code == 500:
            data = response.get_json()
            assert 'error' in data

