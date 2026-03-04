from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import List


def list_required_standards(db_path: Path, equipment_name: str) -> List[str]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        """
        SELECT s.name
        FROM standards s
        JOIN equipment e ON s.equipment_id = e.id
        WHERE e.name = ?
        ORDER BY s.name
        """,
        (equipment_name,),
    ).fetchall()
    conn.close()
    return [r[0] for r in rows]
