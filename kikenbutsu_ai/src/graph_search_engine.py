"""決定論グラフ検索（v2スキーマ準拠）。

旧Standardモデルは使わず、Document/Paragraph中心で辿る。
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import networkx as nx


@dataclass
class TraversalStep:
    node: str
    node_type: str
    relation: str


@dataclass
class TraversalResult:
    equipment: str
    documents: List[str]
    law_articles: List[str]
    eras: List[str]
    paragraphs: List[Dict[str, Any]]
    traversal_path: List[TraversalStep] = field(default_factory=list)


class GraphSearchEngine:
    def __init__(self, graph: nx.DiGraph, db_path: Path):
        self.graph = graph
        self._conn = sqlite3.connect(db_path, check_same_thread=False)

    def close(self) -> None:
        self._conn.close()

    def search_by_equipment(self, equipment_name: str) -> Optional[TraversalResult]:
        # Equipmentノードをラベル一致で探索
        eq_node = None
        for n, d in self.graph.nodes(data=True):
            if d.get("type") == "Equipment" and d.get("label") == equipment_name:
                eq_node = n
                break
        if not eq_node:
            return None

        path = [TraversalStep(equipment_name, "Equipment", "ROOT")]
        docs: list[str] = []
        paragraphs: list[dict[str, Any]] = []
        laws: list[str] = []
        eras: list[str] = []

        # Document -> Equipment の逆辺から文書を回収
        for doc_node in self.graph.predecessors(eq_node):
            d = self.graph.nodes[doc_node]
            if d.get("type") != "Document":
                continue
            doc_label = d.get("label", doc_node)
            docs.append(doc_label)
            path.append(TraversalStep(doc_label, "Document", "related"))

            # 文書配下の段落
            for p_node in self.graph.successors(doc_node):
                pd = self.graph.nodes[p_node]
                if pd.get("type") == "Paragraph":
                    path.append(TraversalStep(pd.get("label", p_node), "Paragraph", "has_paragraph"))

            # 年代
            for e_node in self.graph.successors(doc_node):
                ed = self.graph.nodes[e_node]
                if ed.get("type") == "Era":
                    eras.append(ed.get("label", "不明"))

        # DB原文
        if docs:
            placeholders = ",".join(["?"] * len(docs))
            rows = self._conn.execute(
                f"""
                SELECT d.title, COALESCE(p.text_normalized,p.text,''), p.confidence_avg, p.needs_review
                FROM documents d JOIN paragraphs p ON p.document_id=d.id
                WHERE d.title IN ({placeholders})
                ORDER BY d.title, p.paragraph_index
                LIMIT 200
                """,
                docs,
            ).fetchall()
            for t, txt, c, r in rows:
                paragraphs.append({"title": t, "text": txt, "confidence": c, "needs_review": r})

        # LawArticleはParagraph→LawArticle辺から拾う
        for n, d in self.graph.nodes(data=True):
            if d.get("type") != "LawArticle":
                continue
            laws.append(d.get("label", n))

        return TraversalResult(
            equipment=equipment_name,
            documents=sorted(set(docs)),
            law_articles=sorted(set(laws)),
            eras=sorted(set(eras)),
            paragraphs=paragraphs,
            traversal_path=path,
        )


def load_graph(graphml_path: Path) -> Optional[nx.DiGraph]:
    if not graphml_path.exists():
        return None
    return nx.read_graphml(graphml_path)
