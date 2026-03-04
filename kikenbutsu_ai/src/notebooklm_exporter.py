from __future__ import annotations

import sqlite3
from pathlib import Path

MAX_FILE_SIZE_MB = 10

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

ERA_SECTION_MAP = {
    "昭和": "昭和基準",
    "平成": "平成改正",
    "令和": "令和基準",
}


def export_markdown_by_equipment(db_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)

    equipment_rows = conn.execute("SELECT id, name FROM equipment ORDER BY name").fetchall()
    for equipment_id, equipment_name in equipment_rows:
        section_content: dict[str, list[str]] = {s: [] for s in SECTIONS}

        standards = conn.execute(
            "SELECT id, name FROM standards WHERE equipment_id = ? ORDER BY name", (equipment_id,)
        ).fetchall()

        for std_id, std_name in standards:
            section_content["関係通知"].append(f"- {std_name}")

            law_links = conn.execute(
                "SELECT law_name, article_number FROM law_article_links WHERE standard_id = ?",
                (std_id,),
            ).fetchall()
            for law_name, article_number in law_links:
                entry = f"- {law_name} {article_number}"
                if entry not in section_content["関係条文"]:
                    section_content["関係条文"].append(entry)

        paragraphs = conn.execute(
            """
            SELECT p.text FROM paragraphs p
            JOIN documents d ON p.document_id = d.id
            JOIN standards s ON s.name = d.title
            WHERE s.equipment_id = ?
            ORDER BY d.title, p.id
            """,
            (equipment_id,),
        ).fetchall()

        for (text,) in paragraphs:
            section_content["原文"].append(f"> {text}")
            section_content["概要"].append(f"- {text[:100]}...")

            for era_key, section_name in ERA_SECTION_MAP.items():
                if era_key in text:
                    section_content[section_name].append(f"- {text[:200]}")

        lines = [f"# {equipment_name}", ""]
        for section in SECTIONS:
            lines.append(f"## {section}")
            lines.append("")
            content = section_content.get(section, [])
            if content:
                lines.extend(content)
            else:
                lines.append("（データなし）")
            lines.append("")

        md_text = "\n".join(lines).strip() + "\n"

        size_mb = len(md_text.encode("utf-8")) / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            _export_split(output_dir, equipment_name, section_content, SECTIONS)
        else:
            out = output_dir / f"{equipment_name}.md"
            out.write_text(md_text, encoding="utf-8")

    conn.close()


def _export_split(
    output_dir: Path,
    equipment_name: str,
    section_content: dict[str, list[str]],
    sections: list[str],
) -> None:
    """Split large equipment files into era-based parts."""
    base_sections = ["概要", "関係通知", "関係条文"]
    era_sections = ["昭和基準", "平成改正", "令和基準"]
    detail_sections = ["改正理由", "原文"]

    lines = [f"# {equipment_name}（概要）", ""]
    for s in base_sections:
        lines.extend([f"## {s}", ""])
        lines.extend(section_content.get(s, ["（データなし）"]))
        lines.append("")
    out = output_dir / f"{equipment_name}_概要.md"
    out.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    for s in era_sections:
        content = section_content.get(s, [])
        if not content:
            continue
        lines = [f"# {equipment_name} — {s}", ""]
        lines.extend(content)
        lines.append("")
        out = output_dir / f"{equipment_name}_{s}.md"
        out.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")

    for s in detail_sections:
        content = section_content.get(s, [])
        if not content:
            continue
        lines = [f"# {equipment_name} — {s}", ""]
        lines.extend(content)
        lines.append("")
        out = output_dir / f"{equipment_name}_{s}.md"
        out.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
