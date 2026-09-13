import asyncio

import httpx

from backend.app import app, wifi_adapter


def test_wifi_goal_is_idempotent() -> None:
    wifi_adapter.reset(enabled=True)

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/agent/tasks", json={"command": "on wifi"})
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "succeeded"
            assert result["goal"] == {"type": "wifi_enabled", "ssid": None}
            assert result["plan"] == []
            assert result["executions"] == []

    asyncio.run(scenario())


def test_connect_compiles_plans_executes_and_verifies() -> None:
    wifi_adapter.reset()

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/agent/tasks",
                json={"command": "connect StudioNet"},
            )
            assert response.status_code == 200
            result = response.json()
            assert result["route"] == "deterministic"
            assert [step["action"] for step in result["plan"]] == [
                "wifi.enable",
                "wifi.scan",
                "wifi.connect",
            ]
            assert [step["status"] for step in result["executions"]] == [
                "succeeded",
                "succeeded",
                "succeeded",
            ]
            assert result["status"] == "succeeded"
            assert result["final_state"]["connected"] is True
            assert result["final_state"]["ssid"] == "StudioNet"
            assert result["final_state"]["internet_available"] is True

    asyncio.run(scenario())


def test_unknown_network_returns_structured_execution_failure() -> None:
    wifi_adapter.reset()

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/agent/tasks",
                json={"command": "connect MissingNet"},
            )
            assert response.status_code == 200
            result = response.json()
            assert result["status"] == "failed"
            assert result["executions"][-1]["action"] == "wifi.connect"
            assert result["executions"][-1]["status"] == "failed"
            assert result["error"] == "Network not found: MissingNet"
            assert result["final_state"]["connected"] is False

    asyncio.run(scenario())


def test_disconnect_uses_least_cost_action() -> None:
    wifi_adapter.reset(ssid="StudioNet")

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            result = (
                await client.post("/api/agent/tasks", json={"command": "disconnect wifi"})
            ).json()
            assert [step["action"] for step in result["plan"]] == ["wifi.disconnect"]
            assert result["final_state"]["enabled"] is True
            assert result["final_state"]["connected"] is False
            assert "StudioNet" in result["final_state"]["known_networks"]

    asyncio.run(scenario())


def test_action_contract_and_confirmation_boundary() -> None:
    wifi_adapter.reset(enabled=True)

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            actions = (await client.get("/api/wifi/actions")).json()["items"]
            forget = next(action for action in actions if action["id"] == "wifi.forget")
            assert forget["cost"] == 10
            assert forget["risk"] == "medium"
            assert forget["reversible"] is False
            assert forget["confirmation_required"] is True
            assert forget["endpoint"] == "/api/wifi/forget"

            denied = await client.post("/api/wifi/forget", json={"ssid": "StudioNet"})
            assert denied.status_code == 409
            assert denied.json()["detail"]["message"] == "Action requires confirmation"

            confirmed = await client.post(
                "/api/wifi/forget?confirmed=true",
                json={"ssid": "StudioNet"},
            )
            assert confirmed.status_code == 200
            state = (await client.get("/api/wifi/state")).json()
            assert "StudioNet" not in state["known_networks"]

    asyncio.run(scenario())


def test_unsupported_command_stops_before_execution() -> None:
    wifi_adapter.reset()

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/agent/tasks",
                json={"command": "connect best"},
            )
            assert response.status_code == 422
            detail = response.json()["detail"]
            assert detail["route"] == "unsupported"
            assert "contextual-bandit" in detail["message"]
            assert wifi_adapter.observe().enabled is False

    asyncio.run(scenario())


def test_uniform_registry_state_compile_and_execute_endpoints() -> None:
    wifi_adapter.reset()

    async def scenario() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            actions = (await client.get("/api/actions")).json()
            assert actions["environment_version"] == "agentos-wifi-v2"
            assert len(actions["semantics_version"]) == 16
            assert "wifi.enable" in [item["id"] for item in actions["items"]]

            observed = (await client.get("/api/environment/state")).json()
            assert observed["fields"]["wifi"]["enabled"] is False
            assert len(observed["state_hash"]) == 64

            compiled = await client.post(
                "/api/agent/compile", json={"command": "connect to StudioNet"}
            )
            assert compiled.status_code == 200
            assert compiled.json()["automaton"]["milestones"][0]["goals"][0]["predicate"]["field"] == "wifi.ssid"

            enabled = await client.post("/api/actions/wifi.enable/execute", json={})
            assert enabled.status_code == 200
            assert enabled.json()["verified"] is True
            assert enabled.json()["state_diff"][0]["field"] == "wifi.enabled"

            denied = await client.post(
                "/api/actions/wifi.forget/execute", json={"args": {"ssid": "StudioNet"}}
            )
            assert denied.status_code == 428

    asyncio.run(scenario())
