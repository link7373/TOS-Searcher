from __future__ import annotations

import logging
import random
import time

from tos_searcher.config import Settings

logger = logging.getLogger(__name__)


class DuckDuckGoProvider:
    name = "duckduckgo"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def search(self, query: str, max_results: int = 50) -> list[str]:
        try:
            from ddgs import DDGS
        except ImportError:
            logger.warning("ddgs not installed, skipping DuckDuckGo")
            return []

        urls: list[str] = []
        try:
            ddgs = DDGS()
            results = ddgs.text(query, max_results=max_results)
            for r in results:
                url = r.get("href") or r.get("link")
                if url:
                    urls.append(url)
        except Exception as e:
            logger.warning("DuckDuckGo search failed for '%s': %s", query, e)

        delay = random.uniform(
            self._settings.search_delay_min,
            self._settings.search_delay_max,
        )
        time.sleep(delay)
        return urls
