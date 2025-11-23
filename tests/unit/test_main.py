"""
Tests for scraper/main.py CLI interface.
"""
import pytest
from unittest.mock import patch, MagicMock
import sys

# Import after checking if it exists
try:
    from scraper.main import main
    MAIN_AVAILABLE = True
except ImportError:
    MAIN_AVAILABLE = False


@pytest.mark.skipif(not MAIN_AVAILABLE, reason="main module not available")
class TestMainCLI:
    """Test the main CLI interface."""
    
    @patch('scraper.main.init_db')
    @patch('scraper.main.populate_accounts')
    @patch('scraper.main.simulate_metrics')
    def test_main_init_db(self, mock_metrics, mock_populate, mock_init):
        """Test --init-db flag."""
        with patch.object(sys, 'argv', ['main.py', '--init-db']):
            main()
            mock_init.assert_called_once()
            mock_populate.assert_not_called()
            mock_metrics.assert_not_called()
    
    @patch('scraper.main.init_db')
    @patch('scraper.main.populate_accounts')
    @patch('scraper.main.simulate_metrics')
    def test_main_extract_accounts(self, mock_metrics, mock_populate, mock_init):
        """Test --extract-accounts flag."""
        with patch.object(sys, 'argv', ['main.py', '--extract-accounts']):
            main()
            mock_init.assert_not_called()
            mock_populate.assert_called_once()
            mock_metrics.assert_not_called()
    
    @patch('scraper.main.init_db')
    @patch('scraper.main.populate_accounts')
    @patch('scraper.main.simulate_metrics')
    def test_main_collect_daily(self, mock_metrics, mock_populate, mock_init):
        """Test --collect-daily flag."""
        with patch.object(sys, 'argv', ['main.py', '--collect-daily']):
            main()
            mock_init.assert_not_called()
            mock_populate.assert_not_called()
            mock_metrics.assert_called_once()
    
    @patch('scraper.main.init_db')
    @patch('scraper.main.populate_accounts')
    @patch('scraper.main.simulate_metrics')
    def test_main_all(self, mock_metrics, mock_populate, mock_init):
        """Test --all flag runs all steps."""
        with patch.object(sys, 'argv', ['main.py', '--all']):
            main()
            mock_init.assert_called_once()
            mock_populate.assert_called_once()
            mock_metrics.assert_called_once()
    
    @patch('scraper.main.init_db')
    @patch('scraper.main.populate_accounts')
    @patch('scraper.main.simulate_metrics')
    def test_main_no_args(self, mock_metrics, mock_populate, mock_init):
        """Test main with no arguments does nothing."""
        with patch.object(sys, 'argv', ['main.py']):
            main()
            mock_init.assert_not_called()
            mock_populate.assert_not_called()
            mock_metrics.assert_not_called()

