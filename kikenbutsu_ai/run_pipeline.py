from __future__ import annotations

import json
import logging
from pathlib import Path

from src.database_writer import connect_db, insert_document, insert_paragraphs
from src.dictionary_corrector import apply_dictionary, load_dictionary
from src.equipment_tree_builder import detect_equipment
from src.knowledge_graph_builder import build_knowledge_graph, save_graphml
from src.law_article_linker import extract_law_article_links
from src.notebooklm_exporter import export_markdown_by_equipment
from src.old_kanji_converter import convert_old_kanji
from src.paragraph_splitter import split_paragraphs

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input_pdf"
OCR_DIR = BASE_DIR / "ocr_text"
DB_PATH = BASE_DIR / "database" / "kikenbutsu.db"
DICT_PATH = BASE_DIR / "dictionary" / "ocr_dictionary.tsv"
LOG_PATH = BASE_DIR / "logs" / "pipeline.log"


def setup_logger() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
    )


def load_ocr_text(file_stem: str) -> str:
    txt_path = OCR_DIR / f"{file_stem}.txt"
    if txt_path.exists():
        return txt_path.read_text(encoding="utf-8")
    return ""


def main() -> None:
    setup_logger()
    conn = connect_db(DB_PATH)
    dictionary = load_dictionary(DICT_PATH)

    graph_records = []

    pdf_files = sorted(INPUT_DIR.glob("*.pdf"))
    if not pdf_files:
        logging.warning("No PDFs found under input_pdf. Pipeline completed with no documents.")

    for pdf_path in pdf_files:
        try:
            source = "消防法令資料"
            title = pdf_path.stem
            year = None

            document_id = insert_document(conn, title=title, year=year, source=source, file_path=str(pdf_path))

            text = load_ocr_text(pdf_path.stem)
            text = convert_old_kanji(apply_dictionary(text, dictionary))
            paragraphs = split_paragraphs(text)

            insert_paragraphs(conn, document_id, [(p, 1.0) for p in paragraphs])

            equipment_names = set(detect_equipment(text))
            law_links = extract_law_article_links(text)
            for equipment in equipment_names or {"共通法令"}:
                graph_records.append(
                    {
                        "equipment": equipment,
                        "standard": title,
                        "notification": title,
                        "article": ", ".join([f"{n} {a}" for n, a in law_links]) or "条文リンクなし",
                        "era": "不明年代",
                    }
                )

            logging.info("Processed %s", pdf_path.name)
        except Exception as exc:
            logging.exception("Failed to process %s: %s", pdf_path.name, exc)
            continue

    conn.close()

    graph = build_knowledge_graph(graph_records)
    save_graphml(graph, BASE_DIR / "database" / "knowledge_graph.graphml")
    export_markdown_by_equipment(DB_PATH, BASE_DIR / "notebooklm_export")

    (BASE_DIR / "logs" / "graph_records.json").write_text(
        json.dumps(graph_records, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
