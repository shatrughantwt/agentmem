import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import chromadb

from .models import Memory

SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    entities TEXT NOT NULL,
    source TEXT,
    confidence REAL NOT NULL,
    created_at TEXT NOT NULL,
    valid_from TEXT NOT NULL,
    valid_to TEXT,
    superseded_by TEXT,
    last_accessed TEXT,
    access_count INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id);
"""

INSERT = """
INSERT INTO memories VALUES (
    :id, :user_id, :type, :content, :entities, :source, :confidence,
    :created_at, :valid_from, :valid_to, :superseded_by,
    :last_accessed, :access_count
)
"""


def _from_row(row: sqlite3.Row) -> Memory:
    d = dict(row)
    d["entities"] = json.loads(d["entities"])
    d["source"] = json.loads(d["source"]) if d["source"] else None
    return Memory.model_validate(d)


class Store:
    def __init__(self, path: str = ".agentmem") -> None:
        root = Path(path)
        root.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(root / "memories.db")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        client = chromadb.PersistentClient(path=str(root / "chroma"))
        self.vectors = client.get_or_create_collection("memories")

    def save(self, m: Memory) -> None:
        d = m.model_dump(mode="json")
        d["entities"] = json.dumps(d["entities"])
        d["source"] = json.dumps(d["source"]) if d["source"] else None
        self.db.execute(INSERT, d)
        self.db.commit()
        self.vectors.add(
            ids=[m.id],
            documents=[m.content],
            metadatas=[{"user_id": m.user_id}],
        )

    def get(self, memory_id: str) -> Memory | None:
        row = self.db.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()
        return _from_row(row) if row else None

    def list_active(self, user_id: str) -> list[Memory]:
        rows = self.db.execute(
            "SELECT * FROM memories WHERE user_id = ? AND valid_to IS NULL "
            "ORDER BY created_at",
            (user_id,),
        ).fetchall()
        return [_from_row(r) for r in rows]

    def search(self, user_id: str, query: str, k: int = 5) -> list[tuple[Memory, float]]:
        res = self.vectors.query(
            query_texts=[query], n_results=k, where={"user_id": user_id}
        )
        hits = []
        for mid, dist in zip(res["ids"][0], res["distances"][0]):
            m = self.get(mid)
            if m:
                hits.append((m, dist))  # lower distance = closer match
        return hits

    def supersede(self, old_id: str, new_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "UPDATE memories SET valid_to = ?, superseded_by = ? WHERE id = ?",
            (now, new_id, old_id),
        )
        self.db.commit()
        self.vectors.delete(ids=[old_id])

    def delete(self, memory_id: str) -> None:
        self.db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self.db.commit()
        self.vectors.delete(ids=[memory_id])