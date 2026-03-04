from __future__ import annotations

import re
from typing import List

# Maximum length of a single paragraph before forced splitting.
_MAX_PARAGRAPH_CHARS = 2000


def split_paragraphs(text: str) -> List[str]:
    """Split notice text by blank lines.

    If the OCR output has no blank lines at all the text is split by
    common Japanese structural markers (「記」, numbered items, etc.)
    to avoid producing a single giant paragraph.
    """
    raw_parts = re.split(r"\n\s*\n+", text)
    paragraphs = [p.strip() for p in raw_parts if p.strip()]

    # If only one huge paragraph was produced, try splitting on
    # Japanese structural cues that often appear in notices.
    if len(paragraphs) == 1 and len(paragraphs[0]) > _MAX_PARAGRAPH_CHARS:
        secondary = re.split(r"\n(?=\d+\s|第[0-9一二三四五六七八九十]+\s|記\n|別[記紙])", paragraphs[0])
        secondary = [p.strip() for p in secondary if p.strip()]
        if len(secondary) > 1:
            paragraphs = secondary

    # Hard-split any remaining oversized paragraphs.
    result: List[str] = []
    for p in paragraphs:
        while len(p) > _MAX_PARAGRAPH_CHARS:
            # Try to split at the last newline within the limit.
            idx = p.rfind("\n", 0, _MAX_PARAGRAPH_CHARS)
            if idx == -1:
                idx = _MAX_PARAGRAPH_CHARS
            result.append(p[:idx].strip())
            p = p[idx:].strip()
        if p:
            result.append(p)

    return result
