from __future__ import annotations

import sqlite3
from pathlib import Path

MAX_FILE_SIZE_MB = 10


def _write_md(path: Path, title: str, body: str) -> list[Path]:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = f"# {title}\n\n{body}\n"
    b = data.encode("utf-8")
    limit = MAX_FILE_SIZE_MB * 1024 * 1024
    if len(b) <= limit:
        path.write_text(data, encoding="utf-8")
        return [path]

    parts: list[Path] = []
    chunk = []
    size = 0
    idx = 1
    for line in data.splitlines(keepends=True):
        lb = line.encode("utf-8")
        if size + len(lb) > limit and chunk:
            p = path.with_stem(f"{path.stem}_part{idx}")
            p.write_text("".join(chunk), encoding="utf-8")
            parts.append(p)
            chunk, size = [], 0
            idx += 1
        chunk.append(line)
        size += len(lb)
    if chunk:
        p = path.with_stem(f"{path.stem}_part{idx}")
        p.write_text("".join(chunk), encoding="utf-8")
        parts.append(p)
    return parts


def _rows(conn: sqlite3.Connection, sql: str, params=()):
    return conn.execute(sql, params).fetchall()


def export_markdown_bundle(conn: sqlite3.Connection, output_dir: Path) -> list[tuple[str, str, Path]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[tuple[str, str, Path]] = []

    # 1) 設備別
    eq_rows = _rows(
        conn,
        """
        SELECT e.name, d.title, p.text_normalized, p.needs_review, p.confidence_avg
        FROM equipment e
        JOIN document_equipment_links l ON l.equipment_id=e.id
        JOIN documents d ON d.id=l.document_id
        LEFT JOIN paragraphs p ON p.document_id=d.id
        ORDER BY e.name, d.title, p.paragraph_index
        """,
    )
    by_eq: dict[str, list[tuple]] = {}
    for r in eq_rows:
        by_eq.setdefault(r[0], []).append(r)

    for eq, rows in by_eq.items():
        lines = ["## 対象", f"- 設備: {eq}", "", "## 原文引用"]
        for _, title, text, needs_review, conf in rows[:800]:
            if not text:
                continue
            warn = "（OCR低信頼・要人手確認）" if needs_review else ""
            lines.append(f"- [{title}] {text[:240]} {warn} 信頼度:{conf if conf is not None else '不明'}")
        paths = _write_md(output_dir / f"{eq}.md", f"{eq} 向け整理", "\n".join(lines))
        for p in paths:
            records.append(("equipment", eq, p))

    # 2) 差分別
    rev_rows = _rows(
        conn,
        """
        SELECT e.name, r.diff_summary, r.old_text, r.new_text
        FROM revisions r JOIN equipment e ON e.id=r.equipment_id
        ORDER BY e.name, r.id
        """,
    )
    by_rev: dict[str, list[tuple]] = {}
    for r in rev_rows:
        by_rev.setdefault(r[0], []).append(r)
    for eq, rows in by_rev.items():
        lines = ["## 改正差分"]
        for _, summ, old_t, new_t in rows:
            lines += [f"- 差分要約: {summ}", "### 旧基準", old_t[:800], "### 新基準", new_t[:800], ""]
        paths = _write_md(output_dir / f"{eq}_改正差分.md", f"{eq} 改正差分", "\n".join(lines))
        for p in paths:
            records.append(("revision", eq, p))

    # 3) 共通条文別
    law_rows = _rows(
        conn,
        """
        SELECT law_name, article_number, COALESCE(paragraph_number,''), COALESCE(item_number,''), p.text_normalized
        FROM law_article_links l
        JOIN paragraphs p ON p.id=l.paragraph_id
        ORDER BY law_name, article_number
        """,
    )
    by_law: dict[str, list[tuple]] = {}
    for r in law_rows:
        by_law.setdefault(r[0], []).append(r)

    for law, rows in by_law.items():
        lines = ["## 関係条文", f"- 法令名: {law}", ""]
        for _, article, para, item, text in rows[:1200]:
            suffix = "".join([f" 第{para}項" if para else "", f" 第{item}号" if item else ""])
            lines.append(f"- {article}{suffix}: {text[:220]}")
        paths = _write_md(output_dir / f"{law}_関係条文.md", f"{law} 関係条文", "\n".join(lines))
        for p in paths:
            records.append(("law", law, p))

    return records
