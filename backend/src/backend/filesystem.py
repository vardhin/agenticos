from __future__ import annotations

import sqlite3
import json
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any

from fastapi import HTTPException

from .database import Database
from .schemas import ContentUpdate, FileCreate, FileUpdate


PLACE_PATHS = {
    "Home": "/home/agentos",
    "Desktop": "/home/agentos/Desktop",
    "Documents": "/home/agentos/Documents",
    "Downloads": "/home/agentos/Downloads",
    "Pictures": "/home/agentos/Pictures",
    "Research": "/home/agentos/Documents/Research",
    "File System": "/",
    "Archive USB": "/mnt/archive-usb",
}


class VirtualFilesystem:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def normalize(path: str) -> str:
        path = PLACE_PATHS.get(path, path or "/home/agentos")
        if not path.startswith("/"):
            path = "/home/agentos/" + path
        normalized = str(PurePosixPath(path))
        if ".." in PurePosixPath(path).parts:
            raise HTTPException(400, "Parent traversal is not allowed")
        return normalized

    def resolve(self, connection: sqlite3.Connection, path: str) -> sqlite3.Row:
        normalized = self.normalize(path)
        row = connection.execute(
            "SELECT * FROM file_nodes WHERE parent_id IS NULL AND name = ''"
        ).fetchone()
        if row is None:
            raise HTTPException(500, "Filesystem root is missing")
        for part in PurePosixPath(normalized).parts[1:]:
            row = connection.execute(
                """SELECT * FROM file_nodes
                   WHERE parent_id = ? AND name = ? COLLATE NOCASE AND deleted_at IS NULL""",
                (row["id"], part),
            ).fetchone()
            if row is None:
                raise HTTPException(404, f"Path not found: {normalized}")
        return row

    def path_for(self, connection: sqlite3.Connection, node_id: int) -> str:
        parts: list[str] = []
        current = connection.execute("SELECT * FROM file_nodes WHERE id = ?", (node_id,)).fetchone()
        while current is not None and current["parent_id"] is not None:
            parts.append(current["name"])
            current = connection.execute(
                "SELECT * FROM file_nodes WHERE id = ?", (current["parent_id"],)
            ).fetchone()
        return "/" + "/".join(reversed(parts))

    def serialize(self, connection: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "parent_id": row["parent_id"],
            "name": row["name"],
            "kind": row["kind"],
            "mime_type": row["mime_type"],
            "size": row["size"],
            "starred": bool(row["starred"]),
            "deleted": row["deleted_at"] is not None,
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "path": self.path_for(connection, row["id"]),
        }

    def list(self, path: str, query: str | None = None) -> dict[str, Any]:
        with self.database.transaction() as connection:
            if path == "Trash":
                rows = connection.execute(
                    "SELECT * FROM file_nodes WHERE deleted_at IS NOT NULL ORDER BY name COLLATE NOCASE"
                ).fetchall()
                return {"path": "Trash", "items": [self.serialize(connection, row) for row in rows]}
            if path == "Recent":
                rows = connection.execute(
                    """SELECT * FROM file_nodes WHERE parent_id IS NOT NULL AND deleted_at IS NULL
                       ORDER BY updated_at DESC LIMIT 50"""
                ).fetchall()
                return {"path": "Recent", "items": [self.serialize(connection, row) for row in rows]}
            if path == "Starred":
                rows = connection.execute(
                    """SELECT * FROM file_nodes WHERE starred = 1 AND deleted_at IS NULL
                       ORDER BY name COLLATE NOCASE"""
                ).fetchall()
                return {"path": "Starred", "items": [self.serialize(connection, row) for row in rows]}
            parent = self.resolve(connection, path)
            if parent["kind"] != "folder":
                raise HTTPException(400, "Path is not a folder")
            params: list[Any] = [parent["id"]]
            where = "parent_id = ? AND deleted_at IS NULL"
            if query:
                where += " AND name LIKE ? ESCAPE '\\' COLLATE NOCASE"
                escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                params.append(f"%{escaped}%")
            rows = connection.execute(
                f"SELECT * FROM file_nodes WHERE {where} ORDER BY kind != 'folder', name COLLATE NOCASE",
                params,
            ).fetchall()
            return {
                "path": self.normalize(path),
                "items": [self.serialize(connection, row) for row in rows],
            }

    def search(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        if not query.strip():
            return []
        pattern = f"%{query.strip()}%"
        with self.database.transaction() as connection:
            rows = connection.execute(
                """SELECT * FROM file_nodes
                   WHERE deleted_at IS NULL AND parent_id IS NOT NULL
                     AND (name LIKE ? COLLATE NOCASE OR CAST(content AS TEXT) LIKE ? COLLATE NOCASE)
                   ORDER BY kind = 'folder' DESC, updated_at DESC LIMIT ?""",
                (pattern, pattern, limit),
            ).fetchall()
            return [self.serialize(connection, row) for row in rows]

    def get(self, node_id: int, include_content: bool = False) -> dict[str, Any]:
        with self.database.transaction() as connection:
            row = connection.execute("SELECT * FROM file_nodes WHERE id = ?", (node_id,)).fetchone()
            if row is None:
                raise HTTPException(404, "File not found")
            item = self.serialize(connection, row)
            if include_content:
                content = row["content"] or b""
                item["content"] = bytes(content).decode("utf-8", errors="replace")
            return item

    def create(self, value: FileCreate) -> dict[str, Any]:
        with self.database.transaction() as connection:
            parent = self.resolve(connection, value.parent_path)
            if parent["kind"] != "folder":
                raise HTTPException(400, "Parent is not a folder")
            content = (value.content or "").encode()
            try:
                node_id = connection.execute(
                    """INSERT INTO file_nodes
                       (parent_id, name, kind, mime_type, content, size, starred)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (parent["id"], value.name, value.kind, value.mime_type, content, len(content), value.starred),
                ).lastrowid
            except sqlite3.IntegrityError as error:
                raise HTTPException(409, "An item with that name already exists") from error
            row = connection.execute("SELECT * FROM file_nodes WHERE id = ?", (node_id,)).fetchone()
            return self.serialize(connection, row)

    def update(self, node_id: int, value: FileUpdate) -> dict[str, Any]:
        changes = value.model_dump(exclude_unset=True)
        with self.database.transaction() as connection:
            current = connection.execute("SELECT * FROM file_nodes WHERE id = ?", (node_id,)).fetchone()
            if current is None or current["parent_id"] is None:
                raise HTTPException(404, "File not found")
            parent_id = current["parent_id"]
            if value.parent_path is not None:
                parent = self.resolve(connection, value.parent_path)
                if parent["kind"] != "folder":
                    raise HTTPException(400, "Destination is not a folder")
                if parent["id"] == node_id:
                    raise HTTPException(400, "A folder cannot contain itself")
                descendants = connection.execute(
                    """WITH RECURSIVE tree(id) AS (
                         SELECT id FROM file_nodes WHERE parent_id = ?
                         UNION ALL SELECT f.id FROM file_nodes f JOIN tree t ON f.parent_id = t.id
                       ) SELECT id FROM tree WHERE id = ?""",
                    (node_id, parent["id"]),
                ).fetchone()
                if descendants:
                    raise HTTPException(400, "A folder cannot be moved into its descendant")
                parent_id = parent["id"]
            try:
                connection.execute(
                    """UPDATE file_nodes SET name = ?, parent_id = ?, starred = ?,
                       updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
                    (
                        changes.get("name", current["name"]),
                        parent_id,
                        int(changes.get("starred", bool(current["starred"]))),
                        node_id,
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise HTTPException(409, "An item with that name already exists") from error
            row = connection.execute("SELECT * FROM file_nodes WHERE id = ?", (node_id,)).fetchone()
            return self.serialize(connection, row)

    def update_content(self, node_id: int, value: ContentUpdate) -> dict[str, Any]:
        return self.update_bytes(node_id, value.content.encode(), value.mime_type)

    def update_bytes(
        self, node_id: int, payload: bytes, mime_type: str | None = None
    ) -> dict[str, Any]:
        with self.database.transaction() as connection:
            row = connection.execute("SELECT * FROM file_nodes WHERE id = ?", (node_id,)).fetchone()
            if row is None or row["deleted_at"] is not None:
                raise HTTPException(404, "File not found")
            if row["kind"] == "folder":
                raise HTTPException(400, "Folders do not have content")
            connection.execute(
                """UPDATE file_nodes SET content = ?, size = ?, mime_type = ?,
                   updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
                (payload, len(payload), mime_type or row["mime_type"], node_id),
            )
            updated = connection.execute("SELECT * FROM file_nodes WHERE id = ?", (node_id,)).fetchone()
            return self.serialize(connection, updated)

    def read_bytes(self, node_id: int) -> tuple[bytes, str, str]:
        with self.database.transaction() as connection:
            row = connection.execute("SELECT * FROM file_nodes WHERE id = ?", (node_id,)).fetchone()
            if row is None or row["deleted_at"] is not None:
                raise HTTPException(404, "File not found")
            if row["kind"] == "folder":
                raise HTTPException(400, "Folders do not have content")
            return bytes(row["content"] or b""), row["mime_type"] or "application/octet-stream", row["name"]

    def trash(self, node_id: int) -> None:
        deleted_at = datetime.now(timezone.utc).isoformat()
        with self.database.transaction() as connection:
            row = connection.execute("SELECT * FROM file_nodes WHERE id = ?", (node_id,)).fetchone()
            if row is None or row["parent_id"] is None:
                raise HTTPException(404, "File not found")
            connection.execute(
                """WITH RECURSIVE tree(id) AS (
                     SELECT id FROM file_nodes WHERE id = ?
                     UNION ALL SELECT f.id FROM file_nodes f JOIN tree t ON f.parent_id = t.id
                   ) UPDATE file_nodes SET deleted_at = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE id IN (SELECT id FROM tree)""",
                (node_id, deleted_at),
            )

    def restore(self, node_id: int) -> dict[str, Any]:
        with self.database.transaction() as connection:
            row = connection.execute("SELECT * FROM file_nodes WHERE id = ?", (node_id,)).fetchone()
            if row is None:
                raise HTTPException(404, "File not found")
            try:
                connection.execute(
                    """WITH RECURSIVE tree(id) AS (
                         SELECT id FROM file_nodes WHERE id = ?
                         UNION ALL SELECT f.id FROM file_nodes f JOIN tree t ON f.parent_id = t.id
                       ) UPDATE file_nodes SET deleted_at = NULL, updated_at = CURRENT_TIMESTAMP
                       WHERE id IN (SELECT id FROM tree)""",
                    (node_id,),
                )
            except sqlite3.IntegrityError as error:
                raise HTTPException(409, "Restore conflicts with an existing item") from error
            updated = connection.execute("SELECT * FROM file_nodes WHERE id = ?", (node_id,)).fetchone()
            return self.serialize(connection, updated)

    def copy(self, node_id: int, parent_path: str) -> dict[str, Any]:
        with self.database.transaction() as connection:
            source = connection.execute(
                "SELECT * FROM file_nodes WHERE id = ? AND deleted_at IS NULL", (node_id,)
            ).fetchone()
            if source is None or source["parent_id"] is None:
                raise HTTPException(404, "File not found")
            parent = self.resolve(connection, parent_path)
            if parent["kind"] != "folder":
                raise HTTPException(400, "Destination is not a folder")

            def duplicate(row: sqlite3.Row, parent_id: int, name: str | None = None) -> int:
                try:
                    copied_id = int(connection.execute(
                        """INSERT INTO file_nodes(parent_id, name, kind, mime_type, content, size, starred)
                           VALUES(?, ?, ?, ?, ?, ?, ?)""",
                        (parent_id, name or row["name"], row["kind"], row["mime_type"], row["content"], row["size"], row["starred"]),
                    ).lastrowid)
                except sqlite3.IntegrityError as error:
                    raise HTTPException(409, "An item with that name already exists") from error
                if row["kind"] == "folder":
                    children = connection.execute(
                        "SELECT * FROM file_nodes WHERE parent_id = ? AND deleted_at IS NULL", (row["id"],)
                    ).fetchall()
                    for child in children:
                        duplicate(child, copied_id)
                return copied_id

            copy_name = source["name"]
            if parent["id"] == source["parent_id"]:
                stem, dot, suffix = copy_name.rpartition(".")
                copy_name = f"{stem or suffix} copy{dot}{suffix if dot else ''}"
            copied_id = duplicate(source, parent["id"], copy_name)
            copied = connection.execute("SELECT * FROM file_nodes WHERE id = ?", (copied_id,)).fetchone()
            return self.serialize(connection, copied)

    def delete_permanently(self, node_id: int) -> None:
        with self.database.transaction() as connection:
            row = connection.execute("SELECT * FROM file_nodes WHERE id = ?", (node_id,)).fetchone()
            if row is None or row["parent_id"] is None:
                raise HTTPException(404, "File not found")
            if row["deleted_at"] is None:
                raise HTTPException(409, "Only trashed items can be deleted permanently")
            connection.execute("DELETE FROM file_nodes WHERE id = ?", (node_id,))

    def empty_trash(self) -> int:
        with self.database.transaction() as connection:
            roots = connection.execute(
                """SELECT node.id FROM file_nodes node
                   LEFT JOIN file_nodes parent ON parent.id = node.parent_id
                   WHERE node.deleted_at IS NOT NULL
                     AND (parent.id IS NULL OR parent.deleted_at IS NULL)"""
            ).fetchall()
            for row in roots:
                connection.execute("DELETE FROM file_nodes WHERE id = ?", (row["id"],))
            return len(roots)

    def compress(self, node_ids: list[int], parent_path: str, name: str) -> dict[str, Any]:
        archive_name = name if name.casefold().endswith(".zip") else f"{name}.zip"
        entries = [self.get(node_id) for node_id in node_ids]
        return self.create(FileCreate(
            parent_path=parent_path,
            name=archive_name,
            kind="archive",
            mime_type="application/zip",
            content=json.dumps({"format": "agentos-archive-v1", "entries": entries}),
        ))

    def extract(self, node_id: int, destination: str) -> list[dict[str, Any]]:
        archive = self.get(node_id, include_content=True)
        if archive["kind"] != "archive":
            raise HTTPException(400, "Item is not an archive")
        try:
            entries = json.loads(archive.get("content") or "{}").get("entries", [])
        except (json.JSONDecodeError, AttributeError) as error:
            raise HTTPException(400, "Archive metadata is invalid") from error
        created: list[dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict) or not entry.get("name"):
                continue
            created.append(self.create(FileCreate(
                parent_path=destination,
                name=entry["name"],
                kind=entry.get("kind", "file"),
                mime_type=entry.get("mime_type"),
            )))
        return created
