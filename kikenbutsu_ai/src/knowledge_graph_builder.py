from __future__ import annotations

import sqlite3
from pathlib import Path

import networkx as nx


def build_knowledge_graph(conn: sqlite3.Connection) -> nx.DiGraph:
    """v2スキーマ準拠グラフを作成する。Standardノードは作らない。"""
    g = nx.DiGraph()

    for doc_id, title, era in conn.execute("SELECT id, title, COALESCE(era_label, '不明') FROM documents"):
        d_node = f"Document:{doc_id}"
        g.add_node(d_node, type="Document", label=title)

        era_node = f"Era:{era}"
        g.add_node(era_node, type="Era", label=era)
        g.add_edge(d_node, era_node, relation="has_era")

    for p_id, doc_id, sec in conn.execute("SELECT id, document_id, COALESCE(section_label,'本文') FROM paragraphs"):
        p_node = f"Paragraph:{p_id}"
        d_node = f"Document:{doc_id}"
        g.add_node(p_node, type="Paragraph", label=f"段落{p_id}:{sec}")
        g.add_edge(d_node, p_node, relation="has_paragraph")

    for eq_id, name in conn.execute("SELECT id, name FROM equipment"):
        e_node = f"Equipment:{eq_id}"
        g.add_node(e_node, type="Equipment", label=name)

    for doc_id, eq_id, conf in conn.execute("SELECT document_id, equipment_id, confidence FROM document_equipment_links"):
        g.add_edge(f"Document:{doc_id}", f"Equipment:{eq_id}", relation=f"related:{conf:.2f}")

    for lr_id, p_id, eq_id, label in conn.execute(
        "SELECT id, paragraph_id, equipment_id, COALESCE(requirement_label,'要件') FROM legal_requirements"
    ):
        lr_node = f"LegalRequirement:{lr_id}"
        g.add_node(lr_node, type="LegalRequirement", label=label)
        g.add_edge(f"Paragraph:{p_id}", lr_node, relation="has_requirement")
        g.add_edge(lr_node, f"Equipment:{eq_id}", relation="for_equipment")

    for l_id, p_id, law, art in conn.execute("SELECT id, paragraph_id, law_name, article_number FROM law_article_links"):
        la_node = f"LawArticle:{l_id}"
        g.add_node(la_node, type="LawArticle", label=f"{law} {art}")
        g.add_edge(f"Paragraph:{p_id}", la_node, relation="references")

    for rev_id, old_p, new_p in conn.execute("SELECT id, old_paragraph_id, new_paragraph_id FROM revisions"):
        r_node = f"Revision:{rev_id}"
        g.add_node(r_node, type="Revision", label=f"改正差分{rev_id}")
        g.add_edge(r_node, f"Paragraph:{old_p}", relation="old")
        g.add_edge(r_node, f"Paragraph:{new_p}", relation="new")

    return g


def save_graphml(graph: nx.DiGraph, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(graph, output_path)
