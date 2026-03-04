from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, Tuple

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    year INTEGER,
    source TEXT,
    file_path TEXT
);

CREATE TABLE IF NOT EXISTS paragraphs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER,
    text TEXT,
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
    FOREIGN KEY(equipment_id) REFERENCES equipment(id)
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
    FOREIGN KEY(standard_id) REFERENCES standards(id)
);
"""


def connect_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn


def insert_document(conn: sqlite3.Connection, title: str, year: int | None, source: str, file_path: str) -> int:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO documents (title, year, source, file_path) VALUES (?, ?, ?, ?)",
        (title, year, source, file_path),
    )
    conn.commit()
    return int(cur.lastrowid)


def insert_paragraphs(conn: sqlite3.Connection, document_id: int, rows: Iterable[Tuple[str, float]]) -> None:
    conn.executemany(
        "INSERT INTO paragraphs (document_id, text, confidence) VALUES (?, ?, ?)",
        [(document_id, text, confidence) for text, confidence in rows],
    )
    conn.commit()
