from __future__ import annotations

# Full list of hazardous material facility types from the specification.
EQUIPMENT_LIST = [
    "製造所",
    "貯蔵所",
    "取扱所",
    "屋外タンク貯蔵所",
    "屋外タンク",
    "屋内タンク貯蔵所",
    "屋内タンク",
    "地下タンク貯蔵所",
    "地下タンク",
    "移動タンク貯蔵所",
    "移動タンク",
    "給油取扱所",
    "一般取扱所",
]

# Longer names checked first so that "屋外タンク貯蔵所" is preferred
# over "屋外タンク" when both would match.
_SORTED_EQUIPMENT = sorted(EQUIPMENT_LIST, key=len, reverse=True)


def detect_equipment(text: str) -> list[str]:
    """Return all equipment names found in *text*, longest-match first."""
    found: list[str] = []
    seen: set[str] = set()
    for name in _SORTED_EQUIPMENT:
        if name in text and name not in seen:
            found.append(name)
            seen.add(name)
    return found
