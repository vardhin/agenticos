from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any


SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS file_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    parent_id INTEGER REFERENCES file_nodes(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('folder', 'text', 'file', 'pdf', 'archive', 'image')),
    mime_type TEXT,
    content BLOB,
    size INTEGER NOT NULL DEFAULT 0,
    starred INTEGER NOT NULL DEFAULT 0 CHECK (starred IN (0, 1)),
    deleted_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK ((parent_id IS NULL AND name = '') OR (parent_id IS NOT NULL AND name NOT IN ('', '.', '..')))
);

CREATE UNIQUE INDEX IF NOT EXISTS file_nodes_unique_active_name
ON file_nodes(parent_id, name COLLATE NOCASE) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS file_nodes_parent ON file_nodes(parent_id);
CREATE INDEX IF NOT EXISTS file_nodes_updated ON file_nodes(updated_at DESC);

CREATE TABLE IF NOT EXISTS os_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    value TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS action_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    display_time TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('human', 'remote', 'system')),
    node TEXT NOT NULL,
    result TEXT NOT NULL CHECK (result IN ('ok', 'error')),
    detail TEXT NOT NULL,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    input_json TEXT
);
CREATE INDEX IF NOT EXISTS action_events_occurred ON action_events(id DESC);
"""


class Database:
    def __init__(self, path: str | Path | None = None) -> None:
        configured = path or os.getenv("AGENTOS_DB_PATH")
        project_root = Path(__file__).resolve().parents[2]
        self.path = Path(configured) if configured else project_root / "data" / "agentos.db"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self.connect()
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.transaction() as connection:
            connection.executescript(SCHEMA)
            root = connection.execute(
                "SELECT id FROM file_nodes WHERE parent_id IS NULL AND name = ''"
            ).fetchone()
            if root is None:
                root_id = connection.execute(
                    "INSERT INTO file_nodes(parent_id, name, kind) VALUES(NULL, '', 'folder')"
                ).lastrowid
                self._seed_files(connection, int(root_id))
            connection.execute(
                "INSERT OR IGNORE INTO os_state(id, value) VALUES(1, ?)",
                (json.dumps({}),),
            )

    def _seed_files(self, connection: sqlite3.Connection, root_id: int) -> None:
        def folder(parent: int, name: str) -> int:
            return int(
                connection.execute(
                    "INSERT INTO file_nodes(parent_id, name, kind) VALUES(?, ?, 'folder')",
                    (parent, name),
                ).lastrowid
            )

        def file(parent: int, name: str, kind: str, mime: str, content: bytes) -> None:
            connection.execute(
                """INSERT INTO file_nodes(parent_id, name, kind, mime_type, content, size)
                   VALUES(?, ?, ?, ?, ?, ?)""",
                (parent, name, kind, mime, content, len(content)),
            )

        home = folder(root_id, "home")
        agentos = folder(home, "agentos")
        desktop = folder(agentos, "Desktop")
        documents = folder(agentos, "Documents")
        downloads = folder(agentos, "Downloads")
        pictures = folder(agentos, "Pictures")
        research = folder(documents, "Research")
        mnt = folder(root_id, "mnt")
        folder(mnt, "archive-usb")
        folder(agentos, "Music")
        folder(agentos, "Videos")
        file(
            research,
            "desktop-actions-notes.txt",
            "text",
            "text/plain",
            b"Desktop Actions - Research Notes\n\nThis document is stored in the AgentOS virtual filesystem.\n",
        )
        file(research, "agent-architecture.pdf", "pdf", "application/pdf", b"")
        file(downloads, "research-assets.zip", "archive", "application/zip", b"")
        file(desktop, "Welcome.txt", "text", "text/plain", b"Welcome to AgentOS.\n")
        file(pictures, "aurora-wallpaper.png", "image", "image/png", b"")


def row_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}
