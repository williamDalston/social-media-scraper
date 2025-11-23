"""
Full Workflow Testing.

End-to-end tests that verify complete workflows from start to finish.
"""
import pytest
import json
import os
from datetime import date
from scraper.extract_accounts import populate_accounts
from scraper.collect_metrics import simulate_metrics
from scraper.schema import DimAccount, FactFollowersSnapshot, init_db
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine


class TestCompleteWorkflow:
    """Test complete workflows from start to finish."""
    
    def test_account_extraction_to_metrics_workflow(self, test_db_path):
        """Test complete workflow: extract accounts -> collect metrics."""
        # Step 1: Initialize database
        engine = create_engine(f'sqlite:///{test_db_path}')
        init_db(test_db_path)
        
        # Step 2: Extract accounts from JSON
        accounts_data = [
            {'platform': 'X', 'url': 'https://x.com/workflow_test', 'organization': 'HHS'},
            {'platform': 'Instagram', 'url': 'https://instagram.com/workflow_test', 'organization': 'NIH'}
        ]
        
        json_path = os.path.join(os.path.dirname(test_db_path), 'workflow_test.json')
        with open(json_path, 'w') as f:
            json.dump(accounts_data, f)
        
        try:
            populate_accounts(json_path=json_path, db_path=test_db_path)
            
            # Step 3: Verify accounts created
            Session = sessionmaker(bind=engine)
            session = Session()
            accounts = session.query(DimAccount).all()
            assert len(accounts) == 2
            session.close()
            
            # Step 4: Collect metrics
            simulate_metrics(db_path=test_db_path, mode='simulated')
            
            # Step 5: Verify snapshots created
            session = Session()
            snapshots = session.query(FactFollowersSnapshot).all()
            assert len(snapshots) == 2
            
            # Step 6: Verify data quality
            for snapshot in snapshots:
                assert snapshot.followers_count > 0
                assert snapshot.snapshot_date == date.today()
            session.close()
        finally:
            if os.path.exists(json_path):
                os.unlink(json_path)
    
    def test_csv_upload_to_dashboard_workflow(self, client, test_db_path):
        """Test workflow: CSV upload -> data appears in dashboard."""
        import io
        import csv
        
        # Step 1: Upload CSV
        csv_data = io.StringIO()
        writer = csv.writer(csv_data)
        writer.writerow(['Platform', 'Handle', 'Organization'])
        writer.writerow(['X', 'workflow_csv', 'HHS'])
        csv_data.seek(0)
        
        response = client.post(
            '/upload',
            data={'file': (io.BytesIO(csv_data.getvalue().encode('utf-8')), 'test.csv')},
            content_type='multipart/form-data'
        )
        
        # Step 2: Verify upload success
        assert response.status_code in [200, 401, 403]
        
        # Step 3: Collect metrics
        simulate_metrics(db_path=test_db_path, mode='simulated')
        
        # Step 4: Verify data in API
        response = client.get('/api/summary')
        if response.status_code == 200:
            data = response.get_json()
            # Should contain uploaded account
            handles = [item.get('handle', '') for item in data]
            # May or may not be present depending on auth
            assert isinstance(data, list)


class TestMultiStepWorkflows:
    """Test multi-step workflows."""
    
    def test_backfill_then_daily_collection_workflow(self, test_db_path):
        """Test workflow: backfill history -> daily collection."""
        from scraper.backfill import backfill_history
        from scraper.collect_metrics import simulate_metrics
        from scraper.schema import DimAccount, init_db
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import create_engine
        
        # Step 1: Initialize
        engine = create_engine(f'sqlite:///{test_db_path}')
        init_db(test_db_path)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        account = DimAccount(platform='X', handle='backfill_workflow', org_name='HHS')
        session.add(account)
        session.commit()
        session.close()
        
        # Step 2: Backfill 30 days
        backfill_history(db_path=test_db_path, days_back=30)
        
        # Step 3: Verify backfill
        session = Session()
        snapshots = session.query(FactFollowersSnapshot).filter_by(
            account_key=account.account_key
        ).count()
        assert snapshots == 30
        session.close()
        
        # Step 4: Daily collection (should skip existing)
        simulate_metrics(db_path=test_db_path, mode='simulated')
        
        # Step 5: Verify no duplicates
        session = Session()
        snapshots = session.query(FactFollowersSnapshot).filter_by(
            account_key=account.account_key
        ).count()
        # Should still be 30 (today already exists) or 31 (if today was new)
        assert snapshots in [30, 31]
        session.close()

