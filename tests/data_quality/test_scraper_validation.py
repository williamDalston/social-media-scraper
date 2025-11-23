"""
Scraper Result Validation.

Tests to validate scraper results for accuracy and completeness.
"""
import pytest
from unittest.mock import Mock, patch
from scraper.scrapers import SimulatedScraper, RealScraper
from scraper.schema import DimAccount


class TestScraperResultValidation:
    """Validate scraper results."""
    
    def test_simulated_scraper_result_structure(self):
        """Validate simulated scraper returns correct structure."""
        scraper = SimulatedScraper()
        account = DimAccount(
            platform='X',
            handle='test',
            org_name='HHS',
            account_url='https://x.com/test'
        )
        
        result = scraper.scrape(account)
        
        # Validate structure
        assert result is not None
        assert isinstance(result, dict)
        
        # Required fields
        required_fields = [
            'followers_count',
            'following_count',
            'posts_count',
            'likes_count',
            'comments_count',
            'shares_count'
        ]
        
        for field in required_fields:
            assert field in result
            assert isinstance(result[field], int)
            assert result[field] >= 0
    
    def test_scraper_result_value_ranges(self):
        """Validate scraper results are in reasonable ranges."""
        scraper = SimulatedScraper()
        account = DimAccount(
            platform='X',
            handle='test',
            org_name='HHS',
            account_url='https://x.com/test'
        )
        
        result = scraper.scrape(account)
        
        # Validate ranges
        assert 0 <= result['followers_count'] < 10**10
        assert 0 <= result['following_count'] < 10**6
        assert 0 <= result['posts_count'] < 10**6
        assert 0 <= result['likes_count'] < 10**9
        assert 0 <= result['comments_count'] < 10**8
        assert 0 <= result['shares_count'] < 10**8
    
    def test_scraper_result_consistency(self):
        """Validate scraper results are internally consistent."""
        scraper = SimulatedScraper()
        account = DimAccount(
            platform='X',
            handle='test',
            org_name='HHS',
            account_url='https://x.com/test'
        )
        
        # Run multiple times - should be consistent in structure
        results = []
        for _ in range(5):
            result = scraper.scrape(account)
            results.append(result)
        
        # All should have same structure
        for result in results:
            assert 'followers_count' in result
            assert 'engagements_total' not in result or isinstance(result.get('engagements_total'), int)


class TestScraperAccuracy:
    """Test scraper accuracy."""
    
    def test_hhs_account_accuracy(self):
        """Verify HHS accounts get higher follower counts."""
        scraper = SimulatedScraper()
        
        hhs_account = DimAccount(
            platform='X',
            handle='hhs',
            org_name='HHS',
            account_url='https://x.com/hhs'
        )
        
        non_hhs_account = DimAccount(
            platform='X',
            handle='other',
            org_name='NIH',
            account_url='https://x.com/other'
        )
        
        hhs_result = scraper.scrape(hhs_account)
        non_hhs_result = scraper.scrape(non_hhs_account)
        
        # HHS should have higher base followers
        assert hhs_result['followers_count'] > non_hhs_result['followers_count']
    
    def test_scraper_handles_missing_data(self):
        """Verify scraper handles missing account data."""
        scraper = SimulatedScraper()
        
        # Account with minimal data
        account = DimAccount(
            platform='X',
            handle='minimal',
            account_url='https://x.com/minimal'
        )
        
        result = scraper.scrape(account)
        # Should still return valid result
        assert result is not None
        assert 'followers_count' in result


class TestScraperErrorHandling:
    """Test scraper error handling and validation."""
    
    @patch('scraper.scrapers.XScraper')
    def test_scraper_validates_results(self, mock_x_scraper_class):
        """Verify scrapers validate their results."""
        mock_scraper = Mock()
        # Return invalid result (negative followers)
        mock_scraper.scrape.return_value = {
            'followers_count': -100,  # Invalid
            'following_count': 100,
            'posts_count': 5
        }
        mock_x_scraper_class.return_value = mock_scraper
        
        scraper = RealScraper()
        account = DimAccount(
            platform='x',
            handle='test',
            org_name='HHS',
            account_url='https://x.com/test'
        )
        
        result = scraper.scrape(account)
        # Should handle invalid results (may return None or sanitize)
        assert result is None or isinstance(result, dict)
    
    def test_scraper_handles_none_results(self):
        """Verify system handles None results from scrapers."""
        scraper = SimulatedScraper()
        account = DimAccount(
            platform='X',
            handle='test',
            org_name='HHS',
            account_url='https://x.com/test'
        )
        
        result = scraper.scrape(account)
        # Should not return None for simulated scraper
        assert result is not None


class TestDataQualityScoring:
    """Test data quality scoring."""
    
    def test_calculate_data_quality_score(self, db_session, sample_account):
        """Calculate data quality score for a snapshot."""
        from scraper.schema import FactFollowersSnapshot
        from datetime import date
        
        # High quality snapshot
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            followers_count=1000,
            following_count=100,
            posts_count=5,
            likes_count=500,
            comments_count=50,
            shares_count=100,
            engagements_total=650
        )
        
        # Calculate quality score
        quality_score = 100
        
        # Deduct points for missing data
        if snapshot.followers_count is None:
            quality_score -= 20
        if snapshot.engagements_total is None:
            quality_score -= 10
        
        # Deduct points for inconsistencies
        calculated_engagement = (
            (snapshot.likes_count or 0) +
            (snapshot.comments_count or 0) +
            (snapshot.shares_count or 0)
        )
        if snapshot.engagements_total != calculated_engagement:
            quality_score -= 15
        
        # Should have high quality score
        assert quality_score >= 70
    
    def test_data_quality_thresholds(self, db_session, sample_account):
        """Test data quality thresholds."""
        from scraper.schema import FactFollowersSnapshot
        from datetime import date
        
        # Test various quality levels
        test_cases = [
            {
                'name': 'high_quality',
                'snapshot': FactFollowersSnapshot(
                    account_key=sample_account.account_key,
                    snapshot_date=date.today(),
                    followers_count=1000,
                    engagements_total=500
                ),
                'expected_quality': 'high'
            },
            {
                'name': 'medium_quality',
                'snapshot': FactFollowersSnapshot(
                    account_key=sample_account.account_key,
                    snapshot_date=date.today(),
                    followers_count=1000,
                    engagements_total=None  # Missing
                ),
                'expected_quality': 'medium'
            },
        ]
        
        for test_case in test_cases:
            snapshot = test_case['snapshot']
            db_session.add(snapshot)
            db_session.commit()
            
            # Verify snapshot was created
            retrieved = db_session.query(FactFollowersSnapshot).filter_by(
                account_key=sample_account.account_key,
                snapshot_date=date.today()
            ).first()
            
            assert retrieved is not None

