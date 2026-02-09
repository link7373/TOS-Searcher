from __future__ import annotations

import logging
import random
from typing import NamedTuple

import requests

from tos_searcher.config import Settings

logger = logging.getLogger(__name__)


class FetchResult(NamedTuple):
    html: str
    status_code: int
    content_type: str
    success: bool
    error: str | None = None


class Fetcher:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._session = requests.Session()

    def fetch(self, url: str) -> FetchResult:
        """Try requests first, fall back to playwright for JS-rendered pages."""
        result = self._fetch_with_requests(url)
        if result.success:
            return result

        if self._settings.use_playwright_fallback:
            logger.info("Falling back to playwright for %s", url)
            return self._fetch_with_playwright(url)

        return result

    def _fetch_with_requests(self, url: str) -> FetchResult:
        try:
            ua = random.choice(self._settings.user_agents)
            headers = {
                "User-Agent": ua,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
            resp = self._session.get(
                url,
                headers=headers,
                timeout=self._settings.fetch_timeout,
                allow_redirects=True,
            )
            resp.raise_for_status()

            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type and "text/plain" not in content_type:
                return FetchResult(
                    "", resp.status_code, content_type, False, "Non-HTML content type"
                )

            return FetchResult(resp.text, resp.status_code, content_type, True)
        except requests.RequestException as e:
            return FetchResult("", 0, "", False, str(e))

    def _fetch_with_playwright(self, url: str) -> FetchResult:
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, timeout=self._settings.fetch_timeout * 1000)
                page.wait_for_load_state("networkidle", timeout=10000)
                html = page.content()
                browser.close()
                return FetchResult(html, 200, "text/html", True)
        except Exception as e:
            return FetchResult("", 0, "", False, f"Playwright error: {e}")
