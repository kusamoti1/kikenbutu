from __future__ import annotations

import re
from typing import List


def split_paragraphs(text: str) -> List[str]:
    """Split notice text by blank lines / Japanese indentation-like breaks."""
    raw_parts = re.split(r"\n\s*\n+", text)
    paragraphs = [p.strip() for p in raw_parts if p.strip()]
    return paragraphs
