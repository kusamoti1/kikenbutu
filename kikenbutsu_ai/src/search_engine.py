from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List

import faiss
import numpy as np


class SearchEngine:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(db_path)
        self.index = faiss.IndexFlatL2(1)
        self._cache: List[Dict[str, Any]] = []

    def _embed(self, text: str) -> np.ndarray:
        val = float(sum(ord(c) for c in text) % 100000)
        return np.array([[val]], dtype="float32")

    def rebuild_index(self) -> None:
        self._cache.clear()
        self.index.reset()

        rows = self.conn.execute(
            "SELECT p.id, d.title, p.text, p.confidence FROM paragraphs p JOIN documents d ON p.document_id=d.id"
        ).fetchall()

        if not rows:
            return

        vectors = []
        for pid, title, text, conf in rows:
            self._cache.append({"paragraph_id": pid, "title": title, "text": text, "confidence": conf})
            vectors.append(self._embed(text)[0])

        self.index.add(np.array(vectors, dtype="float32"))

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        if self.index.ntotal == 0:
            return []
        qv = self._embed(query)
        _, idx = self.index.search(qv, k)
        return [self._cache[i] for i in idx[0] if i < len(self._cache)]
