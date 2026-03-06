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
