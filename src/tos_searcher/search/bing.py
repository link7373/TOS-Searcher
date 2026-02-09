from __future__ import annotations

import logging
import random
import time

import requests

from tos_searcher.config import Settings

logger = logging.getLogger(__name__)


class BingProvider:
    name = "bing"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._session = requests.Session()
        self._session.headers.update(
            {"User-Agent": random.choice(settings.user_agents)}
        )

    def search(self, query: str, max_results: int = 50) -> list[str]:
        try:
            from search_engines.bing_search import (
                extract_search_results,
                get_search_url,
            )
        except ImportError:
            logger.warning("search-engines not installed, skipping Bing")
            return []

        urls: list[str] = []
        try:
            page_url = get_search_url(query)
            pages = max(1, max_results // 10)

            for _ in range(pages):
                if not page_url or len(urls) >= max_results:
                    break

                resp = self._session.get(page_url, timeout=self._settings.search_timeout)
                resp.raise_for_status()
                results, next_page_url = extract_search_results(resp.text, page_url)

                for r in results:
                    if r.get("url"):
                        urls.append(r["url"])

                page_url = next_page_url
                time.sleep(1)  # delay between pages

        except Exception as e:
            logger.warning("Bing search failed for '%s': %s", query, e)

        delay = random.uniform(
            self._settings.search_delay_min,
            self._settings.search_delay_max,
        )
        time.sleep(delay)
        return urls[:max_results]
