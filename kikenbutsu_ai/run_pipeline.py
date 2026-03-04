from __future__ import annotations

import json
import logging
from pathlib import Path

from src.contextual_chunk_builder import build_contextual_chunks
from src.database_writer import (
    connect_db,
    document_exists,
    ensure_equipment,
    ensure_standard,
    insert_contextual_paragraphs,
    insert_document,
    insert_law_article_links,
)
from src.dictionary_corrector import apply_dictionary, load_dictionary
from src.equipment_tree_builder import detect_equipment
from src.era_tree_builder import detect_eras
from src.knowledge_graph_builder import build_knowledge_graph, save_graphml
from src.law_article_linker import extract_law_article_links
from src.notebooklm_exporter import export_markdown_by_equipment
from src.old_kanji_converter import convert_old_kanji
from src.paragraph_splitter import split_paragraphs

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input_pdf"
OCR_DIR = BASE_DIR / "ocr_text"
PROCESSED_DIR = BASE_DIR / "processed_images"
DB_PATH = BASE_DIR / "database" / "kikenbutsu.db"
DICT_PATH = BASE_DIR / "dictionary" / "ocr_dictionary.tsv"
LOG_PATH = BASE_DIR / "logs" / "pipeline.log"

_logger_configured = False


def setup_logger() -> None:
    """Configure logging once.  Safe to call multiple times."""
    global _logger_configured
    if _logger_configured:
        return
    _logger_configured = True

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=str(LOG_PATH),
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
    )
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(console)


def load_ocr_text(file_stem: str) -> str:
    txt_path = OCR_DIR / f"{file_stem}.txt"
    if txt_path.exists():
        return txt_path.read_text(encoding="utf-8")
    return ""


def try_ocr_pipeline(pdf_path: Path) -> str:
    """Attempt to run the full OCR pipeline for a PDF.

    Returns OCR text or empty string if OCR libraries are not available.
    """
    try:
        from src.image_preprocess import preprocess_image
        from src.pdf_to_image import pdf_to_images
        from src.run_ocr import ocr_image
    except ImportError:
        logging.warning("OCR libraries not available. Skipping OCR for %s", pdf_path.name)
        return ""

    try:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        images = pdf_to_images(pdf_path, PROCESSED_DIR)
        all_text: list[str] = []

        for img_path in images:
            preprocessed = PROCESSED_DIR / f"pre_{img_path.name}"
            preprocess_image(img_path, preprocessed)
            ocr_rows = ocr_image(preprocessed)
            page_lines = [row["text"] for row in ocr_rows]
            all_text.append("\n".join(page_lines))

        text = "\n\n".join(all_text)

        OCR_DIR.mkdir(parents=True, exist_ok=True)
        (OCR_DIR / f"{pdf_path.stem}.txt").write_text(text, encoding="utf-8")

        return text
    except Exception as exc:
        logging.exception("OCR pipeline failed for %s: %s", pdf_path.name, exc)
        return ""


def main() -> None:
    setup_logger()

    # Ensure the input directory exists (avoid FileNotFoundError from glob).
    INPUT_DIR.mkdir(parents=True, exist_ok=True)

    conn = connect_db(DB_PATH)
    try:
        dictionary = load_dictionary(DICT_PATH)
        graph_records: list[dict] = []

        pdf_files = sorted(INPUT_DIR.glob("*.pdf"))
        if not pdf_files:
            logging.warning("No PDFs found under input_pdf/. Pipeline completed with no documents.")
            print("WARNING: input_pdf/ にPDFがありません。PDFを配置してから再実行してください。")

        for pdf_path in pdf_files:
            try:
                source = "消防法令資料"
                title = pdf_path.stem
                year = None
                file_path_str = str(pdf_path)

                if document_exists(conn, title, file_path_str):
                    logging.info("Skipping duplicate: %s", pdf_path.name)
                    continue

                document_id = insert_document(conn, title=title, year=year, source=source, file_path=file_path_str)

                text = load_ocr_text(pdf_path.stem)
                if not text:
                    text = try_ocr_pipeline(pdf_path)
                if not text:
                    logging.warning("No OCR text available for %s. Skipping.", pdf_path.name)
                    continue

                text = convert_old_kanji(apply_dictionary(text, dictionary))
                paragraphs = split_paragraphs(text)

                equipment_names = list(set(detect_equipment(text)))
                law_links = extract_law_article_links(text)
                eras = detect_eras(text)

                # Build context-enriched chunks (Contextual Retrieval).
                chunks = build_contextual_chunks(
                    paragraphs=paragraphs,
                    doc_title=title,
                    equipment=equipment_names if equipment_names else ["共通法令"],
                    eras=eras,
                    law_refs=law_links,
                )

                insert_contextual_paragraphs(
                    conn, document_id,
                    [(c.text, c.context, 1.0) for c in chunks],
                )

                for equipment in equipment_names or ["共通法令"]:
                    eq_id = ensure_equipment(conn, equipment)
                    std_id = ensure_standard(conn, eq_id, title)
                    if law_links:
                        insert_law_article_links(conn, std_id, law_links)

                    for era in eras:
                        graph_records.append(
                            {
                                "equipment": equipment,
                                "standard": title,
                                "notification": title,
                                "article": ", ".join([f"{n} {a}" for n, a in law_links]) or "条文リンクなし",
                                "era": era,
                            }
                        )

                logging.info("Processed %s (%d chunks, contextual)", pdf_path.name, len(chunks))
            except Exception as exc:
                logging.exception("Failed to process %s: %s", pdf_path.name, exc)
                continue
    finally:
        conn.close()

    graph = build_knowledge_graph(graph_records)
    graphml_path = BASE_DIR / "database" / "knowledge_graph.graphml"
    save_graphml(graph, graphml_path)

    # Pass the graph to the exporter so it can use deterministic
    # traversal for content collection and traceability logging.
    export_markdown_by_equipment(DB_PATH, BASE_DIR / "notebooklm_export", graph=graph)

    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    (log_dir / "graph_records.json").write_text(
        json.dumps(graph_records, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    logging.info("Pipeline completed. %d records processed.", len(graph_records))
    print(f"Pipeline completed. {len(graph_records)} records processed.")


if __name__ == "__main__":
    main()
