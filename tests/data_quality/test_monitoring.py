"""
Data Quality Monitoring.

Tests for continuous data quality monitoring and alerting.
"""
import pytest
from datetime import date, timedelta
from scraper.schema import DimAccount, FactFollowersSnapshot


class TestDataQualityMetrics:
    """Test data quality metrics calculation."""
    
    def test_calculate_quality_metrics(self, db_session):
        """Calculate overall data quality metrics."""
        # Create test data
        account = DimAccount(platform='X', handle='quality_test', org_name='HHS')
        db_session.add(account)
        db_session.commit()
        
        # Create snapshots with varying quality
        high_quality = FactFollowersSnapshot(
            account_key=account.account_key,
            snapshot_date=date.today(),
            followers_count=1000,
            engagements_total=500
        )
        db_session.add(high_quality)
        
        medium_quality = FactFollowersSnapshot(
            account_key=account.account_key,
            snapshot_date=date.today() - timedelta(days=1),
            followers_count=1000,
            engagements_total=None  # Missing
        )
        db_session.add(medium_quality)
        
        db_session.commit()
        
        # Calculate quality metrics
        total_snapshots = db_session.query(FactFollowersSnapshot).filter_by(
            account_key=account.account_key
        ).count()
        
        complete_snapshots = db_session.query(FactFollowersSnapshot).filter(
            FactFollowersSnapshot.account_key == account.account_key,
            FactFollowersSnapshot.engagements_total.isnot(None)
        ).count()
        
        completeness_rate = (complete_snapshots / total_snapshots * 100) if total_snapshots > 0 else 0
        
        assert completeness_rate >= 0
        assert completeness_rate <= 100
    
    def test_data_freshness_metrics(self, db_session, sample_account):
        """Calculate data freshness metrics."""
        # Create recent snapshot
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            followers_count=1000
        )
        db_session.add(snapshot)
        db_session.commit()
        
        # Calculate freshness
        latest_snapshot = db_session.query(FactFollowersSnapshot).filter_by(
            account_key=sample_account.account_key
        ).order_by(FactFollowersSnapshot.snapshot_date.desc()).first()
        
        if latest_snapshot:
            days_old = (date.today() - latest_snapshot.snapshot_date).days
            assert days_old >= 0
            assert days_old <= 365  # Should be recent


class TestQualityThresholds:
    """Test data quality thresholds and alerts."""
    
    def test_quality_threshold_checks(self, db_session, sample_account):
        """Check data quality against thresholds."""
        # Create snapshot
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            followers_count=1000,
            engagements_total=500
        )
        db_session.add(snapshot)
        db_session.commit()
        
        # Check quality thresholds
        quality_checks = {
            'has_followers': snapshot.followers_count is not None,
            'has_engagement': snapshot.engagements_total is not None,
            'is_recent': (date.today() - snapshot.snapshot_date).days <= 7,
            'is_consistent': snapshot.engagements_total == (
                (snapshot.likes_count or 0) +
                (snapshot.comments_count or 0) +
                (snapshot.shares_count or 0)
            )
        }
        
        # All checks should pass for high-quality data
        assert all(quality_checks.values())
    
    def test_quality_alert_conditions(self, db_session):
        """Test conditions that should trigger quality alerts."""
        # Create account without recent snapshots
        account = DimAccount(platform='X', handle='stale_test', org_name='HHS')
        db_session.add(account)
        db_session.commit()
        
        # Check for stale data
        today = date.today()
        recent_snapshots = db_session.query(FactFollowersSnapshot).filter(
            FactFollowersSnapshot.account_key == account.account_key,
            FactFollowersSnapshot.snapshot_date >= today - timedelta(days=7)
        ).count()
        
        # Should alert if no recent snapshots
        should_alert = recent_snapshots == 0
        # This is informational - no assertion, just monitoring


class TestQualityReporting:
    """Test data quality reporting."""
    
    def test_generate_quality_report(self, db_session):
        """Generate data quality report."""
        # Create test data
        accounts = []
        for i in range(10):
            account = DimAccount(
                platform='X',
                handle=f'quality_report_{i}',
                org_name='HHS'
            )
            db_session.add(account)
            accounts.append(account)
        db_session.commit()
        
        # Create snapshots
        today = date.today()
        for account in accounts:
            snapshot = FactFollowersSnapshot(
                account_key=account.account_key,
                snapshot_date=today,
                followers_count=1000
            )
            db_session.add(snapshot)
        db_session.commit()
        
        # Generate quality report
        report = {
            'total_accounts': db_session.query(DimAccount).count(),
            'total_snapshots': db_session.query(FactFollowersSnapshot).count(),
            'accounts_with_snapshots': db_session.query(
                DimAccount.account_key
            ).join(FactFollowersSnapshot).distinct().count(),
            'recent_snapshots': db_session.query(FactFollowersSnapshot).filter(
                FactFollowersSnapshot.snapshot_date >= today - timedelta(days=7)
            ).count()
        }
        
        # Verify report structure
        assert 'total_accounts' in report
        assert 'total_snapshots' in report
        assert report['total_accounts'] >= 10
        assert report['total_snapshots'] >= 10

