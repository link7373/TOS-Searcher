from __future__ import annotations

import logging
from typing import Callable
from urllib.parse import urlparse

from tos_searcher.config import Settings
from tos_searcher.search.bing import BingProvider
from tos_searcher.search.crawler import DirectCrawler
from tos_searcher.search.duckduckgo import DuckDuckGoProvider
from tos_searcher.search.google import GoogleProvider
from tos_searcher.storage.database import Database
from tos_searcher.storage.models import Document, SearchProgress

logger = logging.getLogger(__name__)

DISCOVERY_QUERIES = [
    "terms of service",
    "terms and conditions",
    "user agreement",
    "privacy policy",
    "end user license agreement",
    "terms of service hidden prize",
    "terms of service hidden contest",
    "read the fine print prize",
    "hidden message terms of service",
    '"if you read this" terms of service',
    '"first person to" terms conditions',
    '"email us" terms of service reward',
    "terms of service easter egg",
    "hidden contest fine print",
    "company hid prize in terms",
    "buried in fine print contest",
    "terms of service giveaway",
    "sweepstakes hidden in agreement",
    "insurance policy hidden prize",
    "software license agreement prize",
    "terms of use contest reward",
]

ProgressCallback = Callable[[SearchProgress], None]


class SearchEngine:
    def __init__(
        self,
        settings: Settings,
        db: Database,
        on_progress: ProgressCallback,
    ) -> None:
        self._settings = settings
        self._db = db
        self._on_progress = on_progress
        self._stop_requested = False

        self._providers = [
            DuckDuckGoProvider(settings),
            BingProvider(settings),
            GoogleProvider(settings),
        ]
        self._crawler = DirectCrawler(settings)

    def request_stop(self) -> None:
        self._stop_requested = True

    def run_discovery(self) -> None:
        """Phase 1: Discover TOS document URLs from all sources."""
        progress = SearchProgress(phase="discovery", is_running=True)

        total_steps = len(DISCOVERY_QUERIES) * len(self._providers) + 1  # +1 for crawl
        step = 0

        # 1. Run search queries across all engines
        for query in DISCOVERY_QUERIES:
            if self._stop_requested:
                return
            for provider in self._providers:
                if self._stop_requested:
                    return

                step += 1

                if self._db.query_was_executed(query, provider.name):
                    logger.info("Skipping already-executed: %s '%s'", provider.name, query)
                    continue

                progress.current_action = (
                    f"Searching {provider.name} for '{query}'..."
                )
                progress.percent_complete = step / total_steps * 0.3  # discovery = 0-30%
                self._on_progress(progress)

                urls = provider.search(query, self._settings.max_results_per_query)
                new_count = 0
                for url in urls:
                    if not self._db.url_exists(url):
                        doc = Document(
                            url=url,
                            domain=self._extract_domain(url),
                            source=provider.name,
                        )
                        self._db.insert_document(doc)
                        new_count += 1

                self._db.record_query(query, provider.name, len(urls))
                logger.info(
                    "%s '%s': %d results, %d new",
                    provider.name, query, len(urls), new_count,
                )

                stats = self._db.count_by_status()
                progress.total_discovered = sum(stats.values())
                self._on_progress(progress)

        # 2. Crawl seed domains for TOS pages
        if not self._stop_requested:
            progress.current_action = "Crawling known domains for TOS pages..."
            progress.percent_complete = 0.28
            self._on_progress(progress)

            candidate_urls = self._crawler.discover_tos_urls()
            new_count = 0
            for url in candidate_urls:
                if self._stop_requested:
                    return
                if not self._db.url_exists(url):
                    doc = Document(
                        url=url,
                        domain=self._extract_domain(url),
                        source="crawl",
                    )
                    self._db.insert_document(doc)
                    new_count += 1

            logger.info("Crawler generated %d candidates, %d new", len(candidate_urls), new_count)

            stats = self._db.count_by_status()
            progress.total_discovered = sum(stats.values())
            progress.percent_complete = 0.3
            self._on_progress(progress)

    @staticmethod
    def _extract_domain(url: str) -> str:
        return urlparse(url).netloc
