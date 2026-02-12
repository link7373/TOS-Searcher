from __future__ import annotations

import base64
import logging
import random
import time
from urllib.parse import parse_qs, urlparse

import requests

from tos_searcher.config import Settings

logger = logging.getLogger(__name__)


def _extract_real_url(bing_url: str) -> str | None:
    """Extract the real destination URL from a Bing tracking redirect.

    Bing wraps results in URLs like:
      https://www.bing.com/ck/a?...&u=a1aHR0cHM6Ly9leGFtcGxlLmNvbQ&...
    The 'u' parameter contains a base64-encoded URL prefixed with 'a1'.
    """
    parsed = urlparse(bing_url)
    if "bing.com/ck/" not in bing_url:
        return bing_url  # not a tracking URL, return as-is

    params = parse_qs(parsed.query)
    u_param = params.get("u", [None])[0]
    if not u_param:
        return None

    # Strip the 'a1' prefix and decode base64
    if u_param.startswith("a1"):
        encoded = u_param[2:]
        try:
            # Add padding if needed
            padding = 4 - len(encoded) % 4
            if padding != 4:
                encoded += "=" * padding
            decoded = base64.b64decode(encoded).decode("utf-8")
            return decoded
        except Exception:
            pass
    return None


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

                resp = self._session.get(
                    page_url, timeout=self._settings.search_timeout
                )
                resp.raise_for_status()
                results, next_page_url = extract_search_results(
                    resp.text, page_url
                )

                for r in results:
                    raw_url = r.get("url", "")
                    if not raw_url:
                        continue
                    real_url = _extract_real_url(raw_url)
                    if real_url:
                        urls.append(real_url)

                page_url = next_page_url
                time.sleep(1)

        except Exception as e:
            logger.warning("Bing search failed for '%s': %s", query, e)

        delay = random.uniform(
            self._settings.search_delay_min,
            self._settings.search_delay_max,
        )
        time.sleep(delay)
        return urls[:max_results]
