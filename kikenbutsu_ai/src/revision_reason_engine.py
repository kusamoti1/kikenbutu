from __future__ import annotations

import re
from typing import List

REASON_PATTERNS = [r"改正理由[：:](.+)", r"趣旨[：:](.+)", r"背景[：:](.+)"]


def extract_revision_reasons(text: str) -> List[str]:
    reasons: List[str] = []
    for pattern in REASON_PATTERNS:
        for m in re.finditer(pattern, text):
            reasons.append(m.group(1).strip())
    return reasons
