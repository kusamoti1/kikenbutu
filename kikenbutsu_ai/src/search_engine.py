from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List


class SearchEngine:
    """Full-text search engine using SQLite FTS5."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self._ensure_fts()

    def _ensure_fts(self) -> None:
        """Create FTS5 virtual table if it does not exist."""
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

    def rebuild_index(self) -> None:
        """Rebuild the FTS5 index from the paragraphs table."""
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
        except sqlite3.OperationalError:
            rows = self.conn.execute(
                """
                SELECT p.id, d.title, p.text, p.confidence
                FROM paragraphs p
                JOIN documents d ON p.document_id = d.id
                WHERE p.text LIKE ?
                ORDER BY p.id
                LIMIT ?
                """,
                (f"%{safe_query}%", k),
            ).fetchall()

        return [
            {"paragraph_id": r[0], "title": r[1], "text": r[2], "confidence": r[3]}
            for r in rows
        ]

    def close(self) -> None:
        self.conn.close()
