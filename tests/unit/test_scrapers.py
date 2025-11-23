import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date
from scraper.scrapers import SimulatedScraper, RealScraper, get_scraper, BaseScraper
from scraper.schema import DimAccount


class TestBaseScraper:
    """Test the abstract base scraper class."""
    
    def test_base_scraper_is_abstract(self):
        """Test that BaseScraper cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseScraper()


class TestSimulatedScraper:
    """Test the SimulatedScraper class."""
    
    def test_simulated_scraper_returns_data(self):
        """Test that SimulatedScraper returns valid data structure."""
        scraper = SimulatedScraper()
        account = DimAccount(
            platform='X',
            handle='test',
            org_name='HHS',
            account_url='https://x.com/test'
        )
        result = scraper.scrape(account)
        
        assert result is not None
        assert 'followers_count' in result
        assert 'following_count' in result
        assert 'posts_count' in result
        assert 'likes_count' in result
        assert 'comments_count' in result
        assert 'shares_count' in result
        assert result['followers_count'] > 0
    
    def test_simulated_scraper_hhs_account_has_high_followers(self):
        """Test that HHS accounts get higher base follower count."""
        scraper = SimulatedScraper()
        hhs_account = DimAccount(
            platform='X',
            handle='hhs',
            org_name='HHS',
            account_url='https://x.com/hhs'
        )
        result = scraper.scrape(hhs_account)
        
        # HHS should have base of 500000, so result should be close to that
        assert result['followers_count'] >= 499900  # 500000 - 100
    
    def test_simulated_scraper_non_hhs_account(self):
        """Test that non-HHS accounts get lower base follower count."""
        scraper = SimulatedScraper()
        account = DimAccount(
            platform='X',
            handle='test',
            org_name='NIH',
            account_url='https://x.com/test'
        )
        result = scraper.scrape(account)
        
        # Non-HHS should have base of 10000
        assert result['followers_count'] >= 9900  # 10000 - 100
        assert result['followers_count'] <= 10500  # 10000 + 500
    
    def test_simulated_scraper_returns_all_required_fields(self):
        """Test that all required fields are present in result."""
        scraper = SimulatedScraper()
        account = DimAccount(
            platform='Instagram',
            handle='test',
            org_name='CDC',
            account_url='https://instagram.com/test'
        )
        result = scraper.scrape(account)
        
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


class TestRealScraper:
    """Test the RealScraper class."""
    
    @patch('scraper.scrapers.XScraper')
    def test_real_scraper_success(self, mock_x_scraper_class):
        """Test RealScraper when platform scraper succeeds."""
        # Mock platform scraper
        mock_scraper = Mock()
        mock_scraper.scrape.return_value = {
            'followers_count': 12345,
            'following_count': 100,
            'posts_count': 1
        }
        mock_x_scraper_class.return_value = mock_scraper
        
        scraper = RealScraper()
        account = DimAccount(
            platform='x',  # Use lowercase to match platform mapping
            handle='test',
            org_name='HHS',
            account_url='https://x.com/test'
        )
        result = scraper.scrape(account)
        
        assert result is not None
        assert 'followers_count' in result
        assert result['followers_count'] == 12345
        mock_scraper.scrape.assert_called_once()
    
    def test_real_scraper_handles_unsupported_platform(self):
        """Test RealScraper when platform is not supported."""
        scraper = RealScraper()
        account = DimAccount(
            platform='UnknownPlatform',
            handle='test',
            org_name='HHS',
            account_url='https://unknown.com/test'
        )
        result = scraper.scrape(account)
        
        assert result is None
    
    @patch('scraper.scrapers.XScraper')
    def test_real_scraper_handles_scraper_failure(self, mock_x_scraper_class):
        """Test RealScraper when platform scraper returns None."""
        # Mock platform scraper that returns None
        mock_scraper = Mock()
        mock_scraper.scrape.return_value = None
        mock_x_scraper_class.return_value = mock_scraper
        
        scraper = RealScraper()
        account = DimAccount(
            platform='x',  # Use lowercase
            handle='test',
            org_name='HHS',
            account_url='https://x.com/test'
        )
        result = scraper.scrape(account)
        
        assert result is None
    
    @patch('scraper.scrapers.XScraper')
    def test_real_scraper_handles_exception(self, mock_x_scraper_class):
        """Test RealScraper when platform scraper raises exception."""
        # Mock platform scraper that raises exception
        mock_scraper = Mock()
        mock_scraper.scrape.side_effect = Exception("Scraper error")
        mock_x_scraper_class.return_value = mock_scraper
        
        scraper = RealScraper()
        account = DimAccount(
            platform='x',  # Use lowercase
            handle='test',
            org_name='HHS',
            account_url='https://x.com/test'
        )
        result = scraper.scrape(account)
        
        assert result is None


class TestGetScraper:
    """Test the get_scraper factory function."""
    
    def test_get_scraper_returns_simulated_by_default(self):
        """Test that get_scraper returns SimulatedScraper by default."""
        scraper = get_scraper()
        assert isinstance(scraper, SimulatedScraper)
    
    def test_get_scraper_returns_simulated_when_specified(self):
        """Test that get_scraper returns SimulatedScraper when mode='simulated'."""
        scraper = get_scraper('simulated')
        assert isinstance(scraper, SimulatedScraper)
    
    def test_get_scraper_returns_real_when_specified(self):
        """Test that get_scraper returns RealScraper when mode='real'."""
        scraper = get_scraper('real')
        assert isinstance(scraper, RealScraper)
    
    def test_get_scraper_handles_unknown_mode(self):
        """Test that get_scraper defaults to simulated for unknown modes."""
        scraper = get_scraper('unknown_mode')
        assert isinstance(scraper, SimulatedScraper)

