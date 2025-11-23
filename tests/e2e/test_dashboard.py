"""
End-to-end browser tests for the dashboard using Playwright.
"""
import pytest
from playwright.sync_api import Page, expect

@pytest.fixture(scope="function")
def page(browser):
    """Create a new page for each test."""
    page = browser.new_page()
    yield page
    page.close()

def test_dashboard_loads(page: Page, base_url):
    """Test that the dashboard loads successfully."""
    page.goto(f"{base_url}/")
    
    # Check that the main title is visible
    expect(page.locator("h1")).to_contain_text("HHS Social Media Command Center")
    
    # Check that tabs are visible
    expect(page.locator("text=Charts & Analytics")).to_be_visible()
    expect(page.locator("text=Full Data Grid")).to_be_visible()

def test_account_list_loads(page: Page, base_url):
    """Test that account list loads in the sidebar."""
    page.goto(f"{base_url}/")
    
    # Wait for accounts to load (they're loaded via JavaScript)
    page.wait_for_selector(".account-item", timeout=10000)
    
    # Check that at least one account is visible
    account_items = page.locator(".account-item")
    expect(account_items.first).to_be_visible()

def test_chart_rendering(page: Page, base_url):
    """Test that charts render correctly."""
    page.goto(f"{base_url}/")
    
    # Wait for charts to load
    page.wait_for_selector("canvas", timeout=10000)
    
    # Check that canvas elements exist (Chart.js renders to canvas)
    canvas_elements = page.locator("canvas")
    expect(canvas_elements).to_have_count(2)  # Followers chart and engagement chart

def test_tab_switching(page: Page, base_url):
    """Test switching between tabs."""
    page.goto(f"{base_url}/")
    
    # Click on Grid tab
    page.click("text=Full Data Grid")
    
    # Wait for grid to load
    page.wait_for_selector("#table-wrapper", timeout=5000)
    
    # Check that grid view is active
    expect(page.locator("#grid-view")).to_have_class("view-section active")
    
    # Switch back to Charts
    page.click("text=Charts & Analytics")
    expect(page.locator("#charts-view")).to_have_class("view-section active")

def test_download_button(page: Page, base_url):
    """Test that download button is present."""
    page.goto(f"{base_url}/")
    
    # Check download button exists
    download_link = page.locator("text=Download All Data (CSV)")
    expect(download_link).to_be_visible()
    
    # Note: Actually clicking and downloading would require handling file downloads
    # which is more complex and may require authentication

def test_run_scraper_button(page: Page, base_url):
    """Test that run scraper button is present."""
    page.goto(f"{base_url}/")
    
    # Check run scraper button exists
    scraper_button = page.locator("text=Run Scraper")
    expect(scraper_button).to_be_visible()

@pytest.fixture
def base_url():
    """Base URL for the application."""
    return "http://localhost:5000"

@pytest.fixture(scope="session")
def browser():
    """Create browser instance for all tests."""
    from playwright.sync_api import sync_playwright
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()

