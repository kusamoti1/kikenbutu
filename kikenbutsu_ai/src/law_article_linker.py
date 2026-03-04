from __future__ import annotations

import re
from typing import List, Tuple

LAW_KEYWORDS = {
    "消防法": r"消防法\s*第?([0-9一二三四五六七八九十百]+条)",
    "消防法施行令": r"施行令\s*第?([0-9一二三四五六七八九十百]+条)",
    "消防法施行規則": r"施行規則\s*第?([0-9一二三四五六七八九十百]+条)",
}


def extract_law_article_links(text: str) -> List[Tuple[str, str]]:
    links: List[Tuple[str, str]] = []
    for law_name, pattern in LAW_KEYWORDS.items():
        for m in re.finditer(pattern, text):
            links.append((law_name, m.group(1)))
    return links
