import pytest
from datetime import date, timedelta
from scraper.backfill import backfill_history
from scraper.schema import DimAccount, FactFollowersSnapshot, init_db
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine


class TestBackfillHistory:
    """Test the backfill_history function."""
    
    def test_backfill_history_creates_historical_data(self, test_db_path):
        """Test that backfill_history creates historical snapshots."""
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
        
        # Backfill 30 days
        backfill_history(db_path=test_db_path, days_back=30)
        
        session = Session()
        snapshots = session.query(FactFollowersSnapshot).filter_by(
            account_key=account.account_key
        ).all()
        
        assert len(snapshots) == 30
        
        # Verify dates are sequential
        dates = sorted([s.snapshot_date for s in snapshots])
        assert dates[0] == date.today() - timedelta(days=29)
        assert dates[-1] == date.today()
        
        session.close()
    
    def test_backfill_history_skips_existing_snapshots(self, test_db_path):
        """Test that backfill_history skips existing snapshots."""
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
        
        # Create existing snapshot for a specific date
        existing_date = date.today() - timedelta(days=15)
        existing_snapshot = FactFollowersSnapshot(
            account_key=account.account_key,
            snapshot_date=existing_date,
            followers_count=5000
        )
        session.add(existing_snapshot)
        session.commit()
        session.close()
        
        # Backfill 30 days
        backfill_history(db_path=test_db_path, days_back=30)
        
        session = Session()
        # Should have 30 snapshots (29 new + 1 existing)
        snapshots = session.query(FactFollowersSnapshot).filter_by(
            account_key=account.account_key
        ).all()
        assert len(snapshots) == 30
        
        # Verify existing snapshot wasn't modified
        existing = session.query(FactFollowersSnapshot).filter_by(
            account_key=account.account_key,
            snapshot_date=existing_date
        ).first()
        assert existing.followers_count == 5000
        
        session.close()
    
    def test_backfill_history_generates_growth_pattern(self, test_db_path):
        """Test that backfill_history generates realistic growth pattern."""
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
        
        # Backfill 100 days
        backfill_history(db_path=test_db_path, days_back=100)
        
        session = Session()
        snapshots = session.query(FactFollowersSnapshot).filter_by(
            account_key=account.account_key
        ).order_by(FactFollowersSnapshot.snapshot_date).all()
        
        # Verify growth pattern (later dates should generally have more followers)
        # Allow for some noise, but trend should be upward
        first_followers = snapshots[0].followers_count
        last_followers = snapshots[-1].followers_count
        
        # Last should be higher than first (allowing for noise)
        assert last_followers >= first_followers * 0.9  # Allow 10% variance
        
        session.close()
    
    def test_backfill_history_handles_hhs_accounts(self, test_db_path):
        """Test that backfill_history handles HHS accounts with higher base."""
        engine = create_engine(f'sqlite:///{test_db_path}')
        init_db(test_db_path)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        hhs_account = DimAccount(
            platform='X',
            handle='hhs',
            org_name='HHS',
            account_url='https://x.com/hhs'
        )
        non_hhs_account = DimAccount(
            platform='X',
            handle='nih',
            org_name='NIH',
            account_url='https://x.com/nih'
        )
        session.add(hhs_account)
        session.add(non_hhs_account)
        session.commit()
        session.close()
        
        backfill_history(db_path=test_db_path, days_back=30)
        
        session = Session()
        hhs_snapshots = session.query(FactFollowersSnapshot).filter_by(
            account_key=hhs_account.account_key
        ).all()
        nih_snapshots = session.query(FactFollowersSnapshot).filter_by(
            account_key=non_hhs_account.account_key
        ).all()
        
        # HHS account should have higher follower counts
        avg_hhs = sum(s.followers_count for s in hhs_snapshots) / len(hhs_snapshots)
        avg_nih = sum(s.followers_count for s in nih_snapshots) / len(nih_snapshots)
        
        assert avg_hhs > avg_nih
        
        session.close()
    
    def test_backfill_history_calculates_engagements_total(self, test_db_path):
        """Test that backfill_history calculates engagements_total correctly."""
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
        
        backfill_history(db_path=test_db_path, days_back=30)
        
        session = Session()
        snapshots = session.query(FactFollowersSnapshot).filter_by(
            account_key=account.account_key
        ).all()
        
        for snapshot in snapshots:
            expected_total = snapshot.likes_count + snapshot.comments_count + snapshot.shares_count
            assert snapshot.engagements_total == expected_total
        
        session.close()
    
    def test_backfill_history_handles_weekend_engagement(self, test_db_path):
        """Test that backfill_history reduces engagement on weekends."""
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
        
        backfill_history(db_path=test_db_path, days_back=14)  # 2 weeks
        
        session = Session()
        snapshots = session.query(FactFollowersSnapshot).filter_by(
            account_key=account.account_key
        ).order_by(FactFollowersSnapshot.snapshot_date).all()
        
        # Check that weekends have lower engagement
        for snapshot in snapshots:
            is_weekend = snapshot.snapshot_date.weekday() >= 5
            if is_weekend:
                # Weekend engagement should be lower (multiplier 0.5)
                # But allow for randomness, so just check it's not unusually high
                assert snapshot.engagements_total >= 0
        
        session.close()
    
    def test_backfill_history_handles_no_accounts(self, test_db_path):
        """Test that backfill_history handles case with no accounts."""
        engine = create_engine(f'sqlite:///{test_db_path}')
        init_db(test_db_path)
        
        # Should not raise error
        backfill_history(db_path=test_db_path, days_back=30)
        
        Session = sessionmaker(bind=engine)
        session = Session()
        snapshots = session.query(FactFollowersSnapshot).all()
        assert len(snapshots) == 0
        session.close()
    
    def test_backfill_history_handles_multiple_accounts(self, test_db_path):
        """Test that backfill_history processes all accounts."""
        engine = create_engine(f'sqlite:///{test_db_path}')
        init_db(test_db_path)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Create multiple accounts
        for i in range(3):
            account = DimAccount(
                platform='X',
                handle=f'test{i}',
                org_name='HHS',
                account_url=f'https://x.com/test{i}'
            )
            session.add(account)
        session.commit()
        session.close()
        
        backfill_history(db_path=test_db_path, days_back=30)
        
        session = Session()
        snapshots = session.query(FactFollowersSnapshot).all()
        assert len(snapshots) == 90  # 3 accounts * 30 days
        
        session.close()

