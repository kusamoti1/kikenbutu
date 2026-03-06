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


def split_paragraphs_with_confidence(lines, threshold: float = 0.85, min_len: int = 20):
    """OCR行リストから段落と信頼度を作る。

    lines: [{"text": "...", "confidence": 0.9, ...}, ...]
    """
    paragraphs = []
    buf_text: list[str] = []
    buf_conf: list[float] = []

    def flush():
        if not buf_text:
            return
        text = " ".join(buf_text).strip()
        if not text:
            buf_text.clear(); buf_conf.clear(); return
        if len(text) < min_len and paragraphs:
            # 極端に短い断片は前段落へ吸収
            prev = paragraphs[-1]
            prev["text_original"] = f"{prev['text_original']} {text}".strip()
            if buf_conf:
                all_conf = [prev["confidence_avg"], *buf_conf] if prev["confidence_avg"] is not None else list(buf_conf)
                prev["confidence_avg"] = sum(all_conf) / len(all_conf)
                prev["confidence_min"] = min([prev["confidence_min"], *buf_conf]) if prev["confidence_min"] is not None else min(buf_conf)
                prev["needs_review"] = prev["confidence_min"] < threshold
        else:
            avg = (sum(buf_conf) / len(buf_conf)) if buf_conf else None
            mn = min(buf_conf) if buf_conf else None
            paragraphs.append({
                "text_original": text,
                "confidence_avg": avg,
                "confidence_min": mn,
                "needs_review": (mn is None) or (mn < threshold),
            })
        buf_text.clear(); buf_conf.clear()

    for row in lines:
        text = str(row.get("text_original") or row.get("text") or "").strip()
        conf = row.get("confidence")
        if text == "":
            flush()
            continue

        boundary = bool(_BOUNDARY_RE.match(text))
        if boundary and buf_text:
            flush()

        buf_text.append(text)
        try:
            if conf is not None:
                buf_conf.append(float(conf))
        except Exception:
            pass

        if text.endswith("。") and len(text) > 14:
            flush()

    flush()
    return paragraphs
