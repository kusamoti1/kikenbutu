from __future__ import annotations

import re

KEYWORDS = [
    "改正の趣旨",
    "見直しの理由",
    "技術上の基準の整備",
    "安全対策の強化",
    "運用の明確化",
    "改正理由",
    "背景",
]


def extract_revision_reasons(text: str) -> list[tuple[str, float]]:
    candidates: list[tuple[str, float]] = []
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for i, ln in enumerate(lines):
        for kw in KEYWORDS:
            if kw in ln:
                snippet = " ".join(lines[i:i + 3])[:240]
                score = 0.9 if ln.startswith(kw) or "：" in ln else 0.75
                candidates.append((snippet, score))
                break

    # パターン抽出
    for m in re.finditer(r"(改正(?:の)?趣旨[：:].{0,200})", text):
        candidates.append((m.group(1).strip(), 0.85))

    uniq: list[tuple[str, float]] = []
    seen: set[str] = set()
    for txt, conf in candidates:
        if txt not in seen:
            seen.add(txt)
            uniq.append((txt, conf))
    return uniq
