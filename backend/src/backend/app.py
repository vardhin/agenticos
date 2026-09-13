from __future__ import annotations

import asyncio
import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .database import Database
from .benchmarks import evaluate_ten_action_benchmarks
from .desktop import DesktopEnvironment, build_desktop_registry
from .environment import Doer, ExecutionEngine, ExecutionLimits, TaskController
from .evaluation import EvaluationTracker, TaskMeasurement
from .filesystem import VirtualFilesystem
from .planning import AdaptivePolicy, PolicyCache, QLearner, TrainingConfig, assess_representation, search_plan
from .schemas import (
    ActionExecuteRequest,
    CommandCreate,
    CompileRequest,
    ContentUpdate,
    EventCreate,
    FileCreate,
    FileCopyRequest,
    FileUpdate,
    ArchiveRequest,
    ExtractRequest,
    StatePatch,
    StateUpdate,
)
from .compiler import AmbiguousReferenceError, CompileError, TaskCompiler
from .environment import ActionProposal as EnvironmentProposal
from .wifi import (
    ActionProposal,
    IntentError,
    SimulatedWifiAdapter,
    TaskRequest,
    WifiActionId,
    WifiOrchestrator,
    WifiTarget,
)


database = Database()
filesystem = VirtualFilesystem(database)
command_subscribers: set[asyncio.Queue[str]] = set()
wifi_adapter = SimulatedWifiAdapter()
wifi_orchestrator = WifiOrchestrator(wifi_adapter)
task_compiler = TaskCompiler()
desktop_registry = build_desktop_registry()
desktop_environment = DesktopEnvironment(desktop_registry)
desktop_doer = Doer(desktop_registry, desktop_environment)
desktop_tasks = TaskController()
policy_cache = PolicyCache(Path(__file__).resolve().parents[2] / "data" / "policies")
trained_policies: dict[str, Any] = {}
evaluation_tracker = EvaluationTracker()


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


@app.get("/api/wifi/state", tags=["wifi"])
async def get_wifi_state():
    return wifi_adapter.observe()


@app.get("/api/wifi/actions", tags=["wifi"])
async def get_wifi_actions():
    endpoints = {
        "wifi.enable": "/api/wifi/enable",
        "wifi.disable": "/api/wifi/disable",
        "wifi.scan": "/api/wifi/scan",
        "wifi.connect": "/api/wifi/connect",
        "wifi.disconnect": "/api/wifi/disconnect",
        "wifi.forget": "/api/wifi/forget",
        "wifi.test_internet": "/api/wifi/test-internet",
    }
    items = []
    for spec in wifi_orchestrator.doer.registry.discover():
        item = spec.model_dump(mode="json")
        # Preserve the v1 discovery fields while exposing the uniform v2 contract.
        item["expected_latency"] = item["latency"]
        item["endpoint"] = endpoints[spec.id]
        items.append(item)
    return {
        "environment_version": wifi_orchestrator.doer.registry.environment_version,
        "semantics_version": wifi_orchestrator.doer.registry.semantics_version,
        "items": items,
    }


@app.get("/api/actions", tags=["agent"])
async def get_actions():
    registry = desktop_registry
    return {
        "environment_version": registry.environment_version,
        "semantics_version": registry.semantics_version,
        "items": [spec.model_dump(mode="json") for spec in registry.discover()],
    }


@app.get("/api/environment/state", tags=["agent"])
async def get_environment_state():
    state = desktop_environment.observe()
    return {**state.model_dump(mode="json"), "state_hash": state.state_hash()}


@app.get("/api/desktop/state", tags=["agent"])
async def get_desktop_environment_state():
    state = desktop_environment.observe()
    return {**state.model_dump(mode="json"), "state_hash": state.state_hash()}


@app.post("/api/agent/compile", tags=["agent"])
async def compile_agent_task(value: CompileRequest):
    try:
        compiled = task_compiler.compile(value.command, value.references)
    except AmbiguousReferenceError as exc:
        raise HTTPException(
            409,
            detail={"type": "ambiguous_reference", "reference": exc.reference, "candidates": exc.candidates},
        ) from exc
    except CompileError as exc:
        raise HTTPException(422, detail={"type": "compile_error", "message": str(exc)}) from exc
    return {
        "source": compiled.source,
        "expression": compiled.expression.as_dict(),
        "parameters": compiled.parameters,
        "automaton": compiled.automaton.model_dump(mode="json") if compiled.automaton else None,
        "requires_fallback": compiled.requires_fallback,
    }


@app.post("/api/agent/preview", tags=["agent"])
async def preview_agent_task(value: CompileRequest):
    """Return interpreted milestones and safety constraints without taking action."""
    try:
        compiled = task_compiler.compile(value.command, value.references)
    except AmbiguousReferenceError as exc:
        raise HTTPException(
            409,
            detail={"type": "ambiguous_reference", "reference": exc.reference, "candidates": exc.candidates},
        ) from exc
    except CompileError as exc:
        raise HTTPException(422, detail={"type": "compile_error", "message": str(exc)}) from exc
    automaton = compiled.automaton
    return {
        "source": compiled.source,
        "expression": compiled.expression.as_dict(),
        "parameters": compiled.parameters,
        "supported": automaton is not None,
        "task_id": automaton.id if automaton else None,
        "milestones": [
            {
                "id": milestone.id,
                "description": milestone.goals[0].description or milestone.id.replace("-", " "),
                "mode": milestone.mode,
                "goals": [goal.model_dump(mode="json") for goal in milestone.goals],
            }
            for milestone in automaton.milestones
        ] if automaton else [],
        "constraints": automaton.constraints if automaton else {},
    }


