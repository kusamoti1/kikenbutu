from __future__ import annotations

import sqlite3
from pathlib import Path

SECTIONS = [
    "概要",
    "昭和基準",
    "平成改正",
    "令和基準",
    "改正理由",
    "関係通知",
    "関係条文",
    "原文",
]


def export_markdown_by_equipment(db_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)

    equipment_rows = conn.execute("SELECT id, name FROM equipment ORDER BY name").fetchall()
    for equipment_id, equipment_name in equipment_rows:
        lines = [f"# {equipment_name}", ""]
        for section in SECTIONS:
            lines.extend([f"## {section}", ""])

        standards = conn.execute(
            "SELECT name FROM standards WHERE equipment_id = ? ORDER BY name", (equipment_id,)
        ).fetchall()
        lines.append("### 関連基準")
        for (name,) in standards:
            lines.append(f"- {name}")

        out = output_dir / f"{equipment_name}.md"
        out.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    conn.close()
