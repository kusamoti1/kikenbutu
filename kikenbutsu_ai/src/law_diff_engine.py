from __future__ import annotations

import difflib


def diff_text(old_text: str, new_text: str) -> str:
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()
    return "\n".join(
        difflib.unified_diff(old_lines, new_lines, fromfile="old", tofile="new", lineterm="")
    )
