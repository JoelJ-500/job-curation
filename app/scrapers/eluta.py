"""Eluta.ca scraper (Agent 2, Step 1).

Eluta is server-rendered, so the search results can be read straight from the DOM.

Search controls (https://www.eluta.ca/search):
  - keywords: `#f-ss-q` (placeholder "job title or keywords")
  - location: `input[name=l]` (placeholder "city, province")
  - category: `filter-field` query param
  - sort by date: `sort=post`

Result items: `div#organic-jobs div.organic-job`, with the title/link in
`h2.title a.lk-job-title` (real URL in the `data-url` attribute).
"""

import logging
from urllib.parse import urlencode, urljoin

from selenium.webdriver.common.by import By

from app.scrapers.base import (
    DEFAULT_TIMEOUT,
    create_driver,
    element_attribute,
    first_text,
    wait_for,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://www.eluta.ca"
SEARCH_URL = "https://www.eluta.ca/search"

RESULTS_SELECTOR = "div#organic-jobs div.organic-job"
TITLE_LINK_SELECTOR = "h2.title a.lk-job-title"
EMPLOYER_SELECTOR = "a.lk-employer"
LOCATION_SELECTOR = "span.location span"
DESCRIPTION_SELECTOR = "span.description"
DATE_SELECTOR = "a.lk.lastseen"
NEXT_PAGE_SELECTOR = "#pager-next"

# How many result pages to walk per role before giving up.
MAX_PAGES_PER_ROLE = 5


class ElutaScraper:
    """A Selenium driver plus parsing for Eluta's search results."""

    source = "eluta"

    def __init__(self) -> None:
        self.driver = create_driver("eluta")

    def close(self) -> None:
        try:
            self.driver.quit()
        except Exception:
            self.driver = None

    # -- search -------------------------------------------------------------

    def _build_url(self, role: str, location: str, category: str, sort_recent: bool) -> str:
        params: dict[str, str] = {}
        if role:
            params["q"] = role
        if location:
            params["l"] = location
        if category:
            params["filter-field"] = category
        if sort_recent:
            params["sort"] = "post"
        return f"{SEARCH_URL}?{urlencode(params)}"

    def fetch_jobs(
        self, role: str, location: str, category: str, sort_recent: bool = True
    ):
        """Yield normalized job dicts for one role, across result pages."""
        url = self._build_url(role, location, category, sort_recent)
        logger.info("Eluta: opening %s", url)
        self.driver.get(url)

        try:
            wait_for(self.driver, RESULTS_SELECTOR, DEFAULT_TIMEOUT)
        except Exception:
            logger.warning("Eluta: no results for role=%r", role)
            return

        for _page in range(MAX_PAGES_PER_ROLE):
            for card in self.driver.find_elements(By.CSS_SELECTOR, RESULTS_SELECTOR):
                job = self._parse_card(card)
                if job is not None:
                    yield job

            next_url = self._next_page_url()
            if not next_url:
                break
            self.driver.get(next_url)
            try:
                wait_for(self.driver, RESULTS_SELECTOR, DEFAULT_TIMEOUT)
            except Exception:
                break

    def _next_page_url(self) -> str | None:
        links = self.driver.find_elements(By.CSS_SELECTOR, NEXT_PAGE_SELECTOR)
        if not links:
            return None
        href = links[0].get_attribute("href")
        if not href:
            return None
        return urljoin(BASE_URL + "/", href)

    # -- parsing ------------------------------------------------------------

    def _parse_card(self, card) -> dict | None:
        title = element_attribute(card, TITLE_LINK_SELECTOR, "title") or first_text(
            card, TITLE_LINK_SELECTOR
        )
        data_url = element_attribute(card, TITLE_LINK_SELECTOR, "data-url")
        link = urljoin(BASE_URL + "/", data_url) if data_url else ""
        if not title or not link:
            return None

        return {
            "source": self.source,
            "title": title,
            "link": link,
            "date_text": first_text(card, DATE_SELECTOR),
            "company": first_text(card, EMPLOYER_SELECTOR),
            "location": first_text(card, LOCATION_SELECTOR),
            "summary": first_text(card, DESCRIPTION_SELECTOR),
        }

    def fetch_detail(self, link: str) -> str:
        """Open a job detail page in a new tab and return its full text (best effort)."""
        try:
            original = self.driver.current_window_handle
            self.driver.execute_script("window.open(arguments[0], '_blank');", link)
            self.driver.switch_to.window(self.driver.window_handles[-1])
            wait_for(self.driver, "body", DEFAULT_TIMEOUT)
            text = self.driver.find_element(By.TAG_NAME, "body").text or ""
            self.driver.close()
            self.driver.switch_to.window(original)
            return text
        except Exception as error:
            logger.warning("Eluta: could not read detail page %s: %s", link, error)
            return ""

    def iter_jobs(self, plan):
        """Yield job dicts for one search plan (adapts SearchPlan to this site)."""
        yield from self.fetch_jobs(
            role=plan.role_query,
            location=plan.location or "",
            category=plan.category or "",
            sort_recent=plan.sort_recent,
        )
