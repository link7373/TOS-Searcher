from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Document:
    id: int | None = None
    url: str = ""
    domain: str = ""
    title: str | None = None
    source: str = ""  # 'duckduckgo', 'bing', 'google', 'crawl'
    status: str = "pending"  # pending, fetched, analyzed, error
    content_hash: str | None = None
    error_message: str | None = None
    fetched_at: datetime | None = None
    analyzed_at: datetime | None = None
    created_at: datetime | None = None


@dataclass
class Result:
    id: int | None = None
    document_id: int = 0
    confidence: float = 0.0
    matched_text: str = ""
    context: str = ""
    pattern_matches: list[str] = field(default_factory=list)
    created_at: datetime | None = None

    def pattern_matches_json(self) -> str:
        return json.dumps(self.pattern_matches)

    @staticmethod
    def pattern_matches_from_json(raw: str) -> list[str]:
        return json.loads(raw) if raw else []


@dataclass
class SearchQuery:
    id: int | None = None
    query: str = ""
    engine: str = ""
    results_count: int = 0
    executed_at: datetime | None = None


@dataclass
class SearchProgress:
    """Snapshot of current search state for GUI updates."""

    phase: str = "idle"  # discovery, fetching, analyzing, complete, error
    total_discovered: int = 0
    total_fetched: int = 0
    total_analyzed: int = 0
    total_results: int = 0
    current_action: str = ""
    percent_complete: float = 0.0
    is_running: bool = False
