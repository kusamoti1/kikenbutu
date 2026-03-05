from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class SearchEngine:
    """Full-text search engine using SQLite FTS5.

    The FTS5 index now includes the ``context`` column so that
    Contextual Retrieval metadata (equipment, era, heading) is
    searchable alongside the original paragraph text.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._ensure_fts()

    def _ensure_fts(self) -> None:
        """Create FTS5 virtual table, recreating if schema has changed.

        If an older database has a ``paragraphs_fts`` table without the
        ``context`` column, ``CREATE VIRTUAL TABLE IF NOT EXISTS`` silently
        keeps the old schema and subsequent INSERTs with 5 values fail.
        We detect this by checking the column count and recreating if needed.
        """
        try:
            # Check whether the existing table has the expected columns.
            try:
                cur = self.conn.execute("PRAGMA table_info(paragraphs_fts)")
                existing_cols = [row[1] for row in cur.fetchall()]
                if existing_cols and "context" not in existing_cols:
                    logger.info("FTS5 table schema outdated (missing 'context'). Recreating.")
                    self.conn.execute("DROP TABLE IF EXISTS paragraphs_fts")
                    self.conn.commit()
            except sqlite3.OperationalError:
                pass  # Table doesn't exist yet — will be created below.

            self.conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS paragraphs_fts USING fts5(
                    paragraph_id UNINDEXED,
                    title,
                    context,
                    text,
                    confidence UNINDEXED,
                    tokenize='unicode61'
                )
                """
            )
            self.conn.commit()
        except sqlite3.OperationalError:
            logger.warning("FTS5 is not available. Falling back to LIKE search only.")

    def rebuild_index(self) -> None:
        """Rebuild the FTS5 index from the paragraphs table.

        The DELETE + INSERT is wrapped in a single transaction so that
        a crash between the two operations does not leave an empty index.
        """
        try:
            self.conn.execute("SELECT 1 FROM paragraphs_fts LIMIT 1")
        except sqlite3.OperationalError:
            return

        rows = self.conn.execute(
            "SELECT p.id, d.title, COALESCE(p.context, ''), p.text, p.confidence "
            "FROM paragraphs p JOIN documents d ON p.document_id = d.id"
        ).fetchall()

        # Wrap in explicit transaction for atomicity.
        self.conn.execute("BEGIN")
        try:
            self.conn.execute("DELETE FROM paragraphs_fts")
            if rows:
                self.conn.executemany(
                    "INSERT INTO paragraphs_fts (paragraph_id, title, context, text, confidence) "
                    "VALUES (?, ?, ?, ?, ?)",
                    rows,
                )
            self.conn.execute("COMMIT")
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search paragraphs using FTS5 MATCH with LIKE fallback.

        The FTS5 index covers title, context, and text — so a query
        for an equipment name will match both the context tag and any
        mention in the body text.
        """
        if not query or not query.strip():
            return []

        safe_query = query.strip().replace('"', '""')
        if not safe_query:
            return []

        rows: list[tuple] = []

        try:
            rows = self.conn.execute(
                """
                SELECT paragraph_id, title, context, text, confidence
                FROM paragraphs_fts
                WHERE paragraphs_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (f'"{safe_query}"', k),
            ).fetchall()
        except sqlite3.OperationalError as exc:
            logger.debug("FTS5 search failed (%s), falling back to LIKE", exc)
            rows = []

        if not rows:
            try:
                rows = self.conn.execute(
                    """
                    SELECT p.id, d.title, COALESCE(p.context, ''), p.text, p.confidence
                    FROM paragraphs p
                    JOIN documents d ON p.document_id = d.id
                    WHERE p.text LIKE ? OR d.title LIKE ? OR p.context LIKE ?
                    ORDER BY p.id
                    LIMIT ?
                    """,
                    (f"%{safe_query}%", f"%{safe_query}%", f"%{safe_query}%", k),
                ).fetchall()
            except sqlite3.OperationalError as exc:
                logger.error("LIKE search also failed: %s", exc)
                return []

        return [
            {
                "paragraph_id": r[0],
                "title": r[1],
                "context": r[2],
                "text": r[3],
                "confidence": r[4],
            }
            for r in rows
        ]

    def close(self) -> None:
        self.conn.close()
