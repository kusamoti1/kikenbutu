from __future__ import annotations

from pathlib import Path

import streamlit as st

try:
    from .search_engine import SearchEngine
except ImportError:
    from search_engine import SearchEngine

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "kikenbutsu.db"
EXPORT_DIR = BASE_DIR / "notebooklm_export"
LOG_DIR = BASE_DIR / "logs"


st.set_page_config(page_title="危険物法令ナレッジAI", layout="wide")
st.title("危険物法令ナレッジAI（原文確認支援）")
st.caption("推論ではなく、原文提示・差分提示・信頼度表示を優先します。")

if not DB_PATH.exists():
    st.error("database/kikenbutsu.db が見つかりません。先に `python src/run_pipeline.py` を実行してください。")
    st.stop()

engine = SearchEngine(DB_PATH)


def conf_badge(conf: float | None, known: int, needs_review: int) -> str:
    if not known:
        return "信頼度不明 / 原本確認推奨"
    if needs_review:
        return f"OCR低信頼 ({conf:.2f}) / 原本確認推奨" if conf is not None else "OCR低信頼 / 原本確認推奨"
    return f"高信頼 ({conf:.2f})" if conf is not None else "高信頼"


tabs = st.tabs(["設備検索", "年代検索", "条文検索", "差分検索", "査察支援", "NotebookLM出力確認", "ログ確認"])

with tabs[0]:
    eq = st.text_input("設備名（例: 地下タンク貯蔵所）")
    if eq:
        rows = engine.search_by_equipment(eq)
        for title, era, text, conf, review, known, ocr_source in rows:
            st.markdown(f"**通知名**: {title} / **年代**: {era} / **OCRソース**: {ocr_source}")
            st.markdown(f"**信頼度状態**: {conf_badge(conf, known, review)}")
            st.code((text or "")[:600])

with tabs[1]:
    era = st.selectbox("年代", ["昭和", "平成", "令和", "不明"])
    q = st.text_input("年代内キーワード（任意）")
    if st.button("年代検索"):
        rows = engine.search_by_era(era, q, 120)
        st.write(f"検索件数: {len(rows)}")
        for r in rows:
            st.write(f"通知名: {r[1]} / 年代: {r[2]} / 設備: {r[3]} / 信頼度状態: {conf_badge(r[5], r[7], r[6])}")
            st.code((r[4] or "")[:500])

with tabs[2]:
    q = st.text_input("条文検索（例: 第10条、規則第12条）")
    if q:
        rows = engine.search_fts(q, 60)
        for r in rows:
            st.write(f"通知名: {r[1]} / 年代: {r[2]} / 設備: {r[3]} / 信頼度状態: {conf_badge(r[5], r[7], r[6])}")
            st.code((r[4] or "")[:500])

with tabs[3]:
    eq = st.text_input("差分検索設備（空欄なら全設備）")
    for name, topic, diff, old_t, new_t, old_title, new_title in engine.search_revisions(eq or None):
        st.markdown(f"### {name} / {topic}")
        st.write(f"比較元: {old_title} → 比較先: {new_title}")
        st.write(f"差分要約: {diff}")
        with st.expander("旧基準（比較元）"):
            st.code((old_t or "")[:1200])
        with st.expander("新基準（比較先）"):
            st.code((new_t or "")[:1200])

with tabs[4]:
    eq = st.text_input("査察支援の設備名")
    if eq:
        reqs, laws = engine.inspection_bundle(eq)
        st.markdown("#### 必要基準候補一覧")
        for label, text, conf, review in reqs:
            st.write(f"- {label}: 信頼度 {conf:.2f} / {'要人手確認' if review else '参考候補'}")
            st.code((text or "")[:300])
        st.markdown("#### 関係条文一覧")
        for law, art, para, item, text, known, conf, review in laws:
            st.write(f"- {law} {art} {'第'+para+'項' if para else ''} {'第'+item+'号' if item else ''} / {conf_badge(conf, known, review)}")
            st.caption((text or "")[:220])

with tabs[5]:
    st.write("NotebookLM向け出力ファイル")
    for p in sorted(EXPORT_DIR.glob("*.md")):
        st.write(f"- {p.name}")

with tabs[6]:
    for p in sorted(LOG_DIR.glob("*.log")):
        st.write(f"- {p.name}")
        if st.checkbox(f"表示: {p.name}"):
            st.code(p.read_text(encoding="utf-8")[-3000:])
