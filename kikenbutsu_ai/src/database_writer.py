from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    year INTEGER,
    era_label TEXT,
    source TEXT,
    document_type TEXT,
    file_path TEXT,
    file_hash TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(file_hash)
);

CREATE TABLE IF NOT EXISTS paragraphs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    paragraph_index INTEGER,
    section_label TEXT,
    text_original TEXT,
    text_normalized TEXT,
    confidence_avg REAL,
    confidence_min REAL,
    confidence_known INTEGER DEFAULT 0,
    ocr_source TEXT DEFAULT 'imported_text',
    needs_review INTEGER DEFAULT 1,
    correction_applied INTEGER DEFAULT 0,
    old_kanji_converted INTEGER DEFAULT 0,
    equipment_guess TEXT,
    ocr_applied INTEGER DEFAULT 0,
    preprocess_notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    -- 既存互換
    text TEXT,
    context TEXT DEFAULT '',
    confidence REAL,
    FOREIGN KEY(document_id) REFERENCES documents(id)
);

CREATE TABLE IF NOT EXISTS equipment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE,
    canonical_name TEXT
);

CREATE TABLE IF NOT EXISTS document_equipment_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER,
    equipment_id INTEGER,
    confidence REAL,
    UNIQUE(document_id, equipment_id),
    FOREIGN KEY(document_id) REFERENCES documents(id),
    FOREIGN KEY(equipment_id) REFERENCES equipment(id)
);

CREATE TABLE IF NOT EXISTS legal_requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER,
    paragraph_id INTEGER,
    equipment_id INTEGER,
    requirement_label TEXT,
    requirement_text TEXT,
    confidence REAL,
    needs_review INTEGER DEFAULT 0,
    FOREIGN KEY(document_id) REFERENCES documents(id),
    FOREIGN KEY(paragraph_id) REFERENCES paragraphs(id),
    FOREIGN KEY(equipment_id) REFERENCES equipment(id)
);

CREATE TABLE IF NOT EXISTS eras (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS revisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipment_id INTEGER,
    topic_label TEXT,
    old_document_id INTEGER,
    new_document_id INTEGER,
    old_paragraph_id INTEGER,
    new_paragraph_id INTEGER,
    diff_summary TEXT,
    old_text TEXT,
    new_text TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(equipment_id) REFERENCES equipment(id)
);

CREATE TABLE IF NOT EXISTS revision_reasons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    revision_id INTEGER,
    reason_text TEXT,
    confidence REAL,
    FOREIGN KEY(revision_id) REFERENCES revisions(id)
);

CREATE TABLE IF NOT EXISTS law_article_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    paragraph_id INTEGER,
    law_name TEXT,
    article_number TEXT,
    paragraph_number TEXT,
    item_number TEXT,
    link_confidence REAL,
    UNIQUE(paragraph_id, law_name, article_number, paragraph_number, item_number),
    FOREIGN KEY(paragraph_id) REFERENCES paragraphs(id)
);

CREATE TABLE IF NOT EXISTS search_index_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER,
    paragraph_id INTEGER,
    chunk_path TEXT,
    embedding_ready INTEGER DEFAULT 0,
    fts_ready INTEGER DEFAULT 0,
    FOREIGN KEY(document_id) REFERENCES documents(id),
    FOREIGN KEY(paragraph_id) REFERENCES paragraphs(id)
);

