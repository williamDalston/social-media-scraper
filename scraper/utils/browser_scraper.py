"""
Utility for browser-based scraping using Selenium/Playwright for dynamic content.
Uses undetected-chromedriver for anti-detection capabilities.
"""

import logging
import random
import time
from typing import Optional, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@contextmanager
def get_browser(driver_type="selenium", headless=True):
    """
    Get a browser instance for dynamic content scraping.

    Args:
        driver_type: 'selenium' or 'playwright'
        headless: Run browser in headless mode

    Yields:
        Browser/driver instance
    """
    browser = None
    try:
        if driver_type == "selenium":
            # Try undetected-chromedriver first (better anti-detection)
            try:
                import undetected_chromedriver as uc

                logger.debug("Using undetected-chromedriver for better anti-detection")

                options = uc.ChromeOptions()
                if headless:
                    options.add_argument("--headless=new")  # New headless mode
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--disable-extensions")
                options.add_argument("--window-size=1920,1080")

                # Use realistic user-agent
                options.add_argument(
                    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )

                browser = uc.Chrome(options=options, version_main=None)
                browser.set_page_load_timeout(30)

                # Remove automation indicators
                browser.execute_cdp_cmd(
                    "Page.addScriptToEvaluateOnNewDocument",
                    {
                        "source": """
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                        window.chrome = {
                            runtime: {}
                        };
                    """
                    },
                )

                yield browser

            except ImportError:
                logger.warning(
                    "undetected-chromedriver not installed. Install with: pip install undetected-chromedriver"
                )
                logger.warning(
                    "Falling back to standard Selenium (may be detected by bot protection)"
                )

                # Fallback to standard Selenium
                try:
                    from selenium import webdriver
                    from selenium.webdriver.chrome.options import Options
                    from selenium.webdriver.common.by import By
                    from selenium.webdriver.support.ui import WebDriverWait
                    from selenium.webdriver.support import expected_conditions as EC

                    chrome_options = Options()
                    if headless:
                        chrome_options.add_argument("--headless=new")
                    chrome_options.add_argument("--no-sandbox")
                    chrome_options.add_argument("--disable-dev-shm-usage")
                    chrome_options.add_argument("--disable-gpu")
                    chrome_options.add_argument("--window-size=1920,1080")
                    chrome_options.add_argument(
                        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )

                    browser = webdriver.Chrome(options=chrome_options)
                    browser.set_page_load_timeout(30)

                    yield browser

                except Exception as e:
                    logger.error(f"Browser drivers not available: {e}")
                    yield None

        elif driver_type == "playwright":
            try:
                from playwright.sync_api import sync_playwright

                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=headless)
                    context = browser.new_context(
                        viewport={"width": 1920, "height": 1080},
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    )
                    yield context
                    context.close()
                    browser.close()

            except ImportError:
                logger.warning(
                    "Playwright not installed. Install with: pip install playwright && playwright install"
                )
                yield None

        else:
            yield None

    finally:
        if browser and driver_type == "selenium":
            try:
                browser.quit()
            except:
                pass


def scrape_with_browser(
    url: str, wait_time: int = 5, driver_type: str = "selenium"
) -> Optional[str]:
    """
    Scrape a URL using a headless browser to get dynamically loaded content.

    Args:
        url: URL to scrape
        wait_time: Seconds to wait for page to load
        driver_type: 'selenium' or 'playwright'

    Returns:
        Page HTML content or None if scraping fails
    """
    try:
        with get_browser(driver_type=driver_type, headless=True) as browser:
            if not browser:
                return None

            if driver_type == "selenium":
                browser.get(url)

                # Wait for page to fully load (JavaScript execution)
                time.sleep(wait_time)

                # Wait for document ready state
                try:
                    from selenium.webdriver.support.ui import WebDriverWait

                    WebDriverWait(browser, 10).until(
                        lambda d: d.execute_script("return document.readyState")
                        == "complete"
                    )
                except:
                    pass

                # Additional wait for dynamic content (common pattern)
                # Some sites load content after readyState is complete
                time.sleep(2)

                # Scroll page to trigger lazy-loading (if any)
                try:
                    browser.execute_script(
                        "window.scrollTo(0, document.body.scrollHeight/2);"
                    )
                    time.sleep(1)
                    browser.execute_script("window.scrollTo(0, 0);")
                    time.sleep(1)
                except:
                    pass

                return browser.page_source

            elif driver_type == "playwright":
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                # time module is already imported at module level
                time.sleep(wait_time)
                content = page.content()
                page.close()
                return content

        return None

    except Exception as e:
        logger.error(f"Error scraping with browser: {e}")
        return None
