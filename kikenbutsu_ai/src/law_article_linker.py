from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class LawLink:
    law_name: str
    article_number: str
    paragraph_number: str | None
    item_number: str | None
    confidence: float


LAW_PREFIX = {
    "消防法": r"消防法",
    "消防法施行令": r"(?:消防法)?施行令",
    "消防法施行規則": r"(?:消防法)?施行規則",
    "危険物の規制に関する政令": r"危険物の規制に関する政令",
    "危険物の規制に関する規則": r"危険物の規制に関する規則",
}

ARTICLE_PATTERN = (
    r"第(?P<article>[0-9一二三四五六七八九十百千]+(?:条|条の[0-9一二三四五六七八九十]+|条の二|条の三))"
    r"(?:\s*第(?P<para>[0-9一二三四五六七八九十]+)項)?"
    r"(?:\s*第(?P<item>[0-9一二三四五六七八九十]+)号)?"
)


def extract_law_article_links(text: str) -> list[LawLink]:
    links: list[LawLink] = []
    seen: set[tuple[str, str, str | None, str | None]] = set()

    for law_name, law_pat in LAW_PREFIX.items():
        pattern = re.compile(rf"(?:{law_pat})\s*{ARTICLE_PATTERN}")
        for m in pattern.finditer(text):
            key = (law_name, m.group("article"), m.group("para"), m.group("item"))
            if key in seen:
                continue
            seen.add(key)
            links.append(LawLink(law_name, m.group("article"), m.group("para"), m.group("item"), 0.95))

    # 法令名が明示されない条文候補（保守的に低信頼）
    for m in re.finditer(ARTICLE_PATTERN, text):
        key = ("条文候補", m.group("article"), m.group("para"), m.group("item"))
        if key in seen:
            continue
        seen.add(key)
        links.append(LawLink("条文候補", m.group("article"), m.group("para"), m.group("item"), 0.55))

    for m in re.finditer(r"(別表(?:第?[0-9一二三四五六七八九十]+)?)", text):
        key = ("別表", m.group(1), None, None)
        if key not in seen:
            seen.add(key)
            links.append(LawLink("別表", m.group(1), None, None, 0.8))

    if "ただし書" in text:
        key = ("ただし書", "ただし書", None, None)
        if key not in seen:
            seen.add(key)
            links.append(LawLink("ただし書", "ただし書", None, None, 0.65))

    for m in re.finditer(r"(告示第?\s*[0-9]+号)", text):
        key = ("告示番号", m.group(1), None, None)
        if key not in seen:
            seen.add(key)
            links.append(LawLink("告示番号", m.group(1), None, None, 0.75))

    for m in re.finditer(r"(通知(?:第)?\s*[0-9\-]+号?)", text):
        key = ("通知番号", m.group(1), None, None)
        if key not in seen:
            seen.add(key)
            links.append(LawLink("通知番号", m.group(1), None, None, 0.7))

def extract_law_article_links(text: str) -> list[LawLink]:
    links: list[LawLink] = []
    seen: set[tuple[str, str, str | None, str | None]] = set()

    for law_name, law_pat in LAW_PREFIX.items():
        pattern = re.compile(
            rf"{law_pat}\s*第(?P<article>[0-9一二三四五六七八九十百千]+条(?:の[0-9一二三四五六七八九十]+)?)"
            rf"(?:\s*第(?P<para>[0-9一二三四五六七八九十]+)項)?"
            rf"(?:\s*第(?P<item>[0-9一二三四五六七八九十]+)号)?"
        )
        for m in pattern.finditer(text):
            key = (law_name, m.group("article"), m.group("para"), m.group("item"))
            if key in seen:
                continue
            seen.add(key)
            links.append(
                LawLink(
                    law_name=law_name,
                    article_number=m.group("article"),
                    paragraph_number=m.group("para"),
                    item_number=m.group("item"),
                    confidence=0.95,
                )
            )

    # 別表参照
    for m in re.finditer(r"(別表第?[0-9一二三四五六七八九十]+)", text):
        key = ("別表", m.group(1), None, None)
        if key not in seen:
            seen.add(key)
            links.append(LawLink("別表", m.group(1), None, None, 0.75))

    return links
