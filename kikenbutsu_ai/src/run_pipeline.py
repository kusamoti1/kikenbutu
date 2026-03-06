from __future__ import annotations

import difflib
import sys
import json
import logging
from dataclasses import dataclass
from pathlib import Path

# `python src/run_pipeline.py` と `python run_pipeline.py` の両方で動くようにする
if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.config import load_config
from src.database_writer import (
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
    insert_search_index_metadata,
    link_document_equipment,
    record_export_metadata,
    upsert_fts,
)
from src.dictionary_corrector import apply_dictionary, load_dictionary
from src.contextual_chunk_builder import build_contextual_chunks
from src.equipment_classifier import classify_equipment
from src.knowledge_graph_builder import build_knowledge_graph, save_graphml
from src.law_article_linker import extract_law_article_links
from src.metadata_extractor import extract_metadata
from src.notebooklm_exporter import export_markdown_bundle
from src.old_kanji_converter import convert_old_kanji
from src.paragraph_splitter import split_paragraphs
from src.revision_diff_engine import summarize_diff
from src.revision_reason_engine import extract_revision_reasons
from src.utils import file_sha256


@dataclass
class ParaRow:
    id: int
    text: str
    section_label: str


@dataclass
class DocData:
    document_id: int
    title: str
    year: int
    era_label: str
    source: str
    document_type: str
    equipments: list[str]
    paragraphs: list[ParaRow]
    reasons: list[tuple[str, float]]


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


def _load_imported_text(cfg, pdf_path: Path) -> str:
    txt = cfg.ocr_dir / f"{pdf_path.stem}.txt"
    if txt.exists():
        return txt.read_text(encoding="utf-8")
    return ""


def _run_internal_ocr(cfg, pdf_path: Path) -> list[tuple[str, float]]:
    try:
        from src.pdf_to_image import pdf_to_images
        from src.image_preprocess import preprocess_image
        from src.run_ocr import ocr_image
    except Exception:
        logging.warning("OCRライブラリ未導入のため internal_ocr をスキップ: %s", pdf_path.name)
        return []

    dpi = cfg.ocr_dpi_scanned if any(k in pdf_path.stem for k in ["昭和", "scan", "スキャン"]) else cfg.ocr_dpi_default
    rows: list[tuple[str, float]] = []
    try:
        images = pdf_to_images(pdf_path, cfg.processed_dir / pdf_path.stem, dpi=dpi)
    except Exception:
        logging.exception("PDF画像化に失敗: %s", pdf_path.name)
        return rows

    for img in images:
        try:
            pre = cfg.processed_dir / pdf_path.stem / f"pre_{img.name}"
            preprocess_image(img, pre)
            ocr_rows = ocr_image(pre, confidence_threshold=cfg.ocr_confidence_threshold)
            for r in ocr_rows:
                t = str(r.get("text", "")).strip()
                c = float(r.get("confidence", 0.0))
                if t:
                    rows.append((t, c))
        except Exception:
            logging.exception("OCR実行失敗: %s", img.name)
            continue

    if rows:
        cfg.ocr_dir.mkdir(parents=True, exist_ok=True)
        (cfg.ocr_dir / f"{pdf_path.stem}.txt").write_text("\n".join(t for t, _ in rows), encoding="utf-8")
    return rows


def _estimate_paragraph_confidence(paragraphs: list[str], line_rows: list[tuple[str, float]]) -> list[tuple[float, float]]:
    if not line_rows:
        return [(0.0, 0.0) for _ in paragraphs]
    idx = 0
    used = 0
    confs: list[tuple[float, float]] = []
    for p in paragraphs:
        target = max(1, len(p))
        acc: list[float] = []
        while idx < len(line_rows) and used < target:
            line, c = line_rows[idx]
            acc.append(c)
            used += max(1, len(line))
            idx += 1
        if used >= target:
            used = 0
        if not acc:
            acc = [line_rows[min(idx, len(line_rows) - 1)][1]]
        confs.append((sum(acc) / len(acc), min(acc)))
    return confs


def _section_label(p: str) -> str:
    if p.startswith("附則"):
        return "附則"
    if p.startswith("別記") or p.startswith("別添"):
        return "別記"
    if p.startswith("第") and "条" in p[:16]:
        return "条文"
    return "本文"


def _topic_label(old_section: str, new_section: str, old_text: str, new_text: str) -> str:
    sec = old_section if old_section == new_section else "本文"
    if sec == "条文":
        return "条文比較候補"
    if sec == "附則":
        return "附則比較候補"
    if sec == "別記":
        return "設備別比較候補"
    if "基準" in old_text[:80] or "基準" in new_text[:80]:
        return "基準比較候補"
    return "本文比較候補"


