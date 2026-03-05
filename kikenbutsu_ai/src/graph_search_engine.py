"""Deterministic graph-traversal search engine.

Instead of probabilistic text-similarity search (RAG), this module
traverses the knowledge graph using programmatic loops.  Every search
result is backed by an explicit *traversal path* that records which
graph nodes and edges were visited to produce the answer.

Design principles (from the non-RAG architecture proposal):
  - No inference, no interpretation, no probability.
  - Results are collected by following edges deterministically.
  - The traversal log provides full traceability.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import networkx as nx

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TraversalStep:
    """One step in the graph traversal path."""
    node: str
    node_type: str
    relation: str  # edge label that led here ("ROOT" for the starting node)


@dataclass
class TraversalResult:
    """A single search result with full provenance."""
    equipment: str
    standards: List[str]
    notifications: List[str]
    law_articles: List[str]
    eras: List[str]
    paragraphs: List[Dict[str, Any]]  # original text from DB
    traversal_path: List[TraversalStep] = field(default_factory=list)

    @property
    def path_description(self) -> str:
        """Human-readable traversal path for traceability."""
        parts: list[str] = []
        for step in self.traversal_path:
            if step.relation == "ROOT":
                parts.append(f"[起点] {step.node_type}: {step.node}")
            else:
                parts.append(f"  → ({step.relation}) {step.node_type}: {step.node}")
        return "\n".join(parts)


# ---------------------------------------------------------------------------
# Graph I/O
# ---------------------------------------------------------------------------

def load_graph(graphml_path: Path) -> Optional[nx.DiGraph]:
    """Load a previously saved GraphML file."""
    if not graphml_path.exists():
        logger.warning("GraphML not found at %s", graphml_path)
        return None
    try:
        return nx.read_graphml(graphml_path)
    except Exception as exc:
        logger.error("Failed to load GraphML: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Deterministic graph search
# ---------------------------------------------------------------------------

class GraphSearchEngine:
    """Search by deterministic graph traversal — no vector similarity."""

    def __init__(self, graph: nx.DiGraph, db_path: Path):
        self.graph = graph
        self.db_path = db_path
        # Build lookup indices for fast node access.
        self._by_type: Dict[str, List[str]] = {}
        for node, data in graph.nodes(data=True):
            node_type = data.get("type", "Unknown")
            self._by_type.setdefault(node_type, []).append(node)

    # ---------------------------------------------------------------
    # Public search methods
    # ---------------------------------------------------------------

    def search_by_equipment(self, equipment_name: str) -> Optional[TraversalResult]:
        """Traverse the graph starting from an Equipment node.

        Deterministic loop: Equipment → Standard → Notification → LawArticle / Era
        """
        start_node = f"Equipment:{equipment_name}"
        if start_node not in self.graph:
            # Partial match fallback — still deterministic.
            start_node = self._find_node_containing(equipment_name, "Equipment")
            if start_node is None:
                return None

        label = self.graph.nodes[start_node].get("label", equipment_name)
        path: List[TraversalStep] = [TraversalStep(label, "Equipment", "ROOT")]

        standards: List[str] = []
        notifications: List[str] = []
        law_articles: List[str] = []
        eras: List[str] = []
        visited: Set[str] = {start_node}

        # Loop 1: Equipment → Standards
        for std_node in self.graph.successors(start_node):
            if std_node in visited:
                continue
            visited.add(std_node)
            std_data = self.graph.nodes[std_node]
            if std_data.get("type") != "Standard":
                continue
            std_label = std_data.get("label", std_node)
            standards.append(std_label)
            edge_data = self.graph.edges[start_node, std_node]
            path.append(TraversalStep(std_label, "Standard", edge_data.get("relation", "has_standard")))

            # Loop 2: Standard → Notifications
            for ntc_node in self.graph.successors(std_node):
                if ntc_node in visited:
                    continue
                visited.add(ntc_node)
                ntc_data = self.graph.nodes[ntc_node]
                if ntc_data.get("type") != "Notification":
                    continue
                ntc_label = ntc_data.get("label", ntc_node)
                notifications.append(ntc_label)
                edge_data = self.graph.edges[std_node, ntc_node]
                path.append(TraversalStep(ntc_label, "Notification", edge_data.get("relation", "has_notification")))

                # Loop 3: Notification → LawArticle / Era
                for leaf_node in self.graph.successors(ntc_node):
                    if leaf_node in visited:
                        continue
                    visited.add(leaf_node)
                    leaf_data = self.graph.nodes[leaf_node]
                    leaf_label = leaf_data.get("label", leaf_node)
                    leaf_type = leaf_data.get("type", "Unknown")
                    edge_data = self.graph.edges[ntc_node, leaf_node]
                    relation = edge_data.get("relation", "unknown")

                    if leaf_type == "LawArticle":
                        law_articles.append(leaf_label)
                    elif leaf_type == "Era":
                        eras.append(leaf_label)

                    path.append(TraversalStep(leaf_label, leaf_type, relation))

        # Fetch original text from DB — exact match, no similarity.
        paragraphs = self._fetch_paragraphs_for_standards(standards)

        return TraversalResult(
            equipment=label,
            standards=standards,
            notifications=notifications,
            law_articles=_dedupe(law_articles),
            eras=_dedupe(eras),
            paragraphs=paragraphs,
            traversal_path=path,
        )

    def search_by_era(self, era_name: str) -> List[TraversalResult]:
        """Find all equipment linked to a specific era via reverse traversal.

        Era ← Notification ← Standard ← Equipment
        """
        era_node = f"Era:{era_name}"
        if era_node not in self.graph:
            return []

        # Reverse traversal: find all predecessors.
        equipment_names: Set[str] = set()
        for ntc_node in self.graph.predecessors(era_node):
            ntc_data = self.graph.nodes[ntc_node]
            if ntc_data.get("type") != "Notification":
                continue
            for std_node in self.graph.predecessors(ntc_node):
                std_data = self.graph.nodes[std_node]
                if std_data.get("type") != "Standard":
                    continue
                for eq_node in self.graph.predecessors(std_node):
                    eq_data = self.graph.nodes[eq_node]
                    if eq_data.get("type") == "Equipment":
                        equipment_names.add(eq_data.get("label", eq_node))

        results: List[TraversalResult] = []
        for eq_name in sorted(equipment_names):
            result = self.search_by_equipment(eq_name)
            if result:
                results.append(result)
        return results

    def search_by_law_article(self, keyword: str) -> List[TraversalResult]:
        """Find all equipment linked to a law article containing *keyword*.

        LawArticle ← Notification ← Standard ← Equipment
        """
        matching_articles = [
            node for node in self._by_type.get("LawArticle", [])
            if keyword in self.graph.nodes[node].get("label", "")
        ]

        equipment_names: Set[str] = set()
        for art_node in matching_articles:
            for ntc_node in self.graph.predecessors(art_node):
                ntc_data = self.graph.nodes[ntc_node]
                if ntc_data.get("type") != "Notification":
                    continue
                for std_node in self.graph.predecessors(ntc_node):
                    std_data = self.graph.nodes[std_node]
                    if std_data.get("type") != "Standard":
                        continue
                    for eq_node in self.graph.predecessors(std_node):
                        eq_data = self.graph.nodes[eq_node]
                        if eq_data.get("type") == "Equipment":
                            equipment_names.add(eq_data.get("label", eq_node))

        results: List[TraversalResult] = []
        for eq_name in sorted(equipment_names):
            result = self.search_by_equipment(eq_name)
            if result:
                results.append(result)
        return results

    def search(self, query: str) -> List[TraversalResult]:
        """Unified search entry point.

        Tries, in order:
        1. Exact equipment match
        2. Era match
        3. Law article match
        4. Partial equipment name match
        Each step is deterministic — no scoring, no ranking.
        """
        results: List[TraversalResult] = []
        seen_equipment: Set[str] = set()

        # 1. Direct equipment match
        eq_result = self.search_by_equipment(query)
        if eq_result:
            results.append(eq_result)
            seen_equipment.add(eq_result.equipment)

        # 2. Era match
        if query in ("昭和", "平成", "令和"):
            for r in self.search_by_era(query):
                if r.equipment not in seen_equipment:
                    results.append(r)
                    seen_equipment.add(r.equipment)

        # 3. Law article keyword match
        if not results:
            for r in self.search_by_law_article(query):
                if r.equipment not in seen_equipment:
                    results.append(r)
                    seen_equipment.add(r.equipment)

        # 4. Scan all equipment nodes for partial match
        if not results:
            for eq_node in self._by_type.get("Equipment", []):
                eq_label = self.graph.nodes[eq_node].get("label", "")
                if query in eq_label or eq_label in query:
                    r = self.search_by_equipment(eq_label)
                    if r and r.equipment not in seen_equipment:
                        results.append(r)
                        seen_equipment.add(r.equipment)

        return results

    # ---------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------

    def _find_node_containing(self, text: str, node_type: str) -> Optional[str]:
        """Find a node whose label contains *text* (deterministic scan)."""
        for node in self._by_type.get(node_type, []):
            label = self.graph.nodes[node].get("label", "")
            if text in label or label in text:
                return node
        return None

    def _fetch_paragraphs_for_standards(self, standard_names: List[str]) -> List[Dict[str, Any]]:
        """Fetch original paragraphs from SQLite for given standard (document) names.

        This is a deterministic exact-match query — not a similarity search.
        """
        if not standard_names:
            return []

        conn = sqlite3.connect(self.db_path)
        try:
            placeholders = ", ".join(["?"] * len(standard_names))
            rows = conn.execute(
                f"""
                SELECT d.title, p.text, p.confidence, COALESCE(p.context, '')
                FROM paragraphs p
                JOIN documents d ON p.document_id = d.id
                WHERE d.title IN ({placeholders})
                ORDER BY d.title, p.id
                """,
                standard_names,
            ).fetchall()
            return [
                {"title": r[0], "text": r[1], "confidence": r[2], "context": r[3]}
                for r in rows
            ]
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _dedupe(items: List[str]) -> List[str]:
    """Remove duplicates while preserving order."""
    seen: Set[str] = set()
    result: List[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def format_result_as_guarded_answer(result: TraversalResult) -> str:
    """Format a TraversalResult in the misinterpretation-guard output format.

    This function does NOT interpret or summarise — it only arranges
    the deterministically-collected data into the required output structure.
    """
    lines: List[str] = []
    lines.append("【結論】")
    lines.append(f"設備「{result.equipment}」に関する通知 {len(result.notifications)} 件を検出しました。")
    lines.append("")

    lines.append("【根拠法令】")
    if result.law_articles:
        for art in result.law_articles:
            lines.append(f"  - {art}")
    else:
        lines.append("  （条文リンクなし）")
    lines.append("")

    lines.append("【通知】")
    for ntc in result.notifications:
        lines.append(f"  - {ntc}")
    lines.append("")

    lines.append("【年代】")
    lines.append(f"  {', '.join(result.eras) if result.eras else '不明'}")
    lines.append("")

    lines.append("【原文引用】")
    for p in result.paragraphs[:10]:  # First 10 paragraphs as preview
        lines.append(f"  > {p['text'][:300]}")
    if len(result.paragraphs) > 10:
        lines.append(f"  （他 {len(result.paragraphs) - 10} 段落）")
    lines.append("")

    lines.append("【信頼度】")
    lines.append("  1.00（決定論的グラフ巡回による確定結果）")
    lines.append("")

    lines.append("【巡回経路（トレーサビリティ）】")
    lines.append(result.path_description)

    return "\n".join(lines)
