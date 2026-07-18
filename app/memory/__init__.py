"""Memory: local (SQLite) now, cloud (Postgres/vector) later — one interface (spec §3.5).

'Giving your bot memory' (16:03) + 'Building cloud memory' (17:48). The agent reads memory
before acting and writes trades/outcomes/lessons after. Switching backends is config-only.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Protocol

_DB = Path(__file__).resolve().parents[2] / "whale_desk.sqlite"


class Memory(Protocol):
    def write(self, kind: str, record: dict) -> None: ...
    def search(self, query: str, limit: int = 10) -> list[dict]: ...


class LocalMemory:
    """SQLite-backed memory. Records: trades, signals, outcomes, lessons, reports."""

    def __init__(self, path: Path = _DB) -> None:
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS memory "
            "(id INTEGER PRIMARY KEY, kind TEXT, body TEXT)"
        )
        self.conn.commit()

    def write(self, kind: str, record: dict) -> None:
        self.conn.execute(
            "INSERT INTO memory (kind, body) VALUES (?, ?)", (kind, json.dumps(record))
        )
        self.conn.commit()

    def search(self, query: str, limit: int = 10) -> list[dict]:
        # v1: naive LIKE match. TODO(codex): add vector recall for cloud backend.
        rows = self.conn.execute(
            "SELECT body FROM memory WHERE body LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{query}%", limit),
        ).fetchall()
        return [json.loads(r[0]) for r in rows]


# TODO(codex): CloudMemory backed by Postgres/Supabase (+ pgvector or Chroma) implementing the
#              same Protocol. Must pass the SAME tests as LocalMemory (tests/test_memory.py).


def get_memory(settings) -> Memory:
    if settings.memory_backend == "local":
        return LocalMemory()
    raise NotImplementedError("cloud memory not implemented yet — see TODO(codex)")
