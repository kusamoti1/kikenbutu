from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Minimum number of non-white pixels required for deskew to be meaningful.
_MIN_DESKEW_POINTS = 5


def _deskew(gray: np.ndarray) -> np.ndarray:
    coords = np.column_stack(np.where(gray < 255))
    if coords.shape[0] < _MIN_DESKEW_POINTS:
        # Not enough dark pixels to reliably detect rotation.
        return gray

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle

    # Skip rotation for negligible angles to avoid interpolation artefacts.
    if abs(angle) < 0.1:
        return gray

    (h, w) = gray.shape[:2]
    center = (w // 2, h // 2)
    m = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(gray, m, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def preprocess_image(image_path: Path, output_path: Path) -> Path:
    """Deskew, adjust contrast, and remove noise."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Failed to load image: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    deskewed = _deskew(gray)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    contrasted = clahe.apply(deskewed)
    denoised = cv2.fastNlMeansDenoising(contrasted, None, 14, 7, 21)

    cv2.imwrite(str(output_path), denoised)
    return output_path
