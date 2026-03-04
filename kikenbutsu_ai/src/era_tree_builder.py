from __future__ import annotations

from typing import Dict

ERA_KEYWORDS = {
    "昭和": ["昭和"],
    "平成": ["平成"],
    "令和": ["令和"],
}


def detect_era(text: str) -> str:
    for era, keys in ERA_KEYWORDS.items():
        if any(k in text for k in keys):
            return era
    return "不明"


def build_era_counts(paragraphs: list[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for p in paragraphs:
        era = detect_era(p)
        counts[era] = counts.get(era, 0) + 1
    return counts
