import asyncio
from pathlib import Path

import httpx

from backend.app import app, database, filesystem
from backend.database import Database


def configure_database(tmp_path: Path) -> None:
    test_database = Database(tmp_path / "agentos-test.db")
    test_database.initialize()
    database.path = test_database.path
    filesystem.database = database


def test_filesystem_crud_search_and_trash(tmp_path: Path) -> None:
    configure_database(tmp_path)

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post(
                "/api/files",
                json={
                    "parent_path": "Documents",
                    "name": "plan.txt",
                    "kind": "text",
                    "content": "launch plan",
                },
            )
            assert created.status_code == 201
            item = created.json()

            listing = await client.get("/api/files", params={"path": "Documents"})
            assert any(entry["name"] == "plan.txt" for entry in listing.json()["items"])

            content = await client.get(f"/api/files/{item['id']}", params={"include_content": True})
            assert content.json()["content"] == "launch plan"

            assert (
                await client.put(
                    f"/api/files/{item['id']}/content",
                    json={"content": "revised launch plan"},
                )
            ).status_code == 200

            binary = await client.post(
                "/api/files",
                json={"parent_path": "Downloads", "name": "sample.bin", "kind": "file"},
            )
            binary_id = binary.json()["id"]
            assert (
                await client.put(
                    f"/api/files/{binary_id}/content",
                    content=b"\x00\x01agentos",
                    headers={"content-type": "application/octet-stream"},
                )
            ).json()["size"] == 9
            downloaded = await client.get(f"/api/files/{binary_id}/content")
            assert downloaded.content == b"\x00\x01agentos"
            assert downloaded.headers["content-type"] == "application/octet-stream"
            results = (await client.get("/api/files/search", params={"q": "revised"})).json()["items"]
            assert [result["name"] for result in results] == ["plan.txt"]

            assert (
                await client.patch(
                    f"/api/files/{item['id']}",
                    json={"name": "roadmap.txt", "starred": True},
                )
            ).status_code == 200
            assert (await client.delete(f"/api/files/{item['id']}")).status_code == 204
            trash = (await client.get("/api/files", params={"path": "Trash"})).json()["items"]
            assert any(entry["name"] == "roadmap.txt" for entry in trash)
            assert (await client.post(f"/api/files/{item['id']}/restore")).status_code == 200

    asyncio.run(scenario())


def test_state_revisions_and_events(tmp_path: Path) -> None:
    configure_database(tmp_path)

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            initial = (await client.get("/api/state")).json()
            saved = await client.put(
                "/api/state",
                json={
                    "value": {"darkMode": False},
                    "expected_revision": initial["revision"],
                },
            )
            assert saved.status_code == 200
            conflict = await client.put(
                "/api/state",
                json={
                    "value": {"darkMode": True},
                    "expected_revision": initial["revision"],
                },
            )
            assert conflict.status_code == 409

            event = {
                "time": "12:30:00",
                "source": "human",
                "node": "files.path",
                "result": "ok",
                "detail": "Opened Documents",
                "durationMs": 2,
            }
            assert (await client.post("/api/events", json=event)).status_code == 201
            assert (await client.get("/api/events")).json()["items"][0]["node"] == "files.path"

    asyncio.run(scenario())


def test_copy_archive_extract_and_permanent_delete(tmp_path: Path) -> None:
    configure_database(tmp_path)

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = (await client.post("/api/files", json={
                "parent_path": "Documents", "name": "source.txt", "kind": "text", "content": "source"
            })).json()
            copied = await client.post(
                f"/api/files/{created['id']}/copy", json={"parent_path": "Downloads"}
            )
            assert copied.status_code == 200
            assert copied.json()["path"].endswith("/Downloads/source.txt")
            archive = await client.post("/api/files/archive", json={
                "node_ids": [created["id"]], "parent_path": "Documents", "name": "bundle"
            })
            assert archive.status_code == 201
            extracted = await client.post(
                f"/api/files/{archive.json()['id']}/extract", json={"destination": "Desktop"}
            )
            assert extracted.status_code == 200
            assert extracted.json()["items"][0]["name"] == "source.txt"
            assert (await client.delete(f"/api/files/{created['id']}")).status_code == 204
            permanent = await client.delete(f"/api/files/{created['id']}/permanent")
            assert permanent.status_code == 204

    asyncio.run(scenario())
