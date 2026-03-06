from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DocumentMetadata:
    title: str
    year: int | None
    era_label: str | None
    document_type: str
    source: str


_ERA_RE = re.compile(r"(昭和|平成|令和)\s*([0-9]{1,2})年")
_YEAR_RE = re.compile(r"(19\d{2}|20\d{2})年")


def _detect_doc_type(title: str, text: str) -> str:
    if "施行令" in title or "施行令" in text[:500]:
        return "政令"
    if "施行規則" in title or "施行規則" in text[:500]:
        return "規則"
    if "告示" in title or "告示" in text[:500]:
        return "告示"
    if "通知" in title or "通知" in text[:500]:
        return "通知"
    if "マニュアル" in title:
        return "マニュアル"
    return "法令資料"


def _detect_source(title: str, text: str) -> str:
    header = f"{title}\n{text[:800]}"
    if "消防庁" in header:
        return "消防庁"
    if "都道府県" in header or "市" in header or "県" in header:
        return "自治体"
    return "不明"


def extract_metadata(pdf_path: Path, text: str) -> DocumentMetadata:
    title = pdf_path.stem
    m_era = _ERA_RE.search(title) or _ERA_RE.search(text[:1500])
    era_label = None
    year = None
    if m_era:
        era, n = m_era.groups()
        n_int = int(n)
        era_label = era
        if era == "令和":
            year = 2018 + n_int
        elif era == "平成":
            year = 1988 + n_int
        elif era == "昭和":
            year = 1925 + n_int
    else:
        m_year = _YEAR_RE.search(title) or _YEAR_RE.search(text[:1500])
        if m_year:
            year = int(m_year.group(1))
            if year >= 2019:
                era_label = "令和"
            elif year >= 1989:
                era_label = "平成"
            else:
                era_label = "昭和"

    return DocumentMetadata(
        title=title,
        year=year,
        era_label=era_label,
        document_type=_detect_doc_type(title, text),
        source=_detect_source(title, text),
    )
