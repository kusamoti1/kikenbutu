"""NotebookLM Markdown exporter.

Generates one Markdown file per equipment type, using deterministic
graph traversal to collect all related content.  When the knowledge
graph is available, data is gathered by traversing
Equipment → Standard → Notification → LawArticle / Era.  This
ensures that every piece of content has a clear provenance path.

Falls back to SQL-only collection when no graph is available.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Optional

import networkx as nx

logger = logging.getLogger(__name__)

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
    "巡回経路",
]

ERA_SECTION_MAP = {
    "昭和": "昭和基準",
    "平成": "平成改正",
    "令和": "令和基準",
}

_MAX_SUMMARY_ITEMS = 30


def export_markdown_by_equipment(
    db_path: Path,
    output_dir: Path,
    graph: Optional[nx.DiGraph] = None,
) -> None:
    """Export Markdown files for NotebookLM.

    If *graph* is provided, content is collected via deterministic
    graph traversal.  Otherwise, plain SQL queries are used.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)

    try:
        equipment_rows = conn.execute("SELECT id, name FROM equipment ORDER BY name").fetchall()
        if not equipment_rows:
            logger.warning("No equipment data found. NotebookLM export skipped.")
            return

        for equipment_id, equipment_name in equipment_rows:
            if graph is not None:
                _export_with_graph(conn, output_dir, equipment_id, equipment_name, graph)
            else:
                _export_sql_only(conn, output_dir, equipment_id, equipment_name)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Graph-based export (deterministic traversal)
# ---------------------------------------------------------------------------

def _export_with_graph(
    conn: sqlite3.Connection,
    output_dir: Path,
    equipment_id: int,
    equipment_name: str,
    graph: nx.DiGraph,
) -> None:
    """Collect content by traversing the knowledge graph."""
    section_content: dict[str, list[str]] = {s: [] for s in SECTIONS}

    start_node = f"Equipment:{equipment_name}"
    if start_node not in graph:
        # Fall back to SQL if the equipment is not in the graph.
        _export_sql_only(conn, output_dir, equipment_id, equipment_name)
        return

    traversal_log: list[str] = [f"起点: Equipment:{equipment_name}"]
    standard_names: list[str] = []

    # Loop 1: Equipment → Standards
    for std_node in graph.successors(start_node):
        std_data = graph.nodes[std_node]
        if std_data.get("type") != "Standard":
            continue
        std_label = std_data.get("label", std_node)
        standard_names.append(std_label)
        section_content["関係通知"].append(f"- {std_label}")
        edge = graph.edges[start_node, std_node]
        traversal_log.append(f"  → ({edge.get('relation', '?')}) Standard:{std_label}")

        # Loop 2: Standard → Notifications
        for ntc_node in graph.successors(std_node):
            ntc_data = graph.nodes[ntc_node]
            if ntc_data.get("type") != "Notification":
                continue
            edge = graph.edges[std_node, ntc_node]
            traversal_log.append(f"    → ({edge.get('relation', '?')}) Notification:{ntc_data.get('label', '')}")

            # Loop 3: Notification → LawArticle / Era
            for leaf_node in graph.successors(ntc_node):
                leaf_data = graph.nodes[leaf_node]
                leaf_label = leaf_data.get("label", leaf_node)
                leaf_type = leaf_data.get("type", "")
                edge = graph.edges[ntc_node, leaf_node]
                traversal_log.append(f"      → ({edge.get('relation', '?')}) {leaf_type}:{leaf_label}")

                if leaf_type == "LawArticle":
                    entry = f"- {leaf_label}"
                    if entry not in section_content["関係条文"]:
                        section_content["関係条文"].append(entry)
                elif leaf_type == "Era":
                    # Record which eras are linked.
                    pass  # Used implicitly by paragraph classification below.

    # Fetch paragraphs from DB (exact match by standard/document name).
    if standard_names:
        placeholders = ", ".join(["?"] * len(standard_names))
        paragraphs = conn.execute(
            f"""
            SELECT p.text FROM paragraphs p
            JOIN documents d ON p.document_id = d.id
            WHERE d.title IN ({placeholders})
            ORDER BY d.title, p.id
            """,
            standard_names,
        ).fetchall()
    else:
        paragraphs = []

    for (text,) in paragraphs:
        section_content["原文"].append(f"> {text}")
        for era_key, section_name in ERA_SECTION_MAP.items():
            if era_key in text:
                section_content[section_name].append(f"- {text[:200]}")

    # Build concise summary.
    total = len(paragraphs)
    summary_lines = [f"- 通知段落数: {total}件"]
    if standard_names:
        summary_lines.append(f"- 関連基準数: {len(standard_names)}件")
    for (text,) in paragraphs[:_MAX_SUMMARY_ITEMS]:
        summary_lines.append(f"- {text[:120]}")
    if total > _MAX_SUMMARY_ITEMS:
        summary_lines.append(f"- （他 {total - _MAX_SUMMARY_ITEMS} 件省略）")
    section_content["概要"] = summary_lines

    # Traversal log section (traceability).
    section_content["巡回経路"] = [f"```", *traversal_log, "```"]

    _write_markdown(output_dir, equipment_name, section_content)


# ---------------------------------------------------------------------------
# SQL-only export (fallback)
# ---------------------------------------------------------------------------

def _export_sql_only(
    conn: sqlite3.Connection,
    output_dir: Path,
    equipment_id: int,
    equipment_name: str,
) -> None:
    """Collect content using SQL queries only (no graph)."""
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
        for era_key, section_name in ERA_SECTION_MAP.items():
            if era_key in text:
                section_content[section_name].append(f"- {text[:200]}")

    total = len(paragraphs)
    summary_lines = [f"- 通知段落数: {total}件"]
    if standards:
        summary_lines.append(f"- 関連基準数: {len(standards)}件")
    for (text,) in paragraphs[:_MAX_SUMMARY_ITEMS]:
        summary_lines.append(f"- {text[:120]}")
    if total > _MAX_SUMMARY_ITEMS:
        summary_lines.append(f"- （他 {total - _MAX_SUMMARY_ITEMS} 件省略）")
    section_content["概要"] = summary_lines

    section_content["巡回経路"] = ["（グラフ未使用 — SQL直接取得）"]

    _write_markdown(output_dir, equipment_name, section_content)


# ---------------------------------------------------------------------------
# Markdown writer
# ---------------------------------------------------------------------------

def _write_markdown(
    output_dir: Path,
    equipment_name: str,
    section_content: dict[str, list[str]],
) -> None:
    """Write the assembled section content to Markdown file(s)."""
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
        _export_split(output_dir, equipment_name, section_content)
    else:
        out = output_dir / f"{equipment_name}.md"
        out.write_text(md_text, encoding="utf-8")


def _export_split(
    output_dir: Path,
    equipment_name: str,
    section_content: dict[str, list[str]],
) -> None:
    """Split large equipment files into era-based parts."""
    base_sections = ["概要", "関係通知", "関係条文", "巡回経路"]
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
