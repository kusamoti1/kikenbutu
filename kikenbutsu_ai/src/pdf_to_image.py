from __future__ import annotations

from pathlib import Path
from typing import List

from pdf2image import convert_from_path


def pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int = 400) -> List[Path]:
    """Convert one PDF into PNG images."""
    output_dir.mkdir(parents=True, exist_ok=True)
    images = convert_from_path(str(pdf_path), dpi=dpi)
    output_paths: List[Path] = []

    for idx, image in enumerate(images, start=1):
        out = output_dir / f"{pdf_path.stem}_p{idx:04d}.png"
        image.save(out, "PNG")
        output_paths.append(out)

    return output_paths
