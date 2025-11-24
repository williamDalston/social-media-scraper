"""
Property-based tests for scrapers using Hypothesis.
"""
from hypothesis import given, strategies as st
from scraper.scrapers import SimulatedScraper, get_scraper
from scraper.schema import DimAccount
from datetime import date


@given(
    org_name=st.text(min_size=1, max_size=100),
    platform=st.sampled_from(["X", "Instagram", "Facebook", "LinkedIn", "YouTube"]),
)
def test_simulated_scraper_always_returns_positive_values(org_name, platform):
    """Property: Simulated scraper always returns positive integer values."""
    scraper = SimulatedScraper()
    account = DimAccount(platform=platform, handle="test", org_name=org_name)
    result = scraper.scrape(account)

    # All counts should be non-negative integers
    assert result["followers_count"] >= 0
    assert result["following_count"] >= 0
    assert result["posts_count"] >= 0
    assert result["likes_count"] >= 0
    assert result["comments_count"] >= 0
    assert result["shares_count"] >= 0

    # All values should be integers
    assert isinstance(result["followers_count"], int)
    assert isinstance(result["following_count"], int)
    assert isinstance(result["posts_count"], int)


@given(
    handle=st.text(
        min_size=1,
        max_size=50,
        alphabet=st.characters(whitelist_categories=("L", "N", "_")),
    )
)
def test_get_scraper_returns_scraper(handle):
    """Property: get_scraper always returns a scraper instance."""
    scraper = get_scraper("simulated")
    assert scraper is not None
    assert hasattr(scraper, "scrape")

    # Should work with any valid handle
    account = DimAccount(platform="X", handle=handle, org_name="Test")
    result = scraper.scrape(account)
    assert result is not None
    assert isinstance(result, dict)


@given(base_followers=st.integers(min_value=0, max_value=10000000))
def test_scraper_followers_within_reasonable_range(base_followers):
    """Property: Scraper results should be within reasonable bounds."""
    scraper = SimulatedScraper()
    account = DimAccount(
        platform="X",
        handle="test",
        org_name="HHS" if base_followers > 100000 else "Other",
    )
    result = scraper.scrape(account)

    # Followers should be reasonable (not negative, not impossibly large)
    assert 0 <= result["followers_count"] < 10**9  # Less than 1 billion
    assert 0 <= result["following_count"] < 10**6  # Less than 1 million
    assert 0 <= result["posts_count"] < 10**5  # Less than 100k posts
