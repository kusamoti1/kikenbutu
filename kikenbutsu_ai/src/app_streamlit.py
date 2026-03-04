from __future__ import annotations

from pathlib import Path

import streamlit as st

from inspection_ai import list_required_standards
from search_engine import SearchEngine

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "kikenbutsu.db"

st.set_page_config(page_title="危険物法令ナレッジグラフAI", layout="wide")
st.title("危険物法令ナレッジグラフAI")

if not DB_PATH.exists():
    st.warning("database/kikenbutsu.db が見つかりません。先に run_pipeline.py を実行してください。")
    st.stop()

engine = SearchEngine(DB_PATH)
engine.rebuild_index()

tab1, tab2, tab3, tab4 = st.tabs(["設備検索", "年代検索", "差分検索", "査察AI"])

with tab1:
    q = st.text_input("設備・通知・条文キーワード")
    if st.button("検索", key="search") and q:
        results = engine.search(q, k=10)
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
    era = st.selectbox("年代", ["昭和", "平成", "令和", "不明"])
    results = engine.search(era, k=10)
    for r in results:
        if era in r["text"]:
            st.write(f"- {r['title']} | {r['text'][:80]}...")

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
