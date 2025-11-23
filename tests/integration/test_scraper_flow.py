import pytest
from datetime import date
from scraper.extract_accounts import populate_accounts
from scraper.collect_metrics import simulate_metrics
from scraper.schema import DimAccount, FactFollowersSnapshot, init_db
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import json
import os


class TestFullScraperFlow:
    """Test the complete scraper execution flow."""
    
    def test_extract_accounts_to_metrics_collection(self, test_db_path):
        """Test full flow from account extraction to metrics collection."""
        # Initialize database
        engine = create_engine(f'sqlite:///{test_db_path}')
        init_db(test_db_path)
        
        # Create test JSON file
        accounts_data = [
            {
                'platform': 'X',
                'url': 'https://x.com/test1',
                'organization': 'HHS'
            },
            {
                'platform': 'Instagram',
                'url': 'https://instagram.com/test2',
                'organization': 'NIH'
            }
        ]
        
        json_path = os.path.join(os.path.dirname(test_db_path), 'test_flow_accounts.json')
        with open(json_path, 'w') as f:
            json.dump(accounts_data, f)
        
        try:
            # Step 1: Extract accounts
            populate_accounts(json_path=json_path, db_path=test_db_path)
            
            # Verify accounts were created
            Session = sessionmaker(bind=engine)
            session = Session()
            accounts = session.query(DimAccount).all()
            assert len(accounts) == 2
            session.close()
            
            # Step 2: Collect metrics
            simulate_metrics(db_path=test_db_path, mode='simulated')
            
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
        finally:
            if os.path.exists(json_path):
                os.unlink(json_path)
    
    def test_scraper_flow_with_existing_snapshots(self, test_db_path):
        """Test that scraper flow skips existing snapshots."""
        engine = create_engine(f'sqlite:///{test_db_path}')
        init_db(test_db_path)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Create account with existing snapshot
        account = DimAccount(
            platform='X',
            handle='test',
            org_name='HHS',
            account_url='https://x.com/test'
        )
        session.add(account)
        session.commit()
        
        existing_snapshot = FactFollowersSnapshot(
            account_key=account.account_key,
            snapshot_date=date.today(),
            followers_count=5000
        )
        session.add(existing_snapshot)
        session.commit()
        session.close()
        
        # Run metrics collection
        simulate_metrics(db_path=test_db_path, mode='simulated')
        
        # Verify only one snapshot exists (existing one wasn't duplicated)
        session = Session()
        snapshots = session.query(FactFollowersSnapshot).filter_by(
            account_key=account.account_key,
            snapshot_date=date.today()
        ).all()
        assert len(snapshots) == 1
        assert snapshots[0].followers_count == 5000  # Original value preserved
        session.close()
    
    def test_scraper_flow_handles_multiple_accounts(self, test_db_path):
        """Test scraper flow with multiple accounts."""
        engine = create_engine(f'sqlite:///{test_db_path}')
        init_db(test_db_path)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Create multiple accounts
        platforms = ['X', 'Instagram', 'Facebook', 'YouTube']
        for platform in platforms:
            account = DimAccount(
                platform=platform,
                handle=f'test_{platform.lower()}',
                org_name='HHS',
                account_url=f'https://{platform.lower()}.com/test'
            )
            session.add(account)
        session.commit()
        session.close()
        
        # Collect metrics
        simulate_metrics(db_path=test_db_path, mode='simulated')
        
        # Verify all accounts have snapshots
        session = Session()
        snapshots = session.query(FactFollowersSnapshot).all()
        assert len(snapshots) == 4
        
        # Verify each account has exactly one snapshot
        accounts = session.query(DimAccount).all()
        for account in accounts:
            account_snapshots = [s for s in snapshots if s.account_key == account.account_key]
            assert len(account_snapshots) == 1
        
        session.close()
    
    def test_scraper_flow_error_handling(self, test_db_path):
        """Test that scraper flow handles errors gracefully."""
        engine = create_engine(f'sqlite:///{test_db_path}')
        init_db(test_db_path)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Create account
        account = DimAccount(
            platform='X',
            handle='test',
            org_name='HHS',
            account_url='https://x.com/test'
        )
        session.add(account)
        session.commit()
        session.close()
        
        # Run with real mode (may fail, but shouldn't crash)
        try:
            simulate_metrics(db_path=test_db_path, mode='real')
        except Exception:
            # Should handle errors gracefully
            pass
        
        # Database should still be in valid state
        session = Session()
        accounts = session.query(DimAccount).all()
        assert len(accounts) == 1
        session.close()
    
    def test_scraper_flow_data_persistence(self, test_db_path):
        """Test that scraper flow persists data correctly."""
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
        account_key = account.account_key
        session.close()
        
        # Collect metrics
        simulate_metrics(db_path=test_db_path, mode='simulated')
        
        # Verify data persists across sessions
        session = Session()
        snapshot = session.query(FactFollowersSnapshot).filter_by(
            account_key=account_key
        ).first()
        
        assert snapshot is not None
        assert snapshot.followers_count > 0
        assert snapshot.snapshot_date == date.today()
        
        session.close()


class TestAccountExtractionFlow:
    """Test account extraction flow."""
    
    def test_extract_accounts_creates_all_accounts(self, test_db_path):
        """Test that extract_accounts creates all accounts from JSON."""
        engine = create_engine(f'sqlite:///{test_db_path}')
        init_db(test_db_path)
        
        accounts_data = [
            {'platform': 'X', 'url': 'https://x.com/test1', 'organization': 'HHS'},
            {'platform': 'Instagram', 'url': 'https://instagram.com/test2', 'organization': 'NIH'},
            {'platform': 'Facebook', 'url': 'https://facebook.com/test3', 'organization': 'CDC'}
        ]
        
        json_path = os.path.join(os.path.dirname(test_db_path), 'test_extract.json')
        with open(json_path, 'w') as f:
            json.dump(accounts_data, f)
        
        try:
            populate_accounts(json_path=json_path, db_path=test_db_path)
            
            Session = sessionmaker(bind=engine)
            session = Session()
            accounts = session.query(DimAccount).all()
            assert len(accounts) == 3
            
            # Verify account details
            x_account = session.query(DimAccount).filter_by(platform='X').first()
            assert x_account.handle == 'test1'
            assert x_account.org_name == 'HHS'
            assert x_account.is_core_account is True
            
            session.close()
        finally:
            if os.path.exists(json_path):
                os.unlink(json_path)
    
    def test_extract_accounts_handles_duplicates(self, test_db_path):
        """Test that extract_accounts handles duplicate accounts."""
        engine = create_engine(f'sqlite:///{test_db_path}')
        init_db(test_db_path)
        
        accounts_data = [
            {'platform': 'X', 'url': 'https://x.com/test', 'organization': 'HHS'}
        ]
        
        json_path = os.path.join(os.path.dirname(test_db_path), 'test_duplicate.json')
        with open(json_path, 'w') as f:
            json.dump(accounts_data, f)
        
        try:
            # First extraction
            populate_accounts(json_path=json_path, db_path=test_db_path)
            
            # Second extraction (should skip duplicates)
            populate_accounts(json_path=json_path, db_path=test_db_path)
            
            Session = sessionmaker(bind=engine)
            session = Session()
            accounts = session.query(DimAccount).filter_by(handle='test').all()
            assert len(accounts) == 1  # Should only have one
            
            session.close()
        finally:
            if os.path.exists(json_path):
                os.unlink(json_path)

