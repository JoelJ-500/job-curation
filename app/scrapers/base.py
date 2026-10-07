"""Shared Selenium driver setup and page helpers for the job-site scrapers.

Each site gets its own driver instance (its own user-data-dir and options) so the
two scrapers look like independent browsers and can run concurrently.
"""

import logging
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 20

# A desktop browser UA keeps the sites from serving a degraded/bot page.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def create_driver(profile_name: str) -> webdriver.Chrome:
    """Build a Chrome driver with a unique profile directory and stealth-ish flags."""
    options = Options()
    if settings.chrome_binary:
        options.binary_location = settings.chrome_binary

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1440,900")
    options.add_argument(f"--user-data-dir=/tmp/selenium-{profile_name}")
    options.add_argument(f"--user-agent={USER_AGENT}")
    options.add_argument("--lang=en-CA")
    # Reduce the obvious automation fingerprints.
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    if settings.headless_browser:
        options.add_argument("--headless=new")

    service = Service(executable_path=settings.chromedriver_path)
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(45)

    # Hide the most common headless/automation fingerprint before any navigation.
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"},
        )
    except Exception:
        pass

    return driver


def wait_for(driver, css_selector: str, timeout: int = DEFAULT_TIMEOUT):
    """Wait until at least one element matching the selector is present."""
    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
    )


def first_text(parent, css_selector: str) -> str:
    """Return the trimmed text of the first matching child, or ''."""
    elements = parent.find_elements(By.CSS_SELECTOR, css_selector)
    if not elements:
        return ""
    return (elements[0].text or "").strip()


def element_attribute(parent, css_selector: str, attribute_name: str) -> str:
    """Return an attribute of the first matching child, or ''."""
    elements = parent.find_elements(By.CSS_SELECTOR, css_selector)
    if not elements:
        return ""
    return (elements[0].get_attribute(attribute_name) or "").strip()


def page_title(driver) -> str:
    """Return the current page title (used to detect interstitial/bot pages)."""
    try:
        return driver.title or ""
    except Exception:
        return ""


def polite_pause(seconds: float) -> None:
    """Anti-bot delay between jobs."""
    if seconds and seconds > 0:
        time.sleep(float(seconds))