CREATE TABLE IF NOT EXISTS export_metadata (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    export_type TEXT,
    target_name TEXT,
    file_path TEXT,
    generated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE VIRTUAL TABLE IF NOT EXISTS paragraphs_fts USING fts5(
    paragraph_id UNINDEXED,
    title,
    context,
    text,
    tokenize='unicode61'
);
"""


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")
        conn.commit()


def connect_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    # 旧DBからの移行用（不足カラムがある場合に追加）
    _ensure_column(conn, "paragraphs", "confidence_known", "confidence_known INTEGER DEFAULT 0")
    _ensure_column(conn, "paragraphs", "ocr_source", "ocr_source TEXT DEFAULT 'imported_text'")
    return conn


def document_exists(conn: sqlite3.Connection, file_hash: str) -> bool:
    row = conn.execute("SELECT 1 FROM documents WHERE file_hash = ?", (file_hash,)).fetchone()
    return row is not None


def insert_document(
    conn: sqlite3.Connection,
    title: str,
    year: int | None,
    era_label: str | None,
    source: str,
    document_type: str,
    file_path: str,
    file_hash: str,
) -> int:
    conn.execute(
        """
        INSERT OR IGNORE INTO documents
        (title, year, era_label, source, document_type, file_path, file_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (title, year, era_label, source, document_type, file_path, file_hash),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM documents WHERE file_hash = ?", (file_hash,)).fetchone()
    if row is None:
        raise RuntimeError("document id not found")
    return int(row[0])


def ensure_equipment(conn: sqlite3.Connection, name: str, canonical_name: str | None = None) -> int:
    conn.execute(
        "INSERT OR IGNORE INTO equipment (name, canonical_name) VALUES (?, ?)",
        (name, canonical_name or name),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM equipment WHERE name = ?", (name,)).fetchone()
    return int(row[0])


def link_document_equipment(conn: sqlite3.Connection, document_id: int, equipment_id: int, confidence: float) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO document_equipment_links (document_id, equipment_id, confidence) VALUES (?, ?, ?)",
        (document_id, equipment_id, confidence),
    )
    conn.commit()


def insert_paragraph(
    conn: sqlite3.Connection,
    document_id: int,
    paragraph_index: int,
    section_label: str,
    text_original: str,
    text_normalized: str,
    confidence_avg: float | None,
    confidence_min: float | None,
    confidence_known: bool,
    ocr_source: str,
    needs_review: bool,
    correction_applied: bool,
    old_kanji_converted: bool,
    equipment_guess: str,
    ocr_applied: bool,
    preprocess_notes: str,
    context: str,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO paragraphs (
            document_id, paragraph_index, section_label,
            text_original, text_normalized,
            confidence_avg, confidence_min, confidence_known, ocr_source, needs_review,
            correction_applied, old_kanji_converted, equipment_guess,
            ocr_applied, preprocess_notes,
            text, context, confidence
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            document_id,
            paragraph_index,
            section_label,
            text_original,
            text_normalized,
            confidence_avg,
            confidence_min,
            int(confidence_known),
            ocr_source,
            int(needs_review),
            int(correction_applied),
            int(old_kanji_converted),
            equipment_guess,
            int(ocr_applied),
            preprocess_notes,
            text_normalized,
            context,
            confidence_avg,
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def insert_law_article_links(
    conn: sqlite3.Connection,
    paragraph_id: int,
    links: Iterable[tuple[str, str, str | None, str | None, float]],
) -> None:
    conn.executemany(
        """
        INSERT OR IGNORE INTO law_article_links
        (paragraph_id, law_name, article_number, paragraph_number, item_number, link_confidence)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [(paragraph_id, law, art, para, item, conf) for law, art, para, item, conf in links],
    )
    conn.commit()


def insert_legal_requirement(
    conn: sqlite3.Connection,
    document_id: int,
    paragraph_id: int,
    equipment_id: int,
    requirement_label: str,
    requirement_text: str,
    confidence: float,
    needs_review: bool,
) -> None:
    conn.execute(
        """
        INSERT INTO legal_requirements
        (document_id, paragraph_id, equipment_id, requirement_label, requirement_text, confidence, needs_review)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (document_id, paragraph_id, equipment_id, requirement_label, requirement_text, confidence, int(needs_review)),
    )
    conn.commit()


def ensure_era(conn: sqlite3.Connection, name: str) -> int:
    conn.execute("INSERT OR IGNORE INTO eras (name) VALUES (?)", (name,))
    conn.commit()
    row = conn.execute("SELECT id FROM eras WHERE name = ?", (name,)).fetchone()
    return int(row[0])


def insert_revision(
    conn: sqlite3.Connection,
    equipment_id: int,
    topic_label: str,
    old_document_id: int,
    new_document_id: int,
    old_paragraph_id: int,
    new_paragraph_id: int,
    diff_summary: str,
    old_text: str,
    new_text: str,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO revisions
        (equipment_id, topic_label, old_document_id, new_document_id, old_paragraph_id, new_paragraph_id, diff_summary, old_text, new_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (equipment_id, topic_label, old_document_id, new_document_id, old_paragraph_id, new_paragraph_id, diff_summary, old_text, new_text),
    )
    conn.commit()
    return int(cur.lastrowid)


def insert_revision_reasons(conn: sqlite3.Connection, revision_id: int, reasons: Iterable[tuple[str, float]]) -> None:
    conn.executemany(
        "INSERT INTO revision_reasons (revision_id, reason_text, confidence) VALUES (?, ?, ?)",
        [(revision_id, txt, conf) for txt, conf in reasons],
    )
    conn.commit()


def upsert_fts(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        """
        SELECT p.id, d.title, COALESCE(p.context,''), COALESCE(p.text_normalized, p.text, '')
        FROM paragraphs p JOIN documents d ON p.document_id=d.id
        """
    ).fetchall()
    with conn:
        conn.execute("DELETE FROM paragraphs_fts")
        if rows:
            conn.executemany(
                "INSERT INTO paragraphs_fts (paragraph_id, title, context, text) VALUES (?, ?, ?, ?)",
                rows,
            )


def record_export_metadata(conn: sqlite3.Connection, export_type: str, target_name: str, file_path: str) -> None:
    conn.execute(
        "INSERT INTO export_metadata (export_type, target_name, file_path) VALUES (?, ?, ?)",
        (export_type, target_name, file_path),
    )
    conn.commit()
