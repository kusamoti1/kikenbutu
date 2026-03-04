from __future__ import annotations

from typing import Dict

OLD_TO_NEW: Dict[str, str] = {
    "舊": "旧",
    "體": "体",
    "變": "変",
}


def convert_old_kanji(text: str, mapping: Dict[str, str] | None = None) -> str:
    mapping = mapping or OLD_TO_NEW
    converted = text
    for old, new in mapping.items():
        converted = converted.replace(old, new)
    return converted
