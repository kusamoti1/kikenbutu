from __future__ import annotations

from pathlib import Path

import networkx as nx


def build_knowledge_graph(records: list[dict]) -> nx.DiGraph:
    g = nx.DiGraph()
    for rec in records:
        eq = rec.get("equipment", "不明設備")
        std = rec.get("standard", "不明基準")
        ntc = rec.get("notification", "不明通知")
        art = rec.get("article", "不明条文")
        era = rec.get("era", "不明年代")

        g.add_node(eq, type="Equipment")
        g.add_node(std, type="Standard")
        g.add_node(ntc, type="Notification")
        g.add_node(art, type="LawArticle")
        g.add_node(era, type="Era")

        g.add_edge(eq, std, relation="Equipment→Standard")
        g.add_edge(std, ntc, relation="Standard→Notification")
        g.add_edge(ntc, art, relation="Notification→LawArticle")
        g.add_edge(ntc, era, relation="Notification→Era")
    return g


def save_graphml(graph: nx.DiGraph, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(graph, output_path)
