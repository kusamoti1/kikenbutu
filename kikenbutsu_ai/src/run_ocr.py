from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from paddleocr import PaddleOCR


def ocr_image(image_path: Path, confidence_threshold: float = 0.85) -> List[Dict[str, object]]:
    """Run OCR and mark low-confidence lines as needs_review."""
    ocr = PaddleOCR(use_angle_cls=True, lang="japan")
    results = ocr.ocr(str(image_path), cls=True)

    rows: List[Dict[str, object]] = []
    if not results:
        return rows

    for line in results[0]:
        bbox, (text, conf) = line
        rows.append(
            {
                "text": text,
                "confidence": float(conf),
                "needs_review": float(conf) < confidence_threshold,
                "bbox": bbox,
            }
        )
    return rows
