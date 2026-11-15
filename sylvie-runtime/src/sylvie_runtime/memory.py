from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from uuid import uuid4


@dataclass(frozen=True)
class MemoryRecord:
    memory_id: str
    user_id: str
    category: str
    content: str
    source: str
    created_at: str

    def as_dict(self) -> dict[str, str]:
        return {
            "memory_id": self.memory_id,
            "user_id": self.user_id,
            "category": self.category,
            "content": self.content,
            "source": self.source,
            "created_at": self.created_at,
        }


class SQLiteMemoryStore:
    """Explicit-consent, user-scoped persistent memory.

    This store does not encrypt the database. Deployments handling real user
    data must protect the database file and backups with platform-level access
    controls and encryption, and must authenticate user identities upstream.
    """

    def __init__(self, database_path: str | Path, *, max_records_per_user: int = 500,
                 max_content_chars: int = 4000) -> None:
        if max_records_per_user < 1 or max_content_chars < 1:
            raise ValueError("Memory limits must be positive.")
        self.database_path = str(database_path)
        self.max_records_per_user = max_records_per_user
        self.max_content_chars = max_content_chars
        self._lock = RLock()
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS memory_consent (
                    user_id TEXT PRIMARY KEY,
                    enabled INTEGER NOT NULL CHECK (enabled IN (0, 1)),
                    updated_at TEXT NOT NULL
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            db.execute("CREATE INDEX IF NOT EXISTS idx_memories_user_created ON memories(user_id, created_at)")

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.database_path, timeout=10)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def _validate_user(user_id: str) -> str:
        if not isinstance(user_id, str) or not user_id.strip() or len(user_id) > 200:
            raise ValueError("A valid user_id is required.")
        return user_id.strip()

    def set_consent(self, user_id: str, enabled: bool) -> None:
        user_id = self._validate_user(user_id)
        if not isinstance(enabled, bool):
            raise ValueError("enabled must be a boolean.")
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as db:
            db.execute(
                "INSERT INTO memory_consent(user_id, enabled, updated_at) VALUES(?, ?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET enabled=excluded.enabled, updated_at=excluded.updated_at",
                (user_id, int(enabled), now),
            )
            if not enabled:
                db.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))

    def has_consent(self, user_id: str) -> bool:
        user_id = self._validate_user(user_id)
        with self._connect() as db:
            row = db.execute("SELECT enabled FROM memory_consent WHERE user_id = ?", (user_id,)).fetchone()
            return bool(row and row["enabled"])

    def remember(self, user_id: str, content: str, *, category: str = "general",
                 source: str = "user_explicit") -> MemoryRecord:
        user_id = self._validate_user(user_id)
        if not self.has_consent(user_id):
            raise PermissionError("Persistent memory is disabled until the user opts in.")
        if not isinstance(content, str) or not content.strip() or len(content) > self.max_content_chars:
            raise ValueError("Memory content is empty or exceeds the configured limit.")
        if not isinstance(category, str) or not category.strip() or len(category) > 80:
            raise ValueError("A valid memory category is required.")
        if not isinstance(source, str) or not source.strip() or len(source) > 120:
            raise ValueError("A valid memory source is required.")
        record = MemoryRecord(uuid4().hex, user_id, category.strip(), content.strip(),
                              source.strip(), datetime.now(timezone.utc).isoformat())
        with self._lock, self._connect() as db:
            # Re-check consent in the write transaction to avoid storing after opt-out.
            row = db.execute("SELECT enabled FROM memory_consent WHERE user_id = ?", (user_id,)).fetchone()
            if not row or not row["enabled"]:
                raise PermissionError("Persistent memory is disabled.")
            db.execute(
                "INSERT INTO memories(memory_id,user_id,category,content,source,created_at) VALUES(?,?,?,?,?,?)",
                (record.memory_id, record.user_id, record.category, record.content, record.source, record.created_at),
            )
            db.execute("""
                DELETE FROM memories WHERE memory_id IN (
                    SELECT memory_id FROM memories WHERE user_id = ?
                    ORDER BY created_at DESC, memory_id DESC LIMIT -1 OFFSET ?
                )
            """, (user_id, self.max_records_per_user))
        return record

    def retrieve(self, user_id: str, *, category: str | None = None, limit: int = 20) -> list[MemoryRecord]:
        user_id = self._validate_user(user_id)
        if not self.has_consent(user_id):
            return []
        if not isinstance(limit, int) or limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100.")
        with self._connect() as db:
            if category is None:
                rows = db.execute(
                    "SELECT * FROM memories WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
                    (user_id, limit),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT * FROM memories WHERE user_id = ? AND category = ? ORDER BY created_at DESC LIMIT ?",
                    (user_id, category, limit),
                ).fetchall()
        return [MemoryRecord(**dict(row)) for row in rows]

    def delete(self, user_id: str, memory_id: str) -> bool:
        user_id = self._validate_user(user_id)
        with self._lock, self._connect() as db:
            result = db.execute("DELETE FROM memories WHERE user_id = ? AND memory_id = ?", (user_id, memory_id))
            return result.rowcount > 0

    def export(self, user_id: str) -> str:
        records = [record.as_dict() for record in self.retrieve(user_id, limit=100)]
        return json.dumps(records, ensure_ascii=False, indent=2)

    def clear(self, user_id: str) -> int:
        user_id = self._validate_user(user_id)
        with self._lock, self._connect() as db:
            result = db.execute("DELETE FROM memories WHERE user_id = ?", (user_id,))
            return result.rowcount
