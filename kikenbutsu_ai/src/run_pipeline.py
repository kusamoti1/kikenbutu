from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from config import load_config
from database_writer import (
    connect_db,
    document_exists,
    ensure_equipment,
    ensure_era,
    insert_document,
    insert_law_article_links,
    insert_legal_requirement,
    insert_paragraph,
    insert_revision,
    insert_revision_reasons,
    link_document_equipment,
    record_export_metadata,
    upsert_fts,
)
from dictionary_corrector import apply_dictionary, load_dictionary
from equipment_classifier import classify_equipment
from knowledge_graph_builder import build_knowledge_graph, save_graphml
from law_article_linker import extract_law_article_links
from metadata_extractor import extract_metadata
from notebooklm_exporter import export_markdown_bundle
from old_kanji_converter import convert_old_kanji
from paragraph_splitter import split_paragraphs
from revision_diff_engine import summarize_diff
from revision_reason_engine import extract_revision_reasons
from utils import file_sha256


@dataclass
class ParaRow:
    id: int
    text: str


def setup_logger(log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        filename=str(log_path),
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
    )
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(h)


def _load_orc_text(cfg, pdf_path: Path) -> str:
    txt = cfg.ocr_dir / f"{pdf_path.stem}.txt"
    if txt.exists():
        return txt.read_text(encoding="utf-8")
    return ""


def _insert_document_paragraphs(conn, cfg, pdf_path: Path, dictionary: dict[str, str]):
    text_original = _load_orc_text(cfg, pdf_path)
    if not text_original:
        logging.warning("OCRテキストが見つからないためスキップ: %s", pdf_path.name)
        return None

    meta = extract_metadata(pdf_path, text_original)
    fhash = file_sha256(pdf_path)
    if document_exists(conn, fhash):
        logging.info("重複ファイルをスキップ: %s", pdf_path.name)
        return None

    normalized = convert_old_kanji(apply_dictionary(text_original, dictionary))
    correction_applied = normalized != text_original
    old_kanji_converted = convert_old_kanji(text_original) != text_original

    doc_id = insert_document(
        conn=conn,
        title=meta.title,
        year=meta.year,
        era_label=meta.era_label,
        source=meta.source,
        document_type=meta.document_type,
        file_path=str(pdf_path),
        file_hash=fhash,
    )

    eq_hits = classify_equipment(normalized)
    for hit in eq_hits:
        eq_id = ensure_equipment(conn, hit.name, hit.name)
        link_document_equipment(conn, doc_id, eq_id, hit.confidence)

    if meta.era_label:
        ensure_era(conn, meta.era_label)

    paras = split_paragraphs(normalized)
    para_rows: list[ParaRow] = []
    reasons = extract_revision_reasons(normalized)

    for i, p in enumerate(paras, start=1):
        if len(p.strip()) < cfg.min_paragraph_length:
            continue
        confidence = 1.0
        needs_review = confidence < cfg.ocr_confidence_threshold
        section = "本文"
        if p.startswith("第") and "条" in p[:12]:
            section = "条文"
        elif p.startswith("附則"):
            section = "附則"

        links = extract_law_article_links(p)
        eq_guess = eq_hits[0].name if eq_hits else "共通法令"
        p_id = insert_paragraph(
            conn=conn,
            document_id=doc_id,
            paragraph_index=i,
            section_label=section,
            text_original=p,
            text_normalized=p,
            confidence_avg=confidence,
            confidence_min=confidence,
            needs_review=needs_review,
            correction_applied=correction_applied,
            old_kanji_converted=old_kanji_converted,
            equipment_guess=eq_guess,
            ocr_applied=True,
            preprocess_notes="ocr_text入力から取り込み",
            context=f"設備:{eq_guess} / 年代:{meta.era_label or '不明'} / 文書:{meta.title}",
        )
        para_rows.append(ParaRow(p_id, p))

        if links:
            insert_law_article_links(
                conn,
                p_id,
                [(l.law_name, l.article_number, l.paragraph_number, l.item_number, l.confidence) for l in links],
            )
        for hit in eq_hits[:2]:
            eq_id = ensure_equipment(conn, hit.name, hit.name)
            insert_legal_requirement(
                conn,
                doc_id,
                p_id,
                eq_id,
                requirement_label="基準候補",
                requirement_text=p[:240],
                confidence=hit.confidence,
                needs_review=needs_review,
            )

    return {
        "document_id": doc_id,
        "title": meta.title,
        "year": meta.year or 0,
        "equipments": [e.name for e in eq_hits],
        "paragraphs": para_rows,
        "reasons": reasons,
    }


