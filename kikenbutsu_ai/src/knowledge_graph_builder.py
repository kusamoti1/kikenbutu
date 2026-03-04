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

        eq_id = f"Equipment:{eq}"
        std_id = f"Standard:{std}"
        ntc_id = f"Notification:{ntc}"
        art_id = f"LawArticle:{art}"
        era_id = f"Era:{era}"

        g.add_node(eq_id, type="Equipment", label=eq)
        g.add_node(std_id, type="Standard", label=std)
        g.add_node(ntc_id, type="Notification", label=ntc)
        g.add_node(art_id, type="LawArticle", label=art)
        g.add_node(era_id, type="Era", label=era)

        g.add_edge(eq_id, std_id, relation="has_standard")
        g.add_edge(std_id, ntc_id, relation="has_notification")
        g.add_edge(ntc_id, art_id, relation="references_article")
        g.add_edge(ntc_id, era_id, relation="belongs_to_era")
    return g


def save_graphml(graph: nx.DiGraph, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(graph, output_path)
