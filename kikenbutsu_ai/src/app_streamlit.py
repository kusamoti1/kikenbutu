from __future__ import annotations

import sys
from pathlib import Path

# Ensure the src directory is on sys.path so sibling module imports work
# regardless of how Streamlit is launched.
_SRC_DIR = Path(__file__).resolve().parent
_PROJECT_DIR = _SRC_DIR.parent
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
if str(_PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(_PROJECT_DIR))

import streamlit as st

from graph_search_engine import (
    GraphSearchEngine,
    TraversalResult,
    load_graph,
)
from inspection_ai import list_required_standards
from search_engine import SearchEngine

BASE_DIR = _PROJECT_DIR
DB_PATH = BASE_DIR / "database" / "kikenbutsu.db"
GRAPH_PATH = BASE_DIR / "database" / "knowledge_graph.graphml"

st.set_page_config(page_title="危険物法令ナレッジグラフAI", layout="centered")
st.title("危険物法令ナレッジグラフAI")

if not DB_PATH.exists():
    st.warning("database/kikenbutsu.db が見つかりません。先に run_pipeline.py を実行してください。")
    st.stop()


@st.cache_resource
def get_fts_engine() -> SearchEngine:
    engine = SearchEngine(DB_PATH)
    engine.rebuild_index()
    return engine


@st.cache_resource
def get_graph_engine() -> GraphSearchEngine | None:
    graph = load_graph(GRAPH_PATH)
    if graph is None:
        return None
    return GraphSearchEngine(graph, DB_PATH)


fts_engine = get_fts_engine()
graph_engine = get_graph_engine()

tab1, tab2, tab3, tab4 = st.tabs(["設備検索", "年代検索", "差分検索", "査察AI"])


# ---------------------------------------------------------------------------
# Helper: display a TraversalResult
# ---------------------------------------------------------------------------

def _show_traversal_result(result: TraversalResult) -> None:
    """Render one TraversalResult in the Streamlit UI."""
    st.markdown("---")
    st.write(f"### 設備: {result.equipment}")

    st.write("**根拠法令:**")
    if result.law_articles:
        for art in result.law_articles:
            st.write(f"- {art}")
    else:
        st.write("（条文リンクなし）")

    st.write("**関連通知:**")
    for ntc in result.notifications:
        st.write(f"- {ntc}")

    st.write(f"**年代:** {', '.join(result.eras) if result.eras else '不明'}")

    st.write("**原文引用:**")
    for p in result.paragraphs[:5]:
        st.markdown(f"> {p['text'][:400]}")
    if len(result.paragraphs) > 5:
        st.caption(f"他 {len(result.paragraphs) - 5} 段落（省略）")

    with st.expander("巡回経路（トレーサビリティ）"):
        st.code(result.path_description, language=None)


# ---------------------------------------------------------------------------
# Tab 1: Equipment Search (graph traversal primary, FTS5 fallback)
# ---------------------------------------------------------------------------

with tab1:
    q = st.text_input("設備・通知・条文キーワード")
    if st.button("検索", key="search") and q:
        found = False

        # Primary: deterministic graph traversal
        if graph_engine is not None:
            results = graph_engine.search(q)
            if results:
                found = True
                st.success(f"グラフ巡回で {len(results)} 件の設備を検出しました。")
                for r in results:
                    _show_traversal_result(r)

        # Fallback: FTS5 text search (for keywords not in the graph)
        if not found:
            fts_results = fts_engine.search(q, k=10)
            if fts_results:
                st.info("グラフに該当ノードがないため、全文検索で結果を表示します。")
                for r in fts_results:
                    st.markdown("---")
                    st.write(f"### {r['title']}")
                    st.write(r["text"])
            else:
                st.info("該当する通知が見つかりませんでした。")


# ---------------------------------------------------------------------------
# Tab 2: Era Search (deterministic reverse traversal)
# ---------------------------------------------------------------------------

with tab2:
    era = st.selectbox("年代", ["昭和", "平成", "令和"])
    if st.button("年代で検索", key="era_search"):
        found = False

        if graph_engine is not None:
            results = graph_engine.search_by_era(era)
            if results:
                found = True
                st.success(f"「{era}」に関連する設備: {len(results)} 件")
                for r in results:
                    _show_traversal_result(r)

        if not found:
            # FTS5 fallback
            fts_results = fts_engine.search(era, k=50)
            fts_found = [r for r in fts_results if era in r.get("text", "")]
            if fts_found:
                st.info("グラフに該当ノードがないため、全文検索で結果を表示します。")
                for r in fts_found:
                    text_preview = r.get("text", "")[:80]
                    st.write(f"- {r['title']} | {text_preview}...")
            else:
                st.info(f"「{era}」を含む通知が見つかりませんでした。")


# ---------------------------------------------------------------------------
# Tab 3: Diff Search
# ---------------------------------------------------------------------------

with tab3:
    st.info("差分検索は law_diff テーブルを参照してください。run_pipeline.py 実行後に拡張可能です。")


# ---------------------------------------------------------------------------
# Tab 4: Inspection AI (graph-based standard listing)
# ---------------------------------------------------------------------------

with tab4:
    equipment_input = st.text_input("設備名（例: 地下タンク）", key="inspection")
    if st.button("必要基準を表示", key="inspection_button") and equipment_input:
        found = False

        # Primary: graph traversal
        if graph_engine is not None:
            result = graph_engine.search_by_equipment(equipment_input)
            if result:
                found = True
                st.write("### 必要基準一覧")
                for s in result.standards:
                    st.write(f"- {s}")

                st.write("### 関連法令")
                if result.law_articles:
                    for art in result.law_articles:
                        st.write(f"- {art}")
                else:
                    st.write("（条文リンクなし）")

                with st.expander("巡回経路"):
                    st.code(result.path_description, language=None)

        # Fallback: DB query
        if not found:
            standards = list_required_standards(DB_PATH, equipment_input)
            if standards:
                st.write("### 必要基準一覧")
                for s in standards:
                    st.write(f"- {s}")
            else:
                st.warning("該当設備の基準が見つかりませんでした。")

st.caption("AI設計原則: 推論禁止 / 解釈生成禁止 / 原文引用必須")
st.caption("検索方式: 決定論的グラフ巡回（非RAG）")
