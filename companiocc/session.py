"""SQLite-based session manager for persistent conversation storage."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import aiosqlite

from companiocc.helpers import ensure_dir


@dataclass
class Session:
    """A conversation session."""

    session_id: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    last_consolidated: int = 0


class SessionManager:
    """SQLite-based session manager with atomic writes and indexed lookup."""

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        last_consolidated INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL REFERENCES sessions(session_id),
        role TEXT NOT NULL,
        content TEXT,
        tool_calls TEXT,
        tool_call_id TEXT,
        name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_messages_session
        ON messages(session_id);
    """

    def __init__(self, sessions_dir: Path):
        self._db_path = ensure_dir(sessions_dir) / "companiocc.db"
        self._db: aiosqlite.Connection | None = None
        self._cache: dict[str, Session] = {}

    async def initialize(self) -> None:
        self._db = await aiosqlite.connect(str(self._db_path))
        await self._db.executescript(self._SCHEMA)
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.commit()

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    async def get_or_create(self, session_id: str) -> Session:
        if session_id in self._cache:
            return self._cache[session_id]

        assert self._db is not None

        cursor = await self._db.execute(
            "SELECT last_consolidated FROM sessions WHERE session_id = ?",
            (session_id,),
        )
        row = await cursor.fetchone()

        if row is None:
            await self._db.execute("INSERT INTO sessions (session_id) VALUES (?)", (session_id,))
            await self._db.commit()
            session = Session(session_id=session_id)
        else:
            last_consolidated = row[0]
            cursor = await self._db.execute(
                "SELECT role, content, tool_calls, tool_call_id, name "
                "FROM messages WHERE session_id = ? ORDER BY id",
                (session_id,),
            )
            rows = await cursor.fetchall()
            messages = []
            for r in rows:
                msg: dict[str, Any] = {"role": r[0]}
                if r[1] is not None:
                    msg["content"] = r[1]
                if r[2] is not None:
                    msg["tool_calls"] = json.loads(r[2])
                if r[3] is not None:
                    msg["tool_call_id"] = r[3]
                if r[4] is not None:
                    msg["name"] = r[4]
                messages.append(msg)
            session = Session(
                session_id=session_id,
                messages=messages,
                last_consolidated=last_consolidated,
            )

        self._cache[session_id] = session
        return session

    async def save(self, session: Session) -> None:
        assert self._db is not None

        cursor = await self._db.execute(
            "SELECT COUNT(*) FROM messages WHERE session_id = ?",
            (session.session_id,),
        )
        (db_count,) = await cursor.fetchone()

        new_messages = session.messages[db_count:]
        for msg in new_messages:
            await self._db.execute(
                "INSERT INTO messages (session_id, role, content, tool_calls, tool_call_id, name) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    session.session_id,
                    msg.get("role"),
                    msg.get("content"),
                    json.dumps(msg["tool_calls"]) if "tool_calls" in msg else None,
                    msg.get("tool_call_id"),
                    msg.get("name"),
                ),
            )

        await self._db.execute(
            "UPDATE sessions SET last_consolidated = ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE session_id = ?",
            (session.last_consolidated, session.session_id),
        )
        await self._db.commit()

    async def clear(self, session_id: str) -> None:
        assert self._db is not None
        await self._db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        await self._db.execute(
            "UPDATE sessions SET last_consolidated = 0, updated_at = CURRENT_TIMESTAMP "
            "WHERE session_id = ?",
            (session_id,),
        )
        await self._db.commit()
        self._cache.pop(session_id, None)
