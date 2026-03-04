from __future__ import annotations

EQUIPMENT_LIST = [
    "屋外タンク",
    "地下タンク",
    "移動タンク",
    "給油取扱所",
    "一般取扱所",
    "製造所",
]


def detect_equipment(text: str) -> list[str]:
    return [name for name in EQUIPMENT_LIST if name in text]
