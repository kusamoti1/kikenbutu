from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, List, Tuple

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    year INTEGER,
    source TEXT,
    file_path TEXT,
    UNIQUE(title, file_path)
);

CREATE TABLE IF NOT EXISTS paragraphs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER,
    text TEXT,
    context TEXT DEFAULT '',
    confidence REAL,
    FOREIGN KEY(document_id) REFERENCES documents(id)
);

CREATE TABLE IF NOT EXISTS equipment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS standards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id INTEGER,
    name TEXT,
    FOREIGN KEY(equipment_id) REFERENCES equipment(id),
    UNIQUE(equipment_id, name)
);

CREATE TABLE IF NOT EXISTS eras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS law_diff (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    standard_id INTEGER,
    era_old TEXT,
    era_new TEXT,
    difference TEXT,
    FOREIGN KEY(standard_id) REFERENCES standards(id)
);

CREATE TABLE IF NOT EXISTS revision_reason (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    standard_id INTEGER,
    reason TEXT,
    FOREIGN KEY(standard_id) REFERENCES standards(id)
);

CREATE TABLE IF NOT EXISTS law_article_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    standard_id INTEGER,
    law_name TEXT,
    article_number TEXT,
    FOREIGN KEY(standard_id) REFERENCES standards(id),
    UNIQUE(standard_id, law_name, article_number)
);
"""


def connect_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    # WAL mode allows concurrent reads (Streamlit) while pipeline writes.
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    return conn


def document_exists(conn: sqlite3.Connection, title: str, file_path: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM documents WHERE title = ? AND file_path = ?",
        (title, file_path),
    ).fetchone()
    return row is not None


def insert_document(conn: sqlite3.Connection, title: str, year: int | None, source: str, file_path: str) -> int:
    """Insert a document and return its id.

    Uses INSERT OR IGNORE, then always SELECTs the id to avoid the
    ``cursor.lastrowid`` pitfall where an ignored INSERT leaves
    ``lastrowid`` pointing at a *previous* successful insert.
    """
    conn.execute(
        "INSERT OR IGNORE INTO documents (title, year, source, file_path) VALUES (?, ?, ?, ?)",
        (title, year, source, file_path),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id FROM documents WHERE title = ? AND file_path = ?",
        (title, file_path),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"Failed to retrieve document id for title={title!r}, file_path={file_path!r}")
    return int(row[0])


def insert_paragraphs(conn: sqlite3.Connection, document_id: int, rows: Iterable[Tuple[str, float]]) -> None:
    conn.executemany(
        "INSERT INTO paragraphs (document_id, text, confidence) VALUES (?, ?, ?)",
        [(document_id, text, confidence) for text, confidence in rows],
    )
    conn.commit()


def insert_contextual_paragraphs(
    conn: sqlite3.Connection,
    document_id: int,
    rows: Iterable[Tuple[str, str, float]],
) -> None:
    """Insert paragraphs with their context prefix."""
    conn.executemany(
        "INSERT INTO paragraphs (document_id, text, context, confidence) VALUES (?, ?, ?, ?)",
        [(document_id, text, context, confidence) for text, context, confidence in rows],
    )
    conn.commit()


def ensure_equipment(conn: sqlite3.Connection, name: str) -> int:
    conn.execute("INSERT OR IGNORE INTO equipment (name) VALUES (?)", (name,))
    conn.commit()
    row = conn.execute("SELECT id FROM equipment WHERE name = ?", (name,)).fetchone()
    return int(row[0])


def ensure_standard(conn: sqlite3.Connection, equipment_id: int, name: str) -> int:
    conn.execute(
        "INSERT OR IGNORE INTO standards (equipment_id, name) VALUES (?, ?)",
        (equipment_id, name),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id FROM standards WHERE equipment_id = ? AND name = ?",
        (equipment_id, name),
    ).fetchone()
    return int(row[0])


def insert_law_article_links(conn: sqlite3.Connection, standard_id: int, links: List[Tuple[str, str]]) -> None:
    if not links:
        return
    conn.executemany(
        "INSERT OR IGNORE INTO law_article_links (standard_id, law_name, article_number) VALUES (?, ?, ?)",
        [(standard_id, law_name, article_number) for law_name, article_number in links],
    )
    conn.commit()
