from __future__ import annotations

import sqlite3
from pathlib import Path


class SearchEngine:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)

    def search_fts(self, query: str, limit: int = 20):
        if not query.strip():
            return []
        try:
            return self.conn.execute(
                """
                SELECT p.id, d.title, COALESCE(d.era_label,'不明'), COALESCE(p.equipment_guess,'共通法令'),
                       COALESCE(p.text_normalized,p.text,''), p.confidence_avg, p.needs_review,
                       COALESCE(p.confidence_known,0), COALESCE(p.ocr_source,'imported_text')
                FROM paragraphs_fts f
                JOIN paragraphs p ON p.id=f.paragraph_id
                JOIN documents d ON d.id=p.document_id
                WHERE paragraphs_fts MATCH ?
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            like = f"%{query}%"
            return self.conn.execute(
                """
                SELECT p.id, d.title, COALESCE(d.era_label,'不明'), COALESCE(p.equipment_guess,'共通法令'),
                       COALESCE(p.text_normalized,p.text,''), p.confidence_avg, p.needs_review,
                       COALESCE(p.confidence_known,0), COALESCE(p.ocr_source,'imported_text')
                FROM paragraphs p JOIN documents d ON d.id=p.document_id
                WHERE COALESCE(p.text_normalized,p.text,'') LIKE ? OR d.title LIKE ?
                LIMIT ?
                """,
                (like, like, limit),
            ).fetchall()

    def search_by_era(self, era: str, query: str = "", limit: int = 80):
        if query.strip():
            like = f"%{query.strip()}%"
            return self.conn.execute(
                """
                SELECT p.id, d.title, COALESCE(d.era_label,'不明'), COALESCE(p.equipment_guess,'共通法令'),
                       COALESCE(p.text_normalized,p.text,''), p.confidence_avg, p.needs_review,
                       COALESCE(p.confidence_known,0), COALESCE(p.ocr_source,'imported_text')
                FROM paragraphs p JOIN documents d ON d.id=p.document_id
                WHERE COALESCE(d.era_label,'不明') = ?
                  AND (COALESCE(p.text_normalized,p.text,'') LIKE ? OR d.title LIKE ?)
                ORDER BY d.year, p.paragraph_index
                LIMIT ?
                """,
                (era, like, like, limit),
            ).fetchall()

        return self.conn.execute(
            """
            SELECT p.id, d.title, COALESCE(d.era_label,'不明'), COALESCE(p.equipment_guess,'共通法令'),
                   COALESCE(p.text_normalized,p.text,''), p.confidence_avg, p.needs_review,
                   COALESCE(p.confidence_known,0), COALESCE(p.ocr_source,'imported_text')
            FROM paragraphs p JOIN documents d ON d.id=p.document_id
            WHERE COALESCE(d.era_label,'不明') = ?
            ORDER BY d.year, p.paragraph_index
            LIMIT ?
            """,
            (era, limit),
        ).fetchall()

    def search_by_equipment(self, equipment: str, limit: int = 30):
        return self.conn.execute(
            """
            SELECT d.title, COALESCE(d.era_label,'不明'), COALESCE(p.text_normalized,p.text,''),
                   p.confidence_avg, p.needs_review, COALESCE(p.confidence_known,0), COALESCE(p.ocr_source,'imported_text')
            FROM equipment e
            JOIN document_equipment_links l ON l.equipment_id=e.id
            JOIN documents d ON d.id=l.document_id
            LEFT JOIN paragraphs p ON p.document_id=d.id
            WHERE e.name = ?
            ORDER BY d.year, p.paragraph_index
            LIMIT ?
            """,
            (equipment, limit),
        ).fetchall()

    def search_revisions(self, equipment: str | None = None, limit: int = 50):
        if equipment:
            return self.conn.execute(
                """
                SELECT e.name, r.topic_label, r.diff_summary, r.old_text, r.new_text,
                       od.title, nd.title
                FROM revisions r
                JOIN equipment e ON e.id=r.equipment_id
                JOIN documents od ON od.id=r.old_document_id
                JOIN documents nd ON nd.id=r.new_document_id
                WHERE e.name = ?
                ORDER BY r.id DESC LIMIT ?
                """,
                (equipment, limit),
            ).fetchall()
        return self.conn.execute(
            """
            SELECT e.name, r.topic_label, r.diff_summary, r.old_text, r.new_text,
                   od.title, nd.title
            FROM revisions r
            JOIN equipment e ON e.id=r.equipment_id
            JOIN documents od ON od.id=r.old_document_id
            JOIN documents nd ON nd.id=r.new_document_id
            ORDER BY r.id DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()

    def inspection_bundle(self, equipment: str):
        req = self.conn.execute(
            """
            SELECT lr.requirement_label, lr.requirement_text, lr.confidence, lr.needs_review
            FROM legal_requirements lr
            JOIN equipment e ON e.id=lr.equipment_id
            WHERE e.name=?
            ORDER BY lr.id DESC LIMIT 50
            """,
            (equipment,),
        ).fetchall()
        laws = self.conn.execute(
            """
            SELECT l.law_name, l.article_number, COALESCE(l.paragraph_number,''), COALESCE(l.item_number,''),
                   p.text_normalized, COALESCE(p.confidence_known,0), p.confidence_avg, p.needs_review
            FROM law_article_links l JOIN paragraphs p ON p.id=l.paragraph_id
            WHERE p.equipment_guess=?
            LIMIT 80
            """,
            (equipment,),
        ).fetchall()
        return req, laws