def _insert_document_paragraphs(conn, cfg, pdf_path: Path, dictionary: dict[str, str]) -> DocData | None:
    imported = _load_imported_text(cfg, pdf_path)
    ocr_source = "imported_text"
    confidence_known = False
    line_rows: list[tuple[str, float]] = []

    if imported:
        text_original = imported
        logging.info("OCR入力: imported_text（信頼度不明） %s", pdf_path.name)
    else:
        line_rows = _run_internal_ocr(cfg, pdf_path)
        if not line_rows:
            logging.warning("OCR結果が得られずスキップ: %s", pdf_path.name)
            return None
        text_original = "\n".join(t for t, _ in line_rows)
        ocr_source = "internal_ocr"
        confidence_known = True
        logging.info("OCR入力: internal_ocr（信頼度あり） %s 行数=%d", pdf_path.name, len(line_rows))

    meta = extract_metadata(pdf_path, text_original)
    if meta.source == "不明":
        logging.info("出典判定が不明: %s", pdf_path.name)

    fhash = file_sha256(pdf_path)
    if document_exists(conn, fhash):
        logging.info("重複ファイルをスキップ: %s", pdf_path.name)
        return None

    normalized_text = convert_old_kanji(apply_dictionary(text_original, dictionary))
    correction_applied = normalized_text != text_original
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

    eq_hits = classify_equipment(normalized_text)
    for hit in eq_hits:
        eq_id = ensure_equipment(conn, hit.name, hit.name)
        link_document_equipment(conn, doc_id, eq_id, hit.confidence)

    if meta.era_label:
        ensure_era(conn, meta.era_label)

    raw_paras = split_paragraphs(text_original)
    norm_paras = split_paragraphs(normalized_text)
    count = min(len(raw_paras), len(norm_paras))
    raw_paras = raw_paras[:count]
    norm_paras = norm_paras[:count]

    conf_pairs = _estimate_paragraph_confidence(raw_paras, line_rows) if confidence_known else [(None, None)] * count
    para_rows: list[ParaRow] = []
    reasons = extract_revision_reasons(normalized_text)

    # NotebookLM/検索向けの文脈タグ（見出し・設備・年代・条文）を段落単位で付与
    doc_law_links = extract_law_article_links(normalized_text)
    chunks = build_contextual_chunks(
        paragraphs=norm_paras,
        doc_title=meta.title,
        equipment=[e.name for e in eq_hits] or ["共通法令"],
        eras=[meta.era_label] if meta.era_label else ["不明"],
        law_refs=[(l.law_name, l.article_number) for l in doc_law_links],
    )

    for i, (p_org, p_norm, chunk) in enumerate(zip(raw_paras, norm_paras, chunks), start=1):
        if len(p_norm.strip()) < cfg.min_paragraph_length:
            continue

        conf_avg, conf_min = conf_pairs[i - 1]
        if confidence_known:
            needs_review = (conf_min is not None and conf_min < cfg.ocr_confidence_threshold)
        else:
            # 信頼度不明は安全側で要確認
            needs_review = True

        section = _section_label(p_norm)
        links = extract_law_article_links(p_norm)
        eq_guess = eq_hits[0].name if eq_hits else "共通法令"

        p_id = insert_paragraph(
            conn=conn,
            document_id=doc_id,
            paragraph_index=i,
            section_label=section,
            text_original=p_org,
            text_normalized=p_norm,
            confidence_avg=conf_avg,
            confidence_min=conf_min,
            confidence_known=confidence_known,
            ocr_source=ocr_source,
            needs_review=needs_review,
            correction_applied=correction_applied,
            old_kanji_converted=old_kanji_converted,
            equipment_guess=eq_guess,
            ocr_applied=(ocr_source == "internal_ocr"),
            preprocess_notes=("画像前処理+PaddleOCR" if ocr_source == "internal_ocr" else "外部OCRテキスト取込"),
            context=chunk.context,
        )
        para_rows.append(ParaRow(p_id, p_norm, section))

        # chunks/ に文脈付き段落を保存し、検索メタへ登録
        cfg.chunks_dir.mkdir(parents=True, exist_ok=True)
        chunk_path = cfg.chunks_dir / f"doc{doc_id:06d}_p{i:05d}.txt"
        chunk_path.write_text(chunk.contextualized_text, encoding="utf-8")
        insert_search_index_metadata(
            conn,
            document_id=doc_id,
            paragraph_id=p_id,
            chunk_path=str(chunk_path),
            embedding_ready=False,
            fts_ready=True,
        )

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
                requirement_text=p_norm[:240],
                confidence=hit.confidence,
                needs_review=needs_review,
            )

    return DocData(
        document_id=doc_id,
        title=meta.title,
        year=meta.year or 0,
        era_label=meta.era_label or "不明",
        source=meta.source,
        document_type=meta.document_type,
        equipments=[e.name for e in eq_hits],
        paragraphs=para_rows,
        reasons=reasons,
    )