@app.post("/api/actions/{action_id}/execute", tags=["agent"])
async def execute_registered_action(action_id: str, value: ActionExecuteRequest):
    result = desktop_doer.execute(
        EnvironmentProposal(action=action_id, args=value.args, confirmed=value.confirmed)
    )
    if result.status in {"failed", "confirmation_required"}:
        status_code = 428 if result.status == "confirmation_required" else 409
        raise HTTPException(status_code, detail=result.model_dump(mode="json"))
    return result


def execute_wifi_action(proposal: ActionProposal, *, confirmed: bool = False):
    result = wifi_orchestrator.doer.execute(proposal, confirmed=confirmed)
    if result.status == "failed":
        raise HTTPException(
            409,
            detail={"message": result.message, "state": result.observed_state.model_dump()},
        )
    return result


@app.post("/api/wifi/enable", tags=["wifi"])
async def enable_wifi():
    return execute_wifi_action(ActionProposal(action=WifiActionId.ENABLE))


@app.post("/api/wifi/disable", tags=["wifi"])
async def disable_wifi():
    return execute_wifi_action(ActionProposal(action=WifiActionId.DISABLE))


@app.post("/api/wifi/scan", tags=["wifi"])
async def scan_wifi():
    return execute_wifi_action(ActionProposal(action=WifiActionId.SCAN))


@app.post("/api/wifi/connect", tags=["wifi"])
async def connect_wifi(target: WifiTarget):
    return execute_wifi_action(ActionProposal(action=WifiActionId.CONNECT, args={"ssid": target.ssid}))


@app.post("/api/wifi/disconnect", tags=["wifi"])
async def disconnect_wifi():
    return execute_wifi_action(ActionProposal(action=WifiActionId.DISCONNECT))


@app.post("/api/wifi/forget", tags=["wifi"])
async def forget_wifi(target: WifiTarget, confirmed: bool = False):
    return execute_wifi_action(
        ActionProposal(action=WifiActionId.FORGET, args={"ssid": target.ssid}),
        confirmed=confirmed,
    )


@app.post("/api/wifi/test-internet", tags=["wifi"])
async def test_wifi_internet():
    return execute_wifi_action(ActionProposal(action=WifiActionId.TEST_INTERNET))


@app.post("/api/agent/tasks", tags=["agent"])
async def run_agent_task(task: TaskRequest):
    compiled = task_compiler.compile(task.command)
    if compiled.automaton is not None and not compiled.automaton.id.startswith("compiled-wifi-"):
        automaton = compiled.automaton
        desktop_doer.execute(EnvironmentProposal(action="system.begin_task", args={"task_id": automaton.id}))
        initial = desktop_environment.observe().fields

        started = time.monotonic()
        bfs = search_plan(desktop_registry, automaton, initial, algorithm="bfs", max_steps=30)
        bfs_ms = round((time.monotonic() - started) * 1000, 3)
        started = time.monotonic()
        astar = search_plan(desktop_registry, automaton, initial, algorithm="astar", max_steps=30)
        astar_ms = round((time.monotonic() - started) * 1000, 3)

        learner = QLearner(desktop_registry, policy_cache)
        stochastic_failures = automaton.constraints.get("stochastic_failures", {})
        training_episodes = 600 if stochastic_failures else 220
        cache_hits_before = policy_cache.hits
        trained = learner.train(
            automaton,
            initial,
            TrainingConfig(episodes=training_episodes, max_steps=40),
        )
        trained_policies[trained.cache_key] = trained
        adaptive = AdaptivePolicy(desktop_registry, trained)
        failures = automaton.constraints.get("inject_failures", {})
        desktop_environment.inject_failures(failures if isinstance(failures, dict) else {})
        result = ExecutionEngine(desktop_registry, desktop_doer, adaptive, desktop_tasks).run(
            automaton,
            ExecutionLimits(max_steps=40, timeout_seconds=30, max_state_visits=5),
        )
        cache_hit = policy_cache.hits > cache_hits_before
        succeeded_steps = sum(item.status == "succeeded" for item in result.executions)
        failures_observed = sum(item.status == "failed" for item in result.executions)
        simulator_divergences = sum(
            item.error_code == "verification_failed" for item in result.executions
        )
        evaluation_tracker.record(TaskMeasurement(
            task_id=automaton.id,
            status=result.status,
            training_ms=0 if cache_hit else trained.training_duration_ms,
            inference_ms=result.duration_ms,
            environment_steps=len(result.executions),
            unnecessary_actions=max(0, succeeded_steps - len(automaton.milestones)),
            recoveries=sum(item.phase == "recover" for item in result.timeline),
            failures=failures_observed,
            cache_hit=cache_hit,
            bfs_steps=len(bfs) if bfs else None,
            astar_steps=len(astar) if astar else None,
            rl_steps=succeeded_steps,
            live_simulator_divergences=simulator_divergences,
        ))
        return {
            "command": task.command,
            "goal": automaton.model_dump(mode="json"),
            "route": "q_learning",
            "plan": [
                {"action": item.action, "args": item.args}
                for item in result.executions
                if item.status == "succeeded"
            ],
            "executions": [item.model_dump(mode="json") for item in result.executions],
            "status": result.status,
            "final_state": result.final_state.model_dump(mode="json"),
            "error": result.error,
            "timeline": [item.model_dump(mode="json") for item in result.timeline],
            "duration_ms": result.duration_ms,
            "training": {
                "policy_version": trained.version,
                "cache_key": trained.cache_key,
                "episodes": len(trained.traces),
                "states": len(trained.q_table),
                "action_space": len(trained.action_space),
                "success_rate": sum(trace.succeeded for trace in trained.traces) / len(trained.traces),
                "recent_traces": [trace.model_dump(mode="json") for trace in trained.traces[-10:]],
                "training_time_ms": 0 if cache_hit else trained.training_duration_ms,
                "inference_time_ms": result.duration_ms,
                "cache_hit": cache_hit,
            },
            "baselines": {
                "bfs": {"steps": len(bfs) if bfs else None, "duration_ms": bfs_ms},
                "astar": {"steps": len(astar) if astar else None, "duration_ms": astar_ms},
            },
            "recovery": {
                "injected_failures": failures,
                "observed_failures": sum(item.status == "failed" for item in result.executions),
                "replans": adaptive.replans,
            },
        }
    try:
        return wifi_orchestrator.run(task.command)
    except IntentError as exc:
        raise HTTPException(422, detail={"message": str(exc), "route": "unsupported"}) from exc


