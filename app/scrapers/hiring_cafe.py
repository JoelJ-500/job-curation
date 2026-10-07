"""HiringCafe scraper (Agent 2, Step 1).

Target: https://hiringcafe.com/classic

HiringCafe is a JavaScript single-page app behind a Cloudflare challenge, so this
scraper uses a real (stealth-configured) Chrome and reads the rendered DOM. If the
Cloudflare interstitial is still shown the run fails with a clear error so the
coordinator can fall back to the other site.

Controls are located by their visible label/placeholder text (more stable than the
generated CSS classes): the "Job title or keyword" box, the Location / Experience /
Language filters, and the "Most recent" sort.

If the deterministic selectors find nothing, the caller can use the parsing agent
on `page_html` as a fallback for changed layouts.
"""

import logging
import time
from urllib.parse import urljoin

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

from app.scrapers.base import (
    DEFAULT_TIMEOUT,
    create_driver,
    page_title,
    polite_pause,
    wait_for,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://hiringcafe.com"
START_URL = "https://hiringcafe.com/classic"

CLOUDFLARE_TITLES = ("just a moment", "attention required", "checking your browser")

# The search box is identified by its stable id, with placeholder fallbacks.
SEARCH_BOX_SELECTOR = (
    "input#query-search-v4, input[placeholder='Job title or keyword'], input[type='search']"
)

MAX_PAGES_PER_ROLE = 5


class HiringCafeScraper:
    """A Selenium driver plus parsing for HiringCafe's classic search."""

    source = "hiringcafe"

    def __init__(self) -> None:
        self.driver = create_driver("hiringcafe")

    def close(self) -> None:
        try:
            self.driver.quit()
        except Exception:
            self.driver = None

    # -- search -------------------------------------------------------------

    def open_search(self) -> None:
        logger.info("HiringCafe: opening %s", START_URL)
        self.driver.get(START_URL)
        self._wait_out_challenge()
        try:
            wait_for(self.driver, SEARCH_BOX_SELECTOR, DEFAULT_TIMEOUT)
        except Exception as error:
            raise RuntimeError(
                "HiringCafe search box did not load (possible layout change or bot block): "
                f"{error}"
            ) from error

    def _wait_out_challenge(self, timeout: int = 15) -> None:
        """Give Cloudflare's JS challenge a chance to clear, then verify."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self._is_challenged():
                return
            time.sleep(2)
        if self._is_challenged():
            raise RuntimeError(
                "HiringCafe is showing a Cloudflare challenge; cannot scrape automatically."
            )

    def _is_challenged(self) -> bool:
        title = page_title(self.driver).lower()
        return any(marker in title for marker in CLOUDFLARE_TITLES)

    def _search_box(self):
        boxes = self.driver.find_elements(By.CSS_SELECTOR, SEARCH_BOX_SELECTOR)
        if not boxes:
            raise RuntimeError("HiringCafe search box not found.")
        return boxes[0]

    def run_search(self, role: str, location: str | None, experience: str | None,
                   language: str | None) -> None:
        """Type the role, apply the available filters, and submit the search."""
        box = self._search_box()
        box.clear()
        box.send_keys(role)
        box.send_keys(Keys.ENTER)
        time.sleep(3)
        # Submitting the search triggers a navigation that Cloudflare may gate.
        self._wait_out_challenge()

        # Filters are best-effort: HiringCafe's controls and layout can change.
        self._try_apply_filter("Location", location)
        self._try_apply_filter("Experience", experience)
        self._try_apply_filter("Language", language)
        time.sleep(2)

    def _try_apply_filter(self, label: str, value: str | None) -> None:
        if not value:
            return
        try:
            controls = self.driver.find_elements(
                By.XPATH,
                f"//*[self::button or self::div or self::input]"
                f"[contains(translate(., 'abcdefghijklmnopqrstuvwxyz',"
                f" 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), '{label.upper()}')]",
            )
            if not controls:
                logger.info("HiringCafe: %s filter not found; skipping", label)
                return
            controls[0].click()
            time.sleep(1)
            options = self.driver.find_elements(
                By.XPATH, f"//*[self::li or self::button or self::div][contains(., '{value}')]"
            )
            if options:
                options[0].click()
                time.sleep(1)
            else:
                logger.info("HiringCafe: no option matching %r for %s", value, label)
        except Exception as error:
            logger.warning("HiringCafe: could not apply %s filter: %s", label, error)

    # -- parsing ------------------------------------------------------------

    def fetch_jobs(self, role: str, location: str | None, experience: str | None,
                   language: str | None):
        """Yield normalized job dicts for one role across result pages."""
        self.run_search(role, location, experience, language)

        for _page in range(MAX_PAGES_PER_ROLE):
            for card in self._find_cards():
                job = self._parse_card(card)
                if job is not None:
                    yield job
            if not self._go_next_page():
                break

    def _find_cards(self):
        """Find result cards; HiringCafe links each posting to a /job/ page."""
        anchors = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='/job']")
        cards = []
        seen = set()
        for anchor in anchors:
            href = anchor.get_attribute("href") or ""
            if not href or href in seen:
                continue
            seen.add(href)
            cards.append(anchor)
        return cards

    def _parse_card(self, anchor) -> dict | None:
        href = anchor.get_attribute("href") or ""
        link = urljoin(BASE_URL + "/", href)
        text = (anchor.text or "").strip()
        if not link or not text:
            return None
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        title = lines[0] if lines else ""
        company = lines[1] if len(lines) > 1 else ""
        if not title:
            return None
        return {
            "source": self.source,
            "title": title,
            "link": link,
            "date_text": "",
            "company": company,
            "location": "",
            "summary": text,
        }

    def _go_next_page(self) -> bool:
        try:
            buttons = self.driver.find_elements(
                By.XPATH, "//*[self::button or self::a][contains(., 'Next')]"
            )
            if not buttons or not buttons[0].is_enabled():
                return False
            buttons[0].click()
            polite_pause(1.5)
            return True
        except Exception:
            return False

    def page_html(self) -> str:
        try:
            return self.driver.page_source
        except Exception:
            return ""

    def iter_jobs(self, plan):
        """Yield job dicts for one search plan (adapts SearchPlan to this site)."""
        yield from self.fetch_jobs(
            role=plan.role_query,
            location=plan.location,
            experience=plan.experience,
            language=plan.language,
        )
