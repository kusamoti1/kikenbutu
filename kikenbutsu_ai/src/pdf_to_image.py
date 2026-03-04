from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from pdf2image import convert_from_path

logger = logging.getLogger(__name__)

# Maximum number of pages to convert in one batch to limit memory usage.
_BATCH_SIZE = 10


def pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int = 400) -> List[Path]:
    """Convert one PDF into PNG images (batch-processed to limit memory)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_paths: List[Path] = []

    # Determine total page count first (lightweight – no rendering).
    try:
        from pdf2image import pdfinfo_from_path
        info = pdfinfo_from_path(str(pdf_path))
        total_pages = info.get("Pages", 0)
    except Exception:
        # If pdfinfo is not available, fall back to converting all at once.
        total_pages = 0

    if total_pages > _BATCH_SIZE:
        # Convert in batches to avoid loading all pages into memory.
        for start in range(1, total_pages + 1, _BATCH_SIZE):
            end = min(start + _BATCH_SIZE - 1, total_pages)
            try:
                images = convert_from_path(
                    str(pdf_path), dpi=dpi, first_page=start, last_page=end,
                )
            except Exception as exc:
                logger.error("Failed to convert pages %d-%d of %s: %s", start, end, pdf_path.name, exc)
                continue
            for page_offset, image in enumerate(images):
                page_num = start + page_offset
                out = output_dir / f"{pdf_path.stem}_p{page_num:04d}.png"
                image.save(out, "PNG")
                output_paths.append(out)
    else:
        try:
            images = convert_from_path(str(pdf_path), dpi=dpi)
        except Exception as exc:
            logger.error("Failed to convert %s: %s", pdf_path.name, exc)
            return output_paths
        for idx, image in enumerate(images, start=1):
            out = output_dir / f"{pdf_path.stem}_p{idx:04d}.png"
            image.save(out, "PNG")
            output_paths.append(out)

    return output_paths
