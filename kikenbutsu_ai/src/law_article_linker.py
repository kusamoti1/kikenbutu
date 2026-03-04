from __future__ import annotations

import re
from typing import List, Tuple

LAW_KEYWORDS = {
    "消防法": r"消防法\s*第?([0-9一二三四五六七八九十百]+条(?:の[0-9一二三四五六七八九十]+)?(?:\s*第[0-9一二三四五六七八九十]+項)?(?:\s*第?[0-9一二三四五六七八九十]+号)?)",
    "消防法施行令": r"(?:消防法)?施行令\s*第?([0-9一二三四五六七八九十百]+条(?:の[0-9一二三四五六七八九十]+)?(?:\s*第[0-9一二三四五六七八九十]+項)?(?:\s*第?[0-9一二三四五六七八九十]+号)?)",
    "消防法施行規則": r"(?:消防法)?施行規則\s*第?([0-9一二三四五六七八九十百]+条(?:の[0-9一二三四五六七八九十]+)?(?:\s*第[0-9一二三四五六七八九十]+項)?(?:\s*第?[0-9一二三四五六七八九十]+号)?)",
    "危険物の規制に関する政令": r"危険物の規制に関する政令\s*第?([0-9一二三四五六七八九十百]+条(?:の[0-9一二三四五六七八九十]+)?)",
    "危険物の規制に関する規則": r"危険物の規制に関する規則\s*第?([0-9一二三四五六七八九十百]+条(?:の[0-9一二三四五六七八九十]+)?)",
}


def extract_law_article_links(text: str) -> List[Tuple[str, str]]:
    links: List[Tuple[str, str]] = []
    seen = set()
    for law_name, pattern in LAW_KEYWORDS.items():
        for m in re.finditer(pattern, text):
            key = (law_name, m.group(1))
            if key not in seen:
                seen.add(key)
                links.append(key)
    return links
