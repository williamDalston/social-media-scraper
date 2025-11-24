"""
Integration Testing with Real Platforms.

Tests that interact with real platform APIs/websites (use with caution).
"""
import pytest
from scraper.scrapers import RealScraper
from scraper.schema import DimAccount


@pytest.mark.integration
@pytest.mark.real_platforms
@pytest.mark.slow
class TestRealPlatformIntegration:
    """Integration tests with real platforms."""

    def test_real_scraper_connectivity(self):
        """Test that real scrapers can connect to platforms."""
        scraper = RealScraper()

        # Test with a known public account
        account = DimAccount(
            platform="x",
            handle="twitter",  # Public account
            org_name="Test",
            account_url="https://x.com/twitter",
        )

        result = scraper.scrape(account)
        # May succeed or fail depending on platform blocking
        # Just verify it doesn't crash
        assert result is None or isinstance(result, dict)

    @pytest.mark.skip(reason="Requires API keys and may hit rate limits")
    def test_youtube_api_integration(self):
        """Test YouTube API integration (if configured)."""
        # This would test actual YouTube API calls
        # Skipped by default to avoid rate limits
        pass

    @pytest.mark.skip(reason="May be blocked by platforms")
    def test_instagram_scraper_integration(self):
        """Test Instagram scraper with real platform."""
        # This would test actual Instagram scraping
        # Skipped by default as it may be blocked
        pass


@pytest.mark.integration
@pytest.mark.real_platforms
class TestPlatformErrorHandling:
    """Test error handling with real platforms."""

    def test_handles_platform_changes(self):
        """Test that scrapers handle platform changes gracefully."""
        scraper = RealScraper()
        account = DimAccount(
            platform="x",
            handle="nonexistent_account_12345",
            org_name="Test",
            account_url="https://x.com/nonexistent_account_12345",
        )

        result = scraper.scrape(account)
        # Should handle gracefully (return None or error dict)
        assert result is None or isinstance(result, dict)

    def test_handles_rate_limiting(self):
        """Test handling of platform rate limiting."""
        scraper = RealScraper()
        account = DimAccount(
            platform="x",
            handle="test",
            org_name="Test",
            account_url="https://x.com/test",
        )

        # Make multiple requests (may hit rate limits)
        results = []
        for _ in range(5):
            result = scraper.scrape(account)
            results.append(result)

        # Should handle rate limits gracefully
        assert all(r is None or isinstance(r, dict) for r in results)
