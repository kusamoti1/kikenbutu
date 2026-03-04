"""Contextual Retrieval — chunk-level context prefixing.

Japanese legal notifications frequently omit the subject (主語の欠落).
A paragraph like 「底板の板厚は3.2mm以上とすること」 does not mention
which facility type it applies to.  The answer is only found in a
higher-level heading or in the document title.

This module solves that by prepending a deterministic context tag to
every chunk *before* it is stored in the database or exported to
Markdown.  The tag is built from:

  - 対象設備  (equipment name detected in the document)
  - 文書名    (document title / filename)
  - 年代      (era: 昭和 / 平成 / 令和)
  - 関係条文  (law article references found in the document)
  - 上位見出し (heading hierarchy extracted from the OCR text)

Design principles:
  - No inference.  Context is assembled from deterministic detections.
  - The original text is preserved verbatim after the context tag.
  - The context tag is clearly delimited so it can be stripped if needed.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class ContextualChunk:
    """A text chunk with its deterministic context prefix."""
    text: str                    # Original paragraph text (unmodified)
    context: str                 # Machine-generated context string
    contextualized_text: str     # context + text (for DB/export storage)
    heading_path: List[str]      # Heading hierarchy leading to this chunk
    equipment: List[str]         # Equipment names relevant to this chunk
    era: List[str]               # Era(s) relevant to this chunk
    law_refs: List[str]          # Law article references in scope


@dataclass
class HeadingTracker:
    """Tracks the current heading hierarchy while scanning paragraphs."""
    levels: dict[int, str] = field(default_factory=dict)

    def update(self, level: int, text: str) -> None:
        self.levels[level] = text
        # Clear deeper levels.
        for k in list(self.levels):
            if k > level:
                del self.levels[k]

    def path(self) -> List[str]:
        return [self.levels[k] for k in sorted(self.levels)]

    def path_str(self) -> str:
        return " > ".join(self.path()) if self.levels else ""


# ---------------------------------------------------------------------------
# Heading detection
# ---------------------------------------------------------------------------

# Japanese legal document heading patterns (ordered by hierarchy depth).
_HEADING_PATTERNS: List[Tuple[int, re.Pattern[str]]] = [
    # Level 1: 「第1 ...」「第一 ...」
    (1, re.compile(r"^第[0-9一二三四五六七八九十百]+[条章節款の\s]")),
    # Level 2: 「1 ...」「１ ...」(fullwidth/halfwidth digit at line start)
    (2, re.compile(r"^[0-9０-９]+[\s　.．、]")),
    # Level 3: 「(1) ...」「（1） ...」
    (3, re.compile(r"^[（(][0-9０-９]+[）)]\s*")),
    # Level 3 alt: 「ア ...」「イ ...」（katakana bullet）
    (3, re.compile(r"^[アイウエオカキクケコ][\s　]")),
    # Special: 「記」 marker (common in notifications)
    (1, re.compile(r"^記\s*$")),
]


def _detect_heading(line: str) -> Optional[Tuple[int, str]]:
    """If *line* looks like a heading, return (level, heading_text)."""
    stripped = line.strip()
    if not stripped or len(stripped) > 200:
        return None
    for level, pattern in _HEADING_PATTERNS:
        if pattern.match(stripped):
            return level, stripped
    return None


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------

_CONTEXT_PREFIX = "[文脈]"
_CONTEXT_SUFFIX = "\n"


def build_context_tag(
    equipment: List[str],
    doc_title: str,
    eras: List[str],
    law_refs: List[str],
    heading_path: str,
) -> str:
    """Build a deterministic context string from detected metadata.

    Example output:
      [文脈] 対象設備: 地下タンク貯蔵所 | 文書: 通知第123号 | 年代: 昭和 | 見出し: 構造基準 > 底板
    """
    parts: List[str] = [_CONTEXT_PREFIX]

    if equipment:
        parts.append(f"対象設備: {', '.join(equipment)}")
    if doc_title:
        parts.append(f"文書: {doc_title}")
    if eras:
        parts.append(f"年代: {', '.join(eras)}")
    if law_refs:
        # Keep concise — max 3 refs in the tag.
        refs = law_refs[:3]
        parts.append(f"条文: {', '.join(refs)}")
        if len(law_refs) > 3:
            parts[-1] += f" 他{len(law_refs) - 3}件"
    if heading_path:
        parts.append(f"見出し: {heading_path}")

    return " | ".join(parts)


def build_contextual_chunks(
    paragraphs: List[str],
    doc_title: str,
    equipment: List[str],
    eras: List[str],
    law_refs: List[Tuple[str, str]],
) -> List[ContextualChunk]:
    """Convert raw paragraphs into context-prefixed chunks.

    This function:
    1. Scans each paragraph for heading patterns to track the
       hierarchical position in the document.
    2. Detects per-paragraph equipment/era overrides (a paragraph
       mentioning "移動タンク" in a "地下タンク" document gets both).
    3. Builds a context tag from the accumulated metadata.
    4. Prepends the context tag to the original text.

    The original text is NEVER modified — only prefixed.
    """
    from src.equipment_tree_builder import detect_equipment as _detect_eq
    from src.era_tree_builder import detect_eras as _detect_eras

    tracker = HeadingTracker()
    law_ref_strs = [f"{name} {art}" for name, art in law_refs]

    chunks: List[ContextualChunk] = []

    for para in paragraphs:
        # Update heading tracker from the first line of the paragraph.
        first_line = para.split("\n", 1)[0] if para else ""
        heading = _detect_heading(first_line)
        if heading:
            tracker.update(heading[0], heading[1])

        # Per-paragraph equipment/era detection (may refine doc-level).
        para_equipment = _detect_eq(para)
        effective_equipment = para_equipment if para_equipment else equipment

        para_eras = _detect_eras(para)
        effective_eras = para_eras if para_eras != ["不明"] else eras

        heading_path = tracker.path_str()

        context = build_context_tag(
            equipment=effective_equipment,
            doc_title=doc_title,
            eras=effective_eras,
            law_refs=law_ref_strs,
            heading_path=heading_path,
        )

        contextualized = f"{context}{_CONTEXT_SUFFIX}{para}"

        chunks.append(
            ContextualChunk(
                text=para,
                context=context,
                contextualized_text=contextualized,
                heading_path=tracker.path(),
                equipment=list(effective_equipment),
                era=list(effective_eras),
                law_refs=law_ref_strs,
            )
        )

    return chunks


def strip_context(contextualized_text: str) -> str:
    """Remove the context prefix, returning only the original text."""
    if contextualized_text.startswith(_CONTEXT_PREFIX):
        idx = contextualized_text.find(_CONTEXT_SUFFIX)
        if idx != -1:
            return contextualized_text[idx + len(_CONTEXT_SUFFIX):]
    return contextualized_text
