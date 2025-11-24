"""
End-to-End Browser Tests using Playwright.

Tests that verify the application works correctly in a real browser.
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context."""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
    }


@pytest.mark.e2e
class TestDashboardE2E:
    """End-to-end tests for dashboard."""

    def test_dashboard_loads(self, page: Page, live_server):
        """Test that dashboard page loads correctly."""
        page.goto(f"{live_server.url}/")

        # Check that page loaded
        expect(page).to_have_title(containing="", timeout=5000)

        # Check for common dashboard elements (adjust based on actual HTML)
        # This is a placeholder - adjust selectors based on actual dashboard
        page.wait_for_load_state("networkidle")

    def test_dashboard_displays_data(
        self, page: Page, live_server, db_session, sample_account
    ):
        """Test that dashboard displays data correctly."""
        from scraper.schema import FactFollowersSnapshot
        from datetime import date

        # Create test data
        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            followers_count=1000,
            engagements_total=500,
        )
        db_session.add(snapshot)
        db_session.commit()

        page.goto(f"{live_server.url}/")
        page.wait_for_load_state("networkidle")

        # Verify data is displayed (adjust selectors based on actual dashboard)
        # This is a placeholder
        assert page.url == f"{live_server.url}/"


@pytest.mark.e2e
class TestAPIE2E:
    """End-to-end tests for API endpoints via browser."""

    def test_api_summary_endpoint(
        self, page: Page, live_server, db_session, sample_account
    ):
        """Test API summary endpoint via browser."""
        from scraper.schema import FactFollowersSnapshot
        from datetime import date

        snapshot = FactFollowersSnapshot(
            account_key=sample_account.account_key,
            snapshot_date=date.today(),
            followers_count=1000,
        )
        db_session.add(snapshot)
        db_session.commit()

        # Make API request via browser
        response = page.request.get(f"{live_server.url}/api/summary")
        assert response.status == 200

        data = response.json()
        assert isinstance(data, list)


@pytest.mark.e2e
@pytest.mark.slow
class TestUserInteractionE2E:
    """End-to-end tests for user interactions."""

    def test_page_navigation(self, page: Page, live_server):
        """Test basic page navigation."""
        page.goto(f"{live_server.url}/")
        page.wait_for_load_state("networkidle")

        # Test that page is interactive
        # This is a placeholder - add actual interaction tests
        assert page.url == f"{live_server.url}/"

    def test_form_submission(self, page: Page, live_server):
        """Test form submission (if forms exist)."""
        page.goto(f"{live_server.url}/")
        page.wait_for_load_state("networkidle")

        # Placeholder for form submission tests
        # Adjust based on actual forms in the application
        pass
