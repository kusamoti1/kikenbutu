from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    base_dir: Path
    input_dir: Path
    processed_dir: Path
    ocr_dir: Path
    chunks_dir: Path
    db_path: Path
    dict_path: Path
    logs_dir: Path
    notebooklm_export_dir: Path
    ocr_dpi_default: int = 300
    ocr_dpi_scanned: int = 400
    ocr_confidence_threshold: float = 0.85
    min_paragraph_length: int = 20
    max_export_mb: int = 10


EQUIPMENT_CANONICAL = [
    "屋外タンク貯蔵所",
    "地下タンク貯蔵所",
    "移動タンク貯蔵所",
    "給油取扱所",
    "一般取扱所",
    "製造所",
    "屋内貯蔵所",
    "屋外貯蔵所",
    "販売取扱所",
    "共通法令",
]


def load_config(base_dir: Path) -> AppConfig:
    return AppConfig(
        base_dir=base_dir,
        input_dir=base_dir / "input_pdf",
        processed_dir=base_dir / "processed_images",
        ocr_dir=base_dir / "ocr_text",
        chunks_dir=base_dir / "chunks",
        db_path=base_dir / "database" / "kikenbutsu.db",
        dict_path=base_dir / "dictionary" / "ocr_dictionary.tsv",
        logs_dir=base_dir / "logs",
        notebooklm_export_dir=base_dir / "notebooklm_export",
    )