def _doc_pair_score(old_doc: DocData, new_doc: DocData) -> float:
    if old_doc.year and new_doc.year and old_doc.year >= new_doc.year:
        return -1.0
    eq_overlap = len(set(old_doc.equipments) & set(new_doc.equipments))
    if eq_overlap == 0:
        return -1.0

    title_sim = difflib.SequenceMatcher(None, old_doc.title, new_doc.title).ratio()
    year_gap = abs((new_doc.year or 0) - (old_doc.year or 0))
    year_score = max(0.0, 1.0 - (year_gap / 30.0)) if old_doc.year and new_doc.year else 0.3
    type_score = 1.0 if old_doc.document_type == new_doc.document_type else 0.6
    eq_score = min(1.0, eq_overlap / max(1, len(set(new_doc.equipments))))

    return 0.45 * title_sim + 0.25 * year_score + 0.2 * type_score + 0.1 * eq_score


def _best_para_pairs(old_doc: DocData, new_doc: DocData, top_n: int = 3) -> list[tuple[ParaRow, ParaRow, float]]:
    cands: list[tuple[ParaRow, ParaRow, float]] = []
    for op in old_doc.paragraphs:
        best_np = None
        best_s = -1.0
        for np in new_doc.paragraphs:
            sim = difflib.SequenceMatcher(None, op.text[:400], np.text[:400]).ratio()
            if op.section_label == np.section_label:
                sim += 0.08
            if sim > best_s:
                best_s = sim
                best_np = np
        if best_np and best_s >= 0.35:
            cands.append((op, best_np, best_s))

    cands.sort(key=lambda x: x[2], reverse=True)
    selected: list[tuple[ParaRow, ParaRow, float]] = []
    used_new: set[int] = set()
    for op, np, s in cands:
        if np.id in used_new:
            continue
        selected.append((op, np, s))
        used_new.add(np.id)
        if len(selected) >= top_n:
            break
    return selected


def _create_revisions(conn, docs_info: list[DocData]) -> int:
    count = 0
    if len(docs_info) < 2:
        return count

    pairs: list[tuple[DocData, DocData, float]] = []
    for old_doc in docs_info:
        for new_doc in docs_info:
            if old_doc.document_id == new_doc.document_id:
                continue
            score = _doc_pair_score(old_doc, new_doc)
            if score >= 0.45:
                pairs.append((old_doc, new_doc, score))

    pairs.sort(key=lambda x: x[2], reverse=True)
    used_doc_pair: set[tuple[int, int]] = set()

    for old_doc, new_doc, score in pairs:
        key = (old_doc.document_id, new_doc.document_id)
        if key in used_doc_pair:
            continue
        used_doc_pair.add(key)
        logging.info("差分候補ペア: %s -> %s score=%.3f", old_doc.title, new_doc.title, score)

        eq_common = list(set(old_doc.equipments) & set(new_doc.equipments))
        if not eq_common:
            continue
        eq_id = ensure_equipment(conn, eq_common[0], eq_common[0])

        para_pairs = _best_para_pairs(old_doc, new_doc, top_n=2)
        for op, np, ps in para_pairs:
            d = summarize_diff(op.text, np.text)
            topic = _topic_label(op.section_label, np.section_label, op.text, np.text)
            logging.info("段落ペア採用 old=%d new=%d sim=%.3f topic=%s", op.id, np.id, ps, topic)
            rev_id = insert_revision(
                conn,
                equipment_id=eq_id,
                topic_label=topic,
                old_document_id=old_doc.document_id,
                new_document_id=new_doc.document_id,
                old_paragraph_id=op.id,
                new_paragraph_id=np.id,
                diff_summary=d.diff_summary,
                old_text=d.old_text,
                new_text=d.new_text,
            )
            reasons = new_doc.reasons[:4]
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
    cfg.ocr_dir.mkdir(parents=True, exist_ok=True)

    conn = connect_db(cfg.db_path)
    docs_info: list[DocData] = []

    try:
        dictionary = load_dictionary(cfg.dict_path)
        pdf_files = sorted(cfg.input_dir.glob("*.pdf"))
        if not pdf_files:
            print("input_pdf にPDFがありません。先にPDFを配置してください。")

        for pdf in pdf_files:
            try:
                doc = _insert_document_paragraphs(conn, cfg, pdf, dictionary)
                if doc:
                    docs_info.append(doc)
            except Exception:
                logging.exception("文書処理失敗: %s", pdf.name)

        revision_count = _create_revisions(conn, docs_info)
        upsert_fts(conn)

        graph = build_knowledge_graph(conn)
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