def _create_revisions(conn, docs_info: list[dict]) -> int:
    count = 0
    docs_sorted = sorted(docs_info, key=lambda d: d.get("year", 0))
    for i in range(len(docs_sorted) - 1):
        old_doc = docs_sorted[i]
        new_doc = docs_sorted[i + 1]
        if not set(old_doc["equipments"]) & set(new_doc["equipments"]):
            continue
        if not old_doc["paragraphs"] or not new_doc["paragraphs"]:
            continue

        old_p = old_doc["paragraphs"][0]
        new_p = new_doc["paragraphs"][0]
        d = summarize_diff(old_p.text, new_p.text)
        eq = list(set(old_doc["equipments"]) & set(new_doc["equipments"]))[0]
        eq_id = ensure_equipment(conn, eq, eq)
        rev_id = insert_revision(
            conn,
            equipment_id=eq_id,
            topic_label="自動比較",
            old_document_id=old_doc["document_id"],
            new_document_id=new_doc["document_id"],
            old_paragraph_id=old_p.id,
            new_paragraph_id=new_p.id,
            diff_summary=d.diff_summary,
            old_text=d.old_text,
            new_text=d.new_text,
        )
        reasons = new_doc.get("reasons", [])[:4]
        if reasons:
            insert_revision_reasons(conn, rev_id, reasons)
        count += 1
    return count


def main() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    cfg = load_config(base_dir)
    setup_logger(cfg.logs_dir / "pipeline.log")

    cfg.input_dir.mkdir(parents=True, exist_ok=True)
    cfg.notebooklm_export_dir.mkdir(parents=True, exist_ok=True)

    conn = connect_db(cfg.db_path)
    docs_info: list[dict] = []
    graph_records: list[dict] = []

    try:
        dictionary = load_dictionary(cfg.dict_path)
        pdf_files = sorted(cfg.input_dir.glob("*.pdf"))
        if not pdf_files:
            print("input_pdf にPDFがありません。先にPDFを配置してください。")

        for pdf in pdf_files:
            try:
                doc = _insert_document_paragraphs(conn, cfg, pdf, dictionary)
                if not doc:
                    continue
                docs_info.append(doc)
                for eq in doc["equipments"] or ["共通法令"]:
                    graph_records.append({
                        "equipment": eq,
                        "standard": doc["title"],
                        "notification": doc["title"],
                        "article": "条文候補",
                        "era": "不明",
                    })
            except Exception:
                logging.exception("文書処理失敗: %s", pdf.name)

        revision_count = _create_revisions(conn, docs_info)
        upsert_fts(conn)

        graph = build_knowledge_graph(graph_records)
        save_graphml(graph, cfg.base_dir / "database" / "knowledge_graph.graphml")

        exports = export_markdown_bundle(conn, cfg.notebooklm_export_dir)
        for e in exports:
            record_export_metadata(conn, e[0], e[1], str(e[2]))

        (cfg.logs_dir / "pipeline_summary.json").write_text(
            json.dumps(
                {
                    "documents": len(docs_info),
                    "revisions": revision_count,
                    "exports": len(exports),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        print(f"処理完了: 文書{len(docs_info)}件 / 差分{revision_count}件 / 出力{len(exports)}件")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
