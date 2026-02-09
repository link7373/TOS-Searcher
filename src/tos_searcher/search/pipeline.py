from __future__ import annotations

import logging
import time
from typing import Callable

from tos_searcher.analyzer.detector import Detector
from tos_searcher.config import Settings
from tos_searcher.scraper.fetcher import Fetcher
from tos_searcher.scraper.parser import DocumentParser
from tos_searcher.search.engine import SearchEngine
from tos_searcher.storage.database import Database
from tos_searcher.storage.models import Result, SearchProgress

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[SearchProgress], None]


class SearchPipeline:
    def __init__(
        self,
        settings: Settings,
        db: Database,
        progress_callback: ProgressCallback,
    ) -> None:
        self._settings = settings
        self._db = db
        self._progress_callback = progress_callback
        self._stop_requested = False

        self._search_engine = SearchEngine(settings, db, progress_callback)
        self._fetcher = Fetcher(settings)
        self._parser = DocumentParser()
        self._detector = Detector()

    def request_stop(self) -> None:
        self._stop_requested = True
        self._search_engine.request_stop()

    def run(self) -> None:
        """Execute the full four-phase pipeline."""
        try:
            # Phase 1: Discovery (0% - 30%)
            self._report("discovery", "Starting URL discovery...")
            self._search_engine.run_discovery()

            if self._stop_requested:
                self._report("complete", "Search stopped by user.", percent=1.0)
                return

            # Phase 2: Fetching (30% - 80%)
            self._report("fetching", "Fetching discovered documents...")
            self._run_fetching()

            if self._stop_requested:
                self._report("complete", "Search stopped by user.", percent=1.0)
                return

            # Phase 3: Analysis (80% - 100%)
            self._report("analyzing", "Analyzing documents for hidden prizes...")
            self._run_analysis()

            # Phase 4: Complete
            stats = self._db.get_stats()
            results = self._db.get_all_results(self._settings.min_confidence_threshold)
            self._progress_callback(
                SearchProgress(
                    phase="complete",
                    total_discovered=stats.get("total", 0),
                    total_fetched=stats.get("fetched", 0) + stats.get("analyzed", 0),
                    total_analyzed=stats.get("analyzed", 0),
                    total_results=len(results),
                    current_action=(
                        f"Search complete! Found {len(results)} potential hidden "
                        f"contest(s) in {stats.get('analyzed', 0)} documents."
                    ),
                    percent_complete=1.0,
                    is_running=False,
                )
            )

        except Exception as e:
            logger.exception("Pipeline error")
            self._progress_callback(
                SearchProgress(
                    phase="error",
                    current_action=f"Error: {e}",
                    is_running=False,
                )
            )

    def _run_fetching(self) -> None:
        """Phase 2: Fetch all pending documents."""
        pending = self._db.get_pending_documents(limit=self._settings.max_total_documents)
        total = len(pending)
        if total == 0:
            return

        for i, doc in enumerate(pending):
            if self._stop_requested:
                return

            self._report(
                "fetching",
                f"Fetching {i + 1}/{total}: {doc.domain}...",
                percent=i / total * 0.5 + 0.3,  # 30%-80%
            )

            result = self._fetcher.fetch(doc.url)

            if result.success and result.html:
                text = self._parser.extract_text(result.html)
                title = self._parser.extract_title(result.html)

                if len(text) < 100:
                    # Too little content — probably not a real TOS page
                    self._db.update_document_status(
                        doc.id, "error", error_message="Insufficient content"
                    )
                    continue

                content_hash = Database.hash_content(text)
                self._db.update_document_status(
                    doc.id,
                    "fetched",
                    title=title,
                    content_hash=content_hash,
                )
                self._db.store_document_text(doc.id, text)
            else:
                self._db.update_document_status(
                    doc.id, "error", error_message=result.error
                )

            # Rate limiting between fetches
            time.sleep(0.3)

    def _run_analysis(self) -> None:
        """Phase 3: Analyze fetched documents for hidden prizes."""
        fetched = self._db.get_fetched_documents(
            limit=self._settings.max_total_documents
        )
        total = len(fetched)
        if total == 0:
            return

        for i, doc in enumerate(fetched):
            if self._stop_requested:
                return

            self._report(
                "analyzing",
                f"Analyzing {i + 1}/{total}: {doc.domain}...",
                percent=i / total * 0.2 + 0.8,  # 80%-100%
            )

            text = self._db.get_document_text(doc.id)
            if not text:
                self._db.update_document_status(doc.id, "analyzed")
                continue

            detection = self._detector.analyze(text)
            if (
                detection
                and detection.confidence >= self._settings.min_confidence_threshold
            ):
                result = Result(
                    document_id=doc.id,
                    confidence=detection.confidence,
                    matched_text=detection.matched_text,
                    context=detection.context,
                    pattern_matches=detection.pattern_names,
                )
                self._db.insert_result(result)
                logger.info(
                    "MATCH: %s (%.1f%%) - %s",
                    doc.url,
                    detection.confidence * 100,
                    detection.matched_text[:80],
                )

            self._db.update_document_status(doc.id, "analyzed")

    def _report(
        self, phase: str, action: str, percent: float = 0.0
    ) -> None:
        stats = self._db.count_by_status()
        total = sum(stats.values())
        fetched = stats.get("fetched", 0) + stats.get("analyzed", 0)
        analyzed = stats.get("analyzed", 0)
        results_count = len(
            self._db.get_all_results(self._settings.min_confidence_threshold)
        )
        self._progress_callback(
            SearchProgress(
                phase=phase,
                total_discovered=total,
                total_fetched=fetched,
                total_analyzed=analyzed,
                total_results=results_count,
                current_action=action,
                percent_complete=percent,
                is_running=True,
            )
        )
