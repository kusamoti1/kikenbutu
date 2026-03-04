from __future__ import annotations

import re
from typing import List

# Patterns that detect a revision-reason heading.  The content may span
# multiple lines until the next heading or a double-newline.
REASON_PATTERNS = [
    r"改正理由[：:]\s*((?:.|\n)+?)(?=\n\n|\n[一二三四五六七八九十\d]+[.、]|\Z)",
    r"趣旨[：:]\s*((?:.|\n)+?)(?=\n\n|\n[一二三四五六七八九十\d]+[.、]|\Z)",
    r"背景[：:]\s*((?:.|\n)+?)(?=\n\n|\n[一二三四五六七八九十\d]+[.、]|\Z)",
]


def extract_revision_reasons(text: str) -> List[str]:
    reasons: List[str] = []
    for pattern in REASON_PATTERNS:
        for m in re.finditer(pattern, text):
            reason = m.group(1).strip()
            if reason and reason not in reasons:
                reasons.append(reason)
    return reasons
