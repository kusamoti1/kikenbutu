from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class SearchEngine:
    """Full-text search engine using SQLite FTS5."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        # check_same_thread=False is required because Streamlit's
        # @st.cache_resource may create the object in one thread and
        # reuse it from another.
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._ensure_fts()

    def _ensure_fts(self) -> None:
        """Create FTS5 virtual table if it does not exist."""
        try:
            self.conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS paragraphs_fts USING fts5(
                    paragraph_id UNINDEXED,
                    title,
                    text,
                    confidence UNINDEXED,
                    tokenize='unicode61'
                )
                """
            )
            self.conn.commit()
        except sqlite3.OperationalError:
            # FTS5 extension may not be available in all SQLite builds.
            logger.warning("FTS5 is not available. Falling back to LIKE search only.")

    def rebuild_index(self) -> None:
        """Rebuild the FTS5 index from the paragraphs table."""
        try:
            self.conn.execute("SELECT 1 FROM paragraphs_fts LIMIT 1")
        except sqlite3.OperationalError:
            # FTS table does not exist – nothing to rebuild.
            return

        self.conn.execute("DELETE FROM paragraphs_fts")

        rows = self.conn.execute(
            "SELECT p.id, d.title, p.text, p.confidence "
            "FROM paragraphs p JOIN documents d ON p.document_id = d.id"
        ).fetchall()

        if not rows:
            self.conn.commit()
            return

        self.conn.executemany(
            "INSERT INTO paragraphs_fts (paragraph_id, title, text, confidence) VALUES (?, ?, ?, ?)",
            rows,
        )
        self.conn.commit()

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Search paragraphs using FTS5 MATCH with LIKE fallback."""
        if not query or not query.strip():
            return []

        safe_query = query.strip().replace('"', '""')

        # Reject queries that would become empty after escaping
        if not safe_query:
            return []

        rows: list[tuple] = []

        # Try FTS5 first
        try:
            rows = self.conn.execute(
                """
                SELECT paragraph_id, title, text, confidence
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

        # Fallback to LIKE if FTS5 returned nothing or failed
        if not rows:
            try:
                rows = self.conn.execute(
                    """
                    SELECT p.id, d.title, p.text, p.confidence
                    FROM paragraphs p
                    JOIN documents d ON p.document_id = d.id
                    WHERE p.text LIKE ? OR d.title LIKE ?
                    ORDER BY p.id
                    LIMIT ?
                    """,
                    (f"%{safe_query}%", f"%{safe_query}%", k),
                ).fetchall()
            except sqlite3.OperationalError as exc:
                logger.error("LIKE search also failed: %s", exc)
                return []

        return [
            {"paragraph_id": r[0], "title": r[1], "text": r[2], "confidence": r[3]}
            for r in rows
        ]

    def close(self) -> None:
        self.conn.close()
