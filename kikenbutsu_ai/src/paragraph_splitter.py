from __future__ import annotations

import re

# 法令文書で段落開始になりやすいパターン
_BOUNDARY_RE = re.compile(
    r"^("
    r"第[0-9一二三四五六七八九十百千]+条(?:の[0-9一二三四五六七八九十]+)?"
    r"|第[0-9一二三四五六七八九十]+項"
    r"|第[0-9一二三四五六七八九十]+号"
    r"|[0-9]+[\.．、)]"
    r"|[①-⑳]"
    r"|（[0-9一二三四五六七八九十]+）"
    r"|[アイウエオカキクケコサシスセソタチツテトナニヌネノ]"
    r"|附則"
    r"|別記"
    r"|別添"
    r")"
)


def _normalize_lines(text: str) -> list[str]:
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.strip() for ln in t.split("\n")]
    # 連続空白を潰す（OCR崩れ軽減）
    lines = [re.sub(r"\s+", " ", ln) for ln in lines]
    return lines


def split_paragraphs(text: str, min_len: int = 20) -> list[str]:
    lines = _normalize_lines(text)
    paragraphs: list[str] = []
    current: list[str] = []

    def flush() -> None:
        if not current:
            return
        para = " ".join(current).strip()
        if para:
            paragraphs.append(para)
        current.clear()

    for ln in lines:
        if not ln:
            flush()
            continue

        boundary = bool(_BOUNDARY_RE.match(ln))

        # OCR由来の短文折返しは、境界でなければ前段落に吸収
        if boundary:
            flush()
            current.append(ln)
            continue

        if current:
            # 箇条書き/表崩れらしき短行は連結
            if len(ln) < 14:
                current.append(ln)
            else:
                # 直前が短くてつながる場合は連結、それ以外は改段落
                prev = current[-1]
                if len(prev) < 14 or prev.endswith("。") is False:
                    current.append(ln)
                else:
                    flush()
                    current.append(ln)
        else:
            current.append(ln)

    flush()

    # 極端に短い断片は前段落へ吸収
    merged: list[str] = []
    for p in paragraphs:
        if len(p) < min_len and merged:
            merged[-1] = f"{merged[-1]} {p}".strip()
        else:
            merged.append(p)

    return merged
