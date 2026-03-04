from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

from paddleocr import PaddleOCR

logger = logging.getLogger(__name__)

_ocr_instance: Optional[PaddleOCR] = None


def _get_ocr() -> PaddleOCR:
    """Return a shared PaddleOCR instance to avoid repeated model loading."""
    global _ocr_instance
    if _ocr_instance is None:
        _ocr_instance = PaddleOCR(use_angle_cls=True, lang="japan")
    return _ocr_instance


def ocr_image(image_path: Path, confidence_threshold: float = 0.85) -> List[Dict[str, object]]:
    """Run OCR and mark low-confidence lines as needs_review."""
    ocr = _get_ocr()
    results = ocr.ocr(str(image_path), cls=True)

    rows: List[Dict[str, object]] = []
    if not results:
        return rows

    for page in results:
        if not page:
            continue
        for line in page:
            try:
                bbox, (text, conf) = line
            except (TypeError, ValueError) as exc:
                logger.warning("Unexpected OCR line format in %s: %s – %s", image_path.name, line, exc)
                continue
            rows.append(
                {
                    "text": text,
                    "confidence": float(conf),
                    "needs_review": float(conf) < confidence_threshold,
                    "bbox": bbox,
                }
            )
    return rows
