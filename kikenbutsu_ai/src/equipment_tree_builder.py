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
    """Return all equipment names found in *text*, longest-match first.

    Shorter names that are substrings of an already-matched longer name
    at the *same position* are suppressed.  For example, if "給油取扱所"
    is found, the substring "取扱所" is not reported separately (unless
    it appears elsewhere in *text* outside the longer match).
    """
    found: list[str] = []
    seen: set[str] = set()
    # Track character positions already covered by longer matches.
    covered: set[int] = set()
    for name in _SORTED_EQUIPMENT:
        if name not in text or name in seen:
            continue
        # Check if every occurrence is covered by a longer match.
        start = 0
        has_independent = False
        while True:
            idx = text.find(name, start)
            if idx == -1:
                break
            positions = set(range(idx, idx + len(name)))
            if not positions.issubset(covered):
                has_independent = True
                covered.update(positions)
            start = idx + 1
        if has_independent:
            found.append(name)
            seen.add(name)
    return found
