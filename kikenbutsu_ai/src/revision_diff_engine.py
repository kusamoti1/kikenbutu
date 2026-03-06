from __future__ import annotations

import difflib
from dataclasses import dataclass


@dataclass
class RevisionDiff:
    diff_summary: str
    old_text: str
    new_text: str


def summarize_diff(old_text: str, new_text: str, n: int = 6) -> RevisionDiff:
    old_lines = [x.strip() for x in old_text.splitlines() if x.strip()]
    new_lines = [x.strip() for x in new_text.splitlines() if x.strip()]
    diff = list(difflib.unified_diff(old_lines, new_lines, fromfile="旧", tofile="新", lineterm=""))
    added = [d[1:] for d in diff if d.startswith("+") and not d.startswith("+++")]
    removed = [d[1:] for d in diff if d.startswith("-") and not d.startswith("---")]

    summary_parts = [
        f"追加{len(added)}行",
        f"削除{len(removed)}行",
    ]
    if added:
        summary_parts.append("主な追加: " + " / ".join(added[:n]))
    if removed:
        summary_parts.append("主な削除: " + " / ".join(removed[:n]))

    return RevisionDiff(
        diff_summary="; ".join(summary_parts),
        old_text="\n".join(old_lines[:200]),
        new_text="\n".join(new_lines[:200]),
    )


def _extract_text(p: object) -> str:
    if isinstance(p, dict):
        return str(p.get("text_normalized") or p.get("text_original") or p.get("text") or "")
    return str(getattr(p, "text", ""))


def match_paragraphs(old_paragraphs, new_paragraphs, min_score: float = 0.45):
    """複数段落を保守的に対応付けする。

    old側の各段落について、未使用のnew段落から最良一致を1件だけ採用する。
    """
    matches = []
    used_new: set[int] = set()

    for old in old_paragraphs:
        old_text = _extract_text(old)
        if not old_text:
            continue

        best_idx = -1
        best_score = -1.0
        best_new = None
        for idx, new in enumerate(new_paragraphs):
            if idx in used_new:
                continue
            new_text = _extract_text(new)
            if not new_text:
                continue
            score = difflib.SequenceMatcher(None, old_text[:600], new_text[:600]).ratio()
            # 条文番号が共通なら少し加点
            if "第" in old_text[:40] and "条" in old_text[:40] and old_text[:20] in new_text[:120]:
                score += 0.05
            if score > best_score:
                best_score = score
                best_idx = idx
                best_new = new

        if best_new is not None and best_score >= min_score:
            used_new.add(best_idx)
            matches.append((old, best_new, best_score))

    return matches
