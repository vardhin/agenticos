from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Any
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .database import Database
from .filesystem import VirtualFilesystem
from .schemas import CommandCreate, ContentUpdate, EventCreate, FileCreate, FileUpdate, StatePatch, StateUpdate


database = Database()
filesystem = VirtualFilesystem(database)
command_subscribers: set[asyncio.Queue[str]] = set()


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.initialize()
    yield


app = FastAPI(
    title="AgentOS API",
    version="0.1.0",
    description="Persistent state and virtual filesystem service for the AgentOS simulation.",
    lifespan=lifespan,
)
origins = [item.strip() for item in os.getenv("AGENTOS_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "database": str(database.path)}


def load_state() -> dict[str, Any]:
    with database.transaction() as connection:
        row = connection.execute("SELECT * FROM os_state WHERE id = 1").fetchone()
        return {"value": json.loads(row["value"]), "revision": row["revision"], "updated_at": row["updated_at"]}


@app.get("/api/state", tags=["state"])
async def get_state() -> dict[str, Any]:
    return load_state()


def save_state(value: dict[str, Any], expected_revision: int | None) -> dict[str, Any]:
    with database.transaction() as connection:
        current = connection.execute("SELECT revision FROM os_state WHERE id = 1").fetchone()
        if expected_revision is not None and expected_revision != current["revision"]:
            raise HTTPException(409, detail={"message": "State revision conflict", "revision": current["revision"]})
        revision = current["revision"] + 1
        connection.execute(
            "UPDATE os_state SET value = ?, revision = ?, updated_at = CURRENT_TIMESTAMP WHERE id = 1",
            (json.dumps(value, separators=(",", ":")), revision),
        )
        return {"value": value, "revision": revision}


@app.put("/api/state", tags=["state"])
async def put_state(value: StateUpdate) -> dict[str, Any]:
    return save_state(value.value, value.expected_revision)


@app.patch("/api/state", tags=["state"])
async def patch_state(value: StatePatch) -> dict[str, Any]:
    current = load_state()
    merged = {**current["value"], **value.value}
    return save_state(merged, value.expected_revision)


@app.get("/api/files", tags=["files"])
async def list_files(path: str = "/home/agentos", query: str | None = None) -> dict[str, Any]:
    return filesystem.list(path, query)


@app.get("/api/files/search", tags=["files"])
async def search_files(q: str = Query(min_length=1), limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
    return {"query": q, "items": filesystem.search(q, limit)}


@app.post("/api/files", status_code=201, tags=["files"])
async def create_file(value: FileCreate) -> dict[str, Any]:
    return filesystem.create(value)


@app.get("/api/files/{node_id}", tags=["files"])
async def get_file(node_id: int, include_content: bool = False) -> dict[str, Any]:
    return filesystem.get(node_id, include_content)


@app.patch("/api/files/{node_id}", tags=["files"])
async def update_file(node_id: int, value: FileUpdate) -> dict[str, Any]:
    return filesystem.update(node_id, value)


@app.put("/api/files/{node_id}/content", tags=["files"])
async def update_file_content(node_id: int, request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "application/octet-stream").split(";", 1)[0]
    if content_type == "application/json":
        value = ContentUpdate.model_validate(await request.json())
        return filesystem.update_content(node_id, value)
    return filesystem.update_bytes(node_id, await request.body(), content_type)


@app.get("/api/files/{node_id}/content", tags=["files"])
async def read_file_content(node_id: int, download: bool = False) -> Response:
    content, mime_type, name = filesystem.read_bytes(node_id)
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"} if download else {}
    return Response(content=content, media_type=mime_type, headers=headers)


@app.delete("/api/files/{node_id}", status_code=204, tags=["files"])
async def delete_file(node_id: int) -> Response:
    filesystem.trash(node_id)
    return Response(status_code=204)


@app.post("/api/files/{node_id}/restore", tags=["files"])
async def restore_file(node_id: int) -> dict[str, Any]:
    return filesystem.restore(node_id)


@app.get("/api/events", tags=["events"])
async def list_events(limit: int = Query(default=120, ge=1, le=1000)) -> dict[str, Any]:
    with database.transaction() as connection:
        rows = connection.execute("SELECT * FROM action_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return {
            "items": [
                {
                    "id": row["id"], "time": row["display_time"], "source": row["source"],
                    "node": row["node"], "result": row["result"], "detail": row["detail"],
                    "durationMs": row["duration_ms"],
                }
                for row in rows
            ]
        }


@app.post("/api/events", status_code=201, tags=["events"])
async def create_event(value: EventCreate) -> dict[str, Any]:
    with database.transaction() as connection:
        event_id = connection.execute(
            """INSERT INTO action_events(display_time, source, node, result, detail, duration_ms, input_json)
               VALUES(?, ?, ?, ?, ?, ?, ?)""",
            (value.time, value.source, value.node, value.result, value.detail, value.durationMs, json.dumps(value.input)),
        ).lastrowid
    return {"id": event_id, **value.model_dump(exclude={"input"})}


@app.get("/api/control", tags=["control"])
async def control_stream(request: Request) -> StreamingResponse:
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
    command_subscribers.add(queue)

    async def stream():
        try:
            yield 'event: ready\ndata: {"connected":true}\n\n'
            while not await request.is_disconnected():
                try:
                    packet = await asyncio.wait_for(queue.get(), timeout=20)
                    yield f"event: command\ndata: {packet}\n\n"
                except TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            command_subscribers.discard(queue)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.post("/api/control", status_code=202, tags=["control"])
async def send_command(value: CommandCreate) -> dict[str, Any]:
    packet = json.dumps(value.model_dump(), separators=(",", ":"))
    delivered = 0
    for queue in list(command_subscribers):
        try:
            queue.put_nowait(packet)
            delivered += 1
        except asyncio.QueueFull:
            command_subscribers.discard(queue)
    return {"accepted": True, "command": value, "listeners": delivered}
