from __future__ import annotations

from pathlib import Path
from typing import Dict


def load_dictionary(dictionary_path: Path) -> Dict[str, str]:
    """Load TSV dictionary: wrong<TAB>correct."""
    mapping: Dict[str, str] = {}
    if not dictionary_path.exists():
        return mapping

    for raw in dictionary_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" not in line:
            continue
        wrong, correct = line.split("\t", 1)
        mapping[wrong] = correct
    return mapping


def apply_dictionary(text: str, mapping: Dict[str, str]) -> str:
    corrected = text
    for wrong, right in mapping.items():
        corrected = corrected.replace(wrong, right)
    return corrected
