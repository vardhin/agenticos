import asyncio
from collections import Counter

import httpx

from backend.app import app, desktop_environment
from backend.desktop import desktop_initial_fields


RECOVERY_PROMPT = (
    "Connect to StudioNet, verify internet access, open the browser, visit the project page, "
    "copy its address, make a note from it, save it as online, move it to Research, and star it."
)
CROSS_WORKSPACE_PROMPT = (
    "Open workspace two, launch Files, find hero, copy its contents, switch to workspace one, "
    "open the editor, create a document, paste it, save it as hero-copy, and close it."
)
SETTINGS_EVIDENCE_PROMPT = (
    "Turn on dark mode, set brightness to 60%, enable Do Not Disturb, take a screenshot, "
    "save it as setup, open Files, find setup, move it to Pictures, star it, and return to the desktop."
)


def test_desktop_action_api_exposes_the_complete_registered_tree() -> None:
    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/actions")
            assert response.status_code == 200
            payload = response.json()
            actions = payload["items"]

            assert payload["environment_version"] == "agentos-desktop-v1"
            assert len(actions) == 172
            assert len({item["id"] for item in actions}) == len(actions)
            assert Counter(item["id"].split(".")[0] for item in actions) == {
                "application": 6,
                "audio": 7,
                "bluetooth": 7,
                "browser": 12,
                "capture": 7,
                "clipboard": 9,
                "display": 7,
                "editor": 15,
                "filesystem": 23,
                "launcher": 8,
                "notification": 6,
                "open_with": 1,
                "search": 5,
                "settings": 5,
                "share": 2,
                "software": 7,
                "system": 11,
                "terminal": 7,
                "wifi": 10,
                "window": 11,
                "workspace": 6,
            }
            assert all(item["binding"]["simulator"] == "generated" for item in actions)
            assert all(item["binding"]["live"] == "frontend-runtime" for item in actions)
            assert all(
                {effect["field"] for effect in item["effects"]}
                <= set(item["affected_fields"])
                for item in actions
            )

    asyncio.run(scenario())


def test_desktop_observation_has_stable_ids_for_addressable_resources() -> None:
    fields = desktop_initial_fields()

    assert fields["application"]["ids"]
    assert fields["window"]["ids"]
    assert fields["workspace"]["ids"]
    assert fields["filesystem"]["ids"]
    assert fields["bluetooth"]["device_ids"]
    assert fields["wifi"]["ids"]
    assert fields["browser"]["tab_ids"]
    assert fields["notification"]["ids"]
    assert fields["wifi"]["id_by_ssid"]["StudioNet"] == "network:studio-net"


def test_desktop_agent_endpoint_trains_executes_and_reports_recovery() -> None:
    desktop_environment.reset()

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/agent/tasks", json={"command": RECOVERY_PROMPT})
            assert response.status_code == 200
            result = response.json()

            assert result["route"] == "q_learning"
            assert result["status"] == "succeeded"
            assert result["baselines"]["astar"]["steps"] == 10
            assert result["training"]["success_rate"] >= 0.98
            assert result["recovery"] == {
                "injected_failures": {"wifi.connect": 1},
                "observed_failures": 1,
                "replans": 0,
            }
            assert [
                (execution["action"], execution["status"])
                for execution in result["executions"][:2]
            ] == [
                ("wifi.connect", "failed"),
                ("wifi.connect", "succeeded"),
            ]
            assert result["final_state"]["fields"]["task"]["last_failure"] == {
                "action": "wifi.connect",
                "code": "action_failed",
                "recoverable": True,
            }

            policy = await client.get(
                f"/api/agent/policies/{result['training']['cache_key']}"
            )
            assert policy.status_code == 200
            assert policy.json()["q_table"]

    try:
        asyncio.run(scenario())
    finally:
        desktop_environment.reset()


def test_desktop_agent_endpoint_executes_cross_workspace_writing() -> None:
    desktop_environment.reset()

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/agent/tasks",
                json={"command": CROSS_WORKSPACE_PROMPT},
            )
            assert response.status_code == 200
            result = response.json()

            assert result["route"] == "q_learning"
            assert result["status"] == "succeeded"
            assert result["baselines"]["astar"]["steps"] == 10
            assert result["training"]["success_rate"] == 1
            assert [item["action"] for item in result["plan"]] == [
                "workspace.switch",
                "application.launch",
                "filesystem.search",
                "filesystem.read",
                "workspace.switch",
                "editor.open",
                "editor.new_document",
                "editor.paste_content",
                "editor.save_as",
                "editor.close_document",
            ]
            fields = result["final_state"]["fields"]
            assert fields["workspace"]["current"] == 1
            assert fields["editor"]["filename"] == "hero-copy"
            assert fields["editor"]["document_open"] is False

    try:
        asyncio.run(scenario())
    finally:
        desktop_environment.reset()


def test_desktop_agent_endpoint_executes_settings_evidence_task() -> None:
    desktop_environment.reset()

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/agent/tasks",
                json={"command": SETTINGS_EVIDENCE_PROMPT},
            )
            assert response.status_code == 200
            result = response.json()

            assert result["route"] == "q_learning"
            assert result["status"] == "succeeded"
            assert result["baselines"]["astar"]["steps"] == 10
            assert result["training"]["success_rate"] == 1
            assert [item["action"] for item in result["plan"]] == [
                "display.set_theme",
                "display.set_brightness",
                "notification.set_dnd",
                "capture.fullscreen",
                "capture.save",
                "application.launch",
                "filesystem.search",
                "filesystem.move",
                "filesystem.star",
                "system.show_desktop",
            ]
            fields = result["final_state"]["fields"]
            assert fields["display"]["theme"] == "dark"
            assert fields["display"]["brightness"] == 60
            assert fields["notification"]["dnd"] is True
            assert fields["capture"]["saved_name"] == "setup"
            assert fields["filesystem"]["last_parent"] == "Pictures"
            assert fields["filesystem"]["starred"] is True
            assert fields["task"]["desktop_returned"] is True

    try:
        asyncio.run(scenario())
    finally:
        desktop_environment.reset()
