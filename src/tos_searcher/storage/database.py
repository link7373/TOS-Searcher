from __future__ import annotations

import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from tos_searcher.storage.models import Document, Result, SearchQuery

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    domain TEXT NOT NULL,
    title TEXT,
    source TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'pending',
    content_hash TEXT,
    error_message TEXT,
    fetched_at TEXT,
    analyzed_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS document_texts (
    document_id INTEGER PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
    text_content TEXT NOT NULL,
    char_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    confidence REAL NOT NULL,
    matched_text TEXT NOT NULL,
    context TEXT,
    pattern_matches TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS search_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    engine TEXT NOT NULL,
    results_count INTEGER NOT NULL DEFAULT 0,
    executed_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(query, engine)
);

CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_url ON documents(url);
CREATE INDEX IF NOT EXISTS idx_results_confidence ON results(confidence);
"""


class Database:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @contextmanager
    def _cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        assert self._conn is not None
        cursor = self._conn.cursor()
        try:
            yield cursor
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def _create_tables(self) -> None:
        assert self._conn is not None
        self._conn.executescript(_SCHEMA)

    # --- Document operations ---

    def insert_document(self, doc: Document) -> int:
        with self._cursor() as cur:
            cur.execute(
                "INSERT OR IGNORE INTO documents (url, domain, title, source, status) "
                "VALUES (?, ?, ?, ?, ?)",
                (doc.url, doc.domain, doc.title, doc.source, doc.status),
            )
            return cur.lastrowid or 0

    def get_document_by_url(self, url: str) -> Document | None:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT * FROM documents WHERE url = ?", (url,)
        ).fetchone()
        return self._row_to_document(row) if row else None

    def get_pending_documents(self, limit: int = 5000) -> list[Document]:
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT * FROM documents WHERE status = 'pending' LIMIT ?", (limit,)
        ).fetchall()
        return [self._row_to_document(r) for r in rows]

    def get_fetched_documents(self, limit: int = 5000) -> list[Document]:
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT * FROM documents WHERE status = 'fetched' LIMIT ?", (limit,)
        ).fetchall()
        return [self._row_to_document(r) for r in rows]

    def update_document_status(
        self,
        doc_id: int,
        status: str,
        *,
        title: str | None = None,
        content_hash: str | None = None,
        error_message: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._cursor() as cur:
            cur.execute(
                "UPDATE documents SET status = ?, title = COALESCE(?, title), "
                "content_hash = COALESCE(?, content_hash), "
                "error_message = COALESCE(?, error_message), "
                "fetched_at = CASE WHEN ? = 'fetched' THEN ? ELSE fetched_at END, "
                "analyzed_at = CASE WHEN ? = 'analyzed' THEN ? ELSE analyzed_at END "
                "WHERE id = ?",
                (
                    status,
                    title,
                    content_hash,
                    error_message,
                    status,
                    now,
                    status,
                    now,
                    doc_id,
                ),
            )

    def url_exists(self, url: str) -> bool:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT 1 FROM documents WHERE url = ? LIMIT 1", (url,)
        ).fetchone()
        return row is not None

    def count_by_status(self) -> dict[str, int]:
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT status, COUNT(*) as cnt FROM documents GROUP BY status"
        ).fetchall()
        return {r["status"]: r["cnt"] for r in rows}

    # --- Document text operations ---

    def store_document_text(self, document_id: int, text: str) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT OR REPLACE INTO document_texts (document_id, text_content, char_count) "
                "VALUES (?, ?, ?)",
                (document_id, text, len(text)),
            )

    def get_document_text(self, document_id: int) -> str | None:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT text_content FROM document_texts WHERE document_id = ?",
            (document_id,),
        ).fetchone()
        return row["text_content"] if row else None

    # --- Result operations ---

    def insert_result(self, result: Result) -> int:
        with self._cursor() as cur:
            cur.execute(
                "INSERT INTO results (document_id, confidence, matched_text, context, pattern_matches) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    result.document_id,
                    result.confidence,
                    result.matched_text,
                    result.context,
                    result.pattern_matches_json(),
                ),
            )
            return cur.lastrowid or 0

    def get_all_results(self, min_confidence: float = 0.0) -> list[Result]:
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT * FROM results WHERE confidence >= ? ORDER BY confidence DESC",
            (min_confidence,),
        ).fetchall()
        return [self._row_to_result(r) for r in rows]

    def get_results_with_documents(
        self, min_confidence: float = 0.0
    ) -> list[tuple[Result, Document]]:
        assert self._conn is not None
        rows = self._conn.execute(
            "SELECT r.*, d.id as d_id, d.url, d.domain, d.title, d.source, "
            "d.status, d.content_hash, d.error_message, d.fetched_at, "
            "d.analyzed_at, d.created_at as d_created_at "
            "FROM results r JOIN documents d ON r.document_id = d.id "
            "WHERE r.confidence >= ? ORDER BY r.confidence DESC",
            (min_confidence,),
        ).fetchall()
        pairs: list[tuple[Result, Document]] = []
        for r in rows:
            result = Result(
                id=r["id"],
                document_id=r["document_id"],
                confidence=r["confidence"],
                matched_text=r["matched_text"],
                context=r["context"] or "",
                pattern_matches=Result.pattern_matches_from_json(
                    r["pattern_matches"] or "[]"
                ),
                created_at=r["created_at"],
            )
            doc = Document(
                id=r["d_id"],
                url=r["url"],
                domain=r["domain"],
                title=r["title"],
                source=r["source"],
                status=r["status"],
                content_hash=r["content_hash"],
                error_message=r["error_message"],
                fetched_at=r["fetched_at"],
                analyzed_at=r["analyzed_at"],
                created_at=r["d_created_at"],
            )
            pairs.append((result, doc))
        return pairs

    # --- Search query tracking ---

    def query_was_executed(self, query: str, engine: str) -> bool:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT 1 FROM search_queries WHERE query = ? AND engine = ? LIMIT 1",
            (query, engine),
        ).fetchone()
        return row is not None

    def record_query(self, query: str, engine: str, results_count: int) -> None:
        with self._cursor() as cur:
            cur.execute(
                "INSERT OR IGNORE INTO search_queries (query, engine, results_count) "
                "VALUES (?, ?, ?)",
                (query, engine, results_count),
            )

    # --- Stats ---

    def count_results(self, min_confidence: float = 0.0) -> int:
        assert self._conn is not None
        row = self._conn.execute(
            "SELECT COUNT(*) as cnt FROM results WHERE confidence >= ?",
            (min_confidence,),
        ).fetchone()
        return row["cnt"] if row else 0

    def get_stats(self) -> dict[str, int]:
        counts = self.count_by_status()
        total = sum(counts.values())
        results_count = self.count_results()
        return {
            "total": total,
            "pending": counts.get("pending", 0),
            "fetched": counts.get("fetched", 0),
            "analyzed": counts.get("analyzed", 0),
            "error": counts.get("error", 0),
            "results": results_count,
        }

    # --- Reset ---

    def reset(self) -> None:
        assert self._conn is not None
        self._conn.executescript(
            "DROP TABLE IF EXISTS results;"
            "DROP TABLE IF EXISTS document_texts;"
            "DROP TABLE IF EXISTS search_queries;"
            "DROP TABLE IF EXISTS documents;"
        )
        self._create_tables()

    # --- Helpers ---

    @staticmethod
    def hash_content(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    @staticmethod
    def _row_to_document(row: sqlite3.Row) -> Document:
        return Document(
            id=row["id"],
            url=row["url"],
            domain=row["domain"],
            title=row["title"],
            source=row["source"],
            status=row["status"],
            content_hash=row["content_hash"],
            error_message=row["error_message"],
            fetched_at=row["fetched_at"],
            analyzed_at=row["analyzed_at"],
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_result(row: sqlite3.Row) -> Result:
        return Result(
            id=row["id"],
            document_id=row["document_id"],
            confidence=row["confidence"],
            matched_text=row["matched_text"],
            context=row["context"] or "",
            pattern_matches=Result.pattern_matches_from_json(
                row["pattern_matches"] or "[]"
            ),
            created_at=row["created_at"],
        )