@app.post("/api/agent/tasks/{task_id}/cancel", tags=["agent"])
async def cancel_agent_task(task_id: str):
    cancelled = desktop_tasks.cancel(task_id)
    action = desktop_doer.execute(EnvironmentProposal(action="system.cancel_task"))
    return {"task_id": task_id, "cancelled": cancelled, "action": action.model_dump(mode="json")}


@app.get("/api/agent/policies/{cache_key}", tags=["agent"])
async def inspect_policy(cache_key: str):
    policy = trained_policies.get(cache_key) or policy_cache.get(cache_key)
    if policy is None:
        raise HTTPException(404, "Policy not found")
    return policy.model_dump(mode="json")


@app.get("/api/agent/policies", tags=["agent"])
async def list_policies():
    policies = {**policy_cache._entries, **trained_policies}
    return {
        "items": [
            {
                "cache_key": item.cache_key,
                "version": item.version,
                "states": len(item.q_table),
                "episodes": len(item.traces),
                "action_space": len(item.action_space),
                "training_duration_ms": item.training_duration_ms,
            }
            for item in policies.values()
        ],
        "cache": {"hits": policy_cache.hits, "misses": policy_cache.misses},
    }


@app.get("/api/agent/metrics", tags=["agent"])
async def get_agent_metrics():
    return evaluation_tracker.snapshot()


@app.get("/api/agent/representation", tags=["agent"])
async def get_representation_assessment():
    observed_states = max((len(item.q_table) for item in trained_policies.values()), default=0)
    return assess_representation(
        desktop_environment.observe(), observed_q_states=observed_states
    )


@app.get("/api/agent/benchmarks", tags=["agent"])
async def get_agent_benchmarks():
    return await asyncio.to_thread(evaluate_ten_action_benchmarks)


@app.post("/api/agent/tasks/{task_id}/rollback", tags=["agent"])
async def rollback_agent_task(task_id: str):
    result = desktop_doer.execute(EnvironmentProposal(action="system.undo_last"))
    if result.status == "failed":
        raise HTTPException(409, detail=result.model_dump(mode="json"))
    return {"task_id": task_id, "result": result.model_dump(mode="json")}


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


@app.post("/api/files/{node_id}/copy", tags=["files"])
async def copy_file(node_id: int, value: FileCopyRequest) -> dict[str, Any]:
    return filesystem.copy(node_id, value.parent_path)


@app.delete("/api/files/{node_id}/permanent", status_code=204, tags=["files"])
async def permanently_delete_file(node_id: int) -> Response:
    filesystem.delete_permanently(node_id)
    return Response(status_code=204)


@app.delete("/api/files/trash/all", tags=["files"])
async def empty_file_trash() -> dict[str, int]:
    return {"deleted": filesystem.empty_trash()}


@app.post("/api/files/archive", status_code=201, tags=["files"])
async def create_archive(value: ArchiveRequest) -> dict[str, Any]:
    return filesystem.compress(value.node_ids, value.parent_path, value.name)


@app.post("/api/files/{node_id}/extract", tags=["files"])
async def extract_archive(node_id: int, value: ExtractRequest) -> dict[str, Any]:
    return {"items": filesystem.extract(node_id, value.destination)}


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
