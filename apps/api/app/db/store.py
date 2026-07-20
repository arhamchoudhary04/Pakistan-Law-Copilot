"""SQLite storage for user accounts and per-user chat history.

Kept separate from the Neo4j corpus graph (which is wiped and rebuilt on every
corpus change), and built on the stdlib ``sqlite3`` module so it adds no dependency.

Schema:
    users(id, email, name, password_hash, created_at)
    conversations(id, user_id -> users, title, created_at, updated_at)
    messages(id, conversation_id -> conversations, ordinal, role, content, meta, created_at)
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _id() -> str:
    return uuid.uuid4().hex


@dataclass
class Account:
    id: str
    email: str
    name: str = ""


class EmailTakenError(Exception):
    """Raised when signing up with an email that already exists."""


class AccountStore:
    """Thin data-access layer over a SQLite database file."""

    def __init__(self, path: Path) -> None:
        self._path = str(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        # Fresh connection per operation: safe across FastAPI's request threadpool.
        conn = sqlite3.connect(self._path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id            TEXT PRIMARY KEY,
                    email         TEXT UNIQUE NOT NULL,
                    name          TEXT NOT NULL DEFAULT '',
                    password_hash TEXT NOT NULL,
                    created_at    TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS conversations (
                    id         TEXT PRIMARY KEY,
                    user_id    TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title      TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id              TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    ordinal         INTEGER NOT NULL,
                    role            TEXT NOT NULL,
                    content         TEXT NOT NULL,
                    meta            TEXT,
                    created_at      TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations(user_id, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id, ordinal);
                """
            )
            # Migration: add `name` to databases created before it existed.
            cols = {r["name"] for r in c.execute("PRAGMA table_info(users)")}
            if "name" not in cols:
                c.execute("ALTER TABLE users ADD COLUMN name TEXT NOT NULL DEFAULT ''")

    # ---- users ----

    def create_user(self, email: str, name: str, password_hash: str) -> Account:
        uid = _id()
        try:
            with self._conn() as c:
                c.execute(
                    "INSERT INTO users (id, email, name, password_hash, created_at) "
                    "VALUES (?,?,?,?,?)",
                    (uid, email, name, password_hash, _now()),
                )
        except sqlite3.IntegrityError as exc:
            raise EmailTakenError(email) from exc
        return Account(id=uid, email=email, name=name)

    def find_credentials(self, email: str) -> tuple[str, str] | None:
        """Return (user_id, password_hash) for an email, or None."""
        with self._conn() as c:
            row = c.execute(
                "SELECT id, password_hash FROM users WHERE email = ?", (email,)
            ).fetchone()
        return (row["id"], row["password_hash"]) if row else None

    def get_account(self, user_id: str) -> Account | None:
        with self._conn() as c:
            row = c.execute(
                "SELECT id, email, name FROM users WHERE id = ?", (user_id,)
            ).fetchone()
        return Account(id=row["id"], email=row["email"], name=row["name"]) if row else None

    def get_user_id_by_email(self, email: str) -> str | None:
        with self._conn() as c:
            row = c.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        return row["id"] if row else None

    def update_password(self, user_id: str, password_hash: str) -> bool:
        with self._conn() as c:
            cur = c.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id)
            )
            return cur.rowcount > 0

    # ---- conversations ----

    def create_conversation(self, user_id: str, title: str) -> dict:
        cid = _id()
        ts = _now()
        with self._conn() as c:
            c.execute(
                "INSERT INTO conversations (id, user_id, title, created_at, updated_at) "
                "VALUES (?,?,?,?,?)",
                (cid, user_id, title.strip() or "New chat", ts, ts),
            )
        return {"id": cid, "title": title.strip() or "New chat", "updated_at": ts}

    def list_conversations(self, user_id: str) -> list[dict]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT id, title, updated_at FROM conversations "
                "WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_conversation(self, user_id: str, conv_id: str) -> dict | None:
        with self._conn() as c:
            conv = c.execute(
                "SELECT id, title, updated_at FROM conversations WHERE id = ? AND user_id = ?",
                (conv_id, user_id),
            ).fetchone()
            if conv is None:
                return None
            msgs = c.execute(
                "SELECT role, content, meta FROM messages "
                "WHERE conversation_id = ? ORDER BY ordinal",
                (conv_id,),
            ).fetchall()
        return {
            "id": conv["id"],
            "title": conv["title"],
            "updated_at": conv["updated_at"],
            "messages": [
                {
                    "role": m["role"],
                    "content": m["content"],
                    "meta": json.loads(m["meta"]) if m["meta"] else None,
                }
                for m in msgs
            ],
        }

    def delete_conversation(self, user_id: str, conv_id: str) -> bool:
        with self._conn() as c:
            cur = c.execute(
                "DELETE FROM conversations WHERE id = ? AND user_id = ?", (conv_id, user_id)
            )
            return cur.rowcount > 0

    def append_turn(
        self, user_id: str, conv_id: str, question: str, answer: str, meta: dict | None
    ) -> bool:
        """Append a user question + assistant answer to a conversation the user owns."""
        with self._conn() as c:
            owns = c.execute(
                "SELECT 1 FROM conversations WHERE id = ? AND user_id = ?", (conv_id, user_id)
            ).fetchone()
            if owns is None:
                return False
            row = c.execute(
                "SELECT COALESCE(MAX(ordinal), -1) AS n FROM messages WHERE conversation_id = ?",
                (conv_id,),
            ).fetchone()
            base = int(row["n"]) + 1
            ts = _now()
            c.execute(
                "INSERT INTO messages (id, conversation_id, ordinal, role, content, meta, "
                "created_at) VALUES (?,?,?,?,?,?,?)",
                (_id(), conv_id, base, "user", question, None, ts),
            )
            c.execute(
                "INSERT INTO messages (id, conversation_id, ordinal, role, content, meta, "
                "created_at) VALUES (?,?,?,?,?,?,?)",
                (_id(), conv_id, base + 1, "assistant", answer,
                 json.dumps(meta) if meta else None, ts),
            )
            c.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (ts, conv_id))
        return True


@lru_cache
def get_account_store() -> AccountStore:
    """Return a cached AccountStore backed by the configured SQLite file."""
    return AccountStore(get_settings().app_db_path)
