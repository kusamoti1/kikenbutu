from __future__ import annotations

import hashlib
from pathlib import Path


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def safe_text(v: str | None) -> str:
    return (v or "").strip()
