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

from inspection_ai import list_required_standards
from search_engine import SearchEngine

BASE_DIR = _PROJECT_DIR
DB_PATH = BASE_DIR / "database" / "kikenbutsu.db"

st.set_page_config(page_title="危険物法令ナレッジグラフAI", layout="centered")
st.title("危険物法令ナレッジグラフAI")

if not DB_PATH.exists():
    st.warning("database/kikenbutsu.db が見つかりません。先に run_pipeline.py を実行してください。")
    st.stop()


@st.cache_resource
def get_engine() -> SearchEngine:
    engine = SearchEngine(DB_PATH)
    engine.rebuild_index()
    return engine


engine = get_engine()

tab1, tab2, tab3, tab4 = st.tabs(["設備検索", "年代検索", "差分検索", "査察AI"])

with tab1:
    q = st.text_input("設備・通知・条文キーワード")
    if st.button("検索", key="search") and q:
        results = engine.search(q, k=10)
        if not results:
            st.info("該当する通知が見つかりませんでした。")
        for r in results:
            st.markdown("---")
            st.write("### 結論")
            st.write(r["title"])
            st.write("### 根拠法令")
            st.write("消防法関連資料（要原文確認）")
            st.write("### 通知")
            st.write(r["title"])
            st.write("### 原文")
            st.write(r["text"])

with tab2:
    era = st.selectbox("年代", ["昭和", "平成", "令和"])
    if st.button("年代で検索", key="era_search"):
        results = engine.search(era, k=50)
        found = [r for r in results if era in r.get("text", "")]
        if not found:
            st.info(f"「{era}」を含む通知が見つかりませんでした。")
        for r in found:
            text_preview = r.get("text", "")[:80]
            st.write(f"- {r['title']} | {text_preview}...")

with tab3:
    st.info("差分検索は law_diff テーブルを参照してください。run_pipeline.py 実行後に拡張可能です。")

with tab4:
    equipment = st.text_input("設備名（例: 地下タンク）", key="inspection")
    if st.button("必要基準を表示", key="inspection_button") and equipment:
        standards = list_required_standards(DB_PATH, equipment)
        if not standards:
            st.warning("該当設備の基準が見つかりませんでした。")
        else:
            st.write("### 必要基準一覧")
            for s in standards:
                st.write(f"- {s}")

st.caption("AI設計原則: 推論禁止 / 解釈生成禁止 / 原文引用必須")
