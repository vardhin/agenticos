from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from threading import RLock
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class WifiActionId(StrEnum):
    ENABLE = "wifi.enable"
    DISABLE = "wifi.disable"
    SCAN = "wifi.scan"
    CONNECT = "wifi.connect"
    DISCONNECT = "wifi.disconnect"
    FORGET = "wifi.forget"


class NetworkState(BaseModel):
    ssid: str
    signal_strength: int = Field(ge=0, le=100)
    known: bool = False


class WifiState(BaseModel):
    enabled: bool = False
    connected: bool = False
    ssid: str | None = None
    known_networks: list[str] = Field(default_factory=list)
    visible_networks: list[NetworkState] = Field(default_factory=list)
    internet_available: bool = False


class WifiGoal(BaseModel):
    type: Literal["wifi_enabled", "wifi_disabled", "connected", "disconnected"]
    ssid: str | None = None

    @model_validator(mode="after")
    def validate_ssid(self) -> WifiGoal:
        if self.type == "connected" and not self.ssid:
            raise ValueError("ssid is required for a connected goal")
        if self.type != "connected" and self.ssid is not None:
            raise ValueError("ssid is only valid for a connected goal")
        return self

    def is_satisfied_by(self, state: WifiState) -> bool:
        if self.type == "wifi_enabled":
            return state.enabled
        if self.type == "wifi_disabled":
            return not state.enabled
        if self.type == "disconnected":
            return not state.connected
        return state.enabled and state.connected and state.ssid == self.ssid


class ActionSpec(BaseModel):
    id: WifiActionId
    preconditions: list[str]
    effects: list[str]
    cost: int = Field(ge=0)
    risk: Literal["low", "medium", "high"]
    reversible: bool
    confirmation_required: bool = False
    expected_latency: Literal["low", "medium", "high"]
    endpoint: str


class ActionProposal(BaseModel):
    action: WifiActionId
    args: dict[str, Any] = Field(default_factory=dict)


class ActionResult(BaseModel):
    action: WifiActionId
    args: dict[str, Any]
    status: Literal["succeeded", "failed"]
    message: str
    observed_state: WifiState


class TaskRequest(BaseModel):
    command: str = Field(min_length=1, max_length=500)


class TaskResult(BaseModel):
    command: str
    goal: WifiGoal
    route: Literal["deterministic"] = "deterministic"
    plan: list[ActionProposal]
    executions: list[ActionResult]
    status: Literal["succeeded", "failed"]
    final_state: WifiState
    error: str | None = None


class WifiTarget(BaseModel):
    ssid: str = Field(min_length=1, max_length=128)


class WifiOperationError(RuntimeError):
    pass


class IntentError(ValueError):
    pass


class SimulatedWifiAdapter:
    """Deterministic semantic Wi-Fi environment used by the prototype."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._available = {
            "StudioNet": NetworkState(ssid="StudioNet", signal_strength=92, known=True),
            "PineHouse": NetworkState(ssid="PineHouse", signal_strength=73, known=True),
            "Guest": NetworkState(ssid="Guest", signal_strength=48, known=False),
        }
        self.reset()

    def reset(self, *, enabled: bool = False, ssid: str | None = None) -> WifiState:
        with self._lock:
            self._enabled = enabled or ssid is not None
            self._ssid = ssid
            self._known_networks = {"StudioNet", "PineHouse"}
            self._visible_networks: dict[str, NetworkState] = {}
            return self.observe()

    def observe(self) -> WifiState:
        with self._lock:
            return WifiState(
                enabled=self._enabled,
                connected=self._ssid is not None,
                ssid=self._ssid,
                known_networks=sorted(self._known_networks),
                visible_networks=[network.model_copy() for network in self._visible_networks.values()],
                internet_available=self._ssid is not None,
            )

    def enable(self, _: dict[str, Any]) -> str:
        with self._lock:
            self._enabled = True
        return "Wi-Fi enabled"

    def disable(self, _: dict[str, Any]) -> str:
        with self._lock:
            self._enabled = False
            self._ssid = None
            self._visible_networks = {}
        return "Wi-Fi disabled"

    def scan(self, _: dict[str, Any]) -> str:
        with self._lock:
            self._visible_networks = {
                ssid: network.model_copy(update={"known": ssid in self._known_networks})
                for ssid, network in self._available.items()
            }
        return f"Found {len(self._visible_networks)} networks"

    def connect(self, args: dict[str, Any]) -> str:
        ssid = str(args.get("ssid", "")).strip()
        with self._lock:
            if ssid not in self._visible_networks:
                raise WifiOperationError(f"Network not found: {ssid}")
            self._ssid = ssid
            self._known_networks.add(ssid)
        return f"Connected to {ssid}"

    def disconnect(self, _: dict[str, Any]) -> str:
        with self._lock:
            self._ssid = None
        return "Wi-Fi disconnected"

    def forget(self, args: dict[str, Any]) -> str:
        ssid = str(args.get("ssid", "")).strip()
        with self._lock:
            self._known_networks.discard(ssid)
            if self._ssid == ssid:
                self._ssid = None
        return f"Forgot {ssid}"


Precondition = Callable[[WifiState, dict[str, Any]], str | None]
Handler = Callable[[dict[str, Any]], str]


@dataclass(frozen=True)
class RegisteredAction:
    spec: ActionSpec
    precondition: Precondition
    handler: Handler


def _allowed(_: WifiState, __: dict[str, Any]) -> str | None:
    return None


def _requires_enabled(state: WifiState, _: dict[str, Any]) -> str | None:
    return None if state.enabled else "Wi-Fi must be enabled"


def _requires_connection(state: WifiState, _: dict[str, Any]) -> str | None:
    return None if state.connected else "Wi-Fi is already disconnected"


def _requires_known_network(state: WifiState, args: dict[str, Any]) -> str | None:
    ssid = str(args.get("ssid", "")).strip()
    if not ssid:
        return "ssid is required"
    return None if ssid in state.known_networks else f"Network is not known: {ssid}"


def _requires_visible_network(state: WifiState, args: dict[str, Any]) -> str | None:
    ssid = str(args.get("ssid", "")).strip()
    if not ssid:
        return "ssid is required"
    if not state.enabled:
        return "Wi-Fi must be enabled"
    return None if any(network.ssid == ssid for network in state.visible_networks) else f"Network not found: {ssid}"


def build_action_registry(adapter: SimulatedWifiAdapter) -> dict[WifiActionId, RegisteredAction]:
    definitions = [
        (WifiActionId.ENABLE, [], ["enabled = true"], 1, "low", True, False, "low", "/api/wifi/enable", _allowed, adapter.enable),
        (WifiActionId.DISABLE, ["enabled = true"], ["enabled = false", "connected = false"], 3, "low", True, False, "low", "/api/wifi/disable", _requires_enabled, adapter.disable),
        (WifiActionId.SCAN, ["enabled = true"], ["visible_networks refreshed"], 1, "low", True, False, "medium", "/api/wifi/scan", _requires_enabled, adapter.scan),
        (WifiActionId.CONNECT, ["enabled = true", "ssid in visible_networks"], ["connected = true", "ssid = argument"], 2, "low", True, False, "medium", "/api/wifi/connect", _requires_visible_network, adapter.connect),
        (WifiActionId.DISCONNECT, ["connected = true"], ["connected = false", "ssid = null"], 1, "low", True, False, "low", "/api/wifi/disconnect", _requires_connection, adapter.disconnect),
        (WifiActionId.FORGET, ["ssid in known_networks"], ["ssid removed from known_networks"], 10, "medium", False, True, "low", "/api/wifi/forget", _requires_known_network, adapter.forget),
    ]
    return {
        action_id: RegisteredAction(
            spec=ActionSpec(
                id=action_id,
                preconditions=preconditions,
                effects=effects,
                cost=cost,
                risk=risk,
                reversible=reversible,
                confirmation_required=confirmation,
                expected_latency=latency,
                endpoint=endpoint,
            ),
            precondition=precondition,
            handler=handler,
        )
        for action_id, preconditions, effects, cost, risk, reversible, confirmation, latency, endpoint, precondition, handler in definitions
    }


class WifiDoer:
    def __init__(self, adapter: SimulatedWifiAdapter) -> None:
        self.adapter = adapter
        self.registry = build_action_registry(adapter)

    def execute(self, proposal: ActionProposal, *, confirmed: bool = False) -> ActionResult:
        registered = self.registry[proposal.action]
        state = self.adapter.observe()
        error = registered.precondition(state, proposal.args)
        if registered.spec.confirmation_required and not confirmed:
            error = "Action requires confirmation"
        if error:
            return ActionResult(
                action=proposal.action,
                args=proposal.args,
                status="failed",
                message=error,
                observed_state=state,
            )
        try:
            message = registered.handler(proposal.args)
            status: Literal["succeeded", "failed"] = "succeeded"
        except WifiOperationError as exc:
            message = str(exc)
            status = "failed"
        return ActionResult(
            action=proposal.action,
            args=proposal.args,
            status=status,
            message=message,
            observed_state=self.adapter.observe(),
        )


class WifiPlanner:
    def plan(self, state: WifiState, goal: WifiGoal) -> list[ActionProposal]:
        if goal.is_satisfied_by(state):
            return []
        if goal.type == "wifi_enabled":
            return [ActionProposal(action=WifiActionId.ENABLE)]
        if goal.type == "wifi_disabled":
            return [ActionProposal(action=WifiActionId.DISABLE)]
        if goal.type == "disconnected":
            return [ActionProposal(action=WifiActionId.DISCONNECT)]

        assert goal.ssid is not None
        actions: list[ActionProposal] = []
        if not state.enabled:
            actions.append(ActionProposal(action=WifiActionId.ENABLE))
        if not any(network.ssid == goal.ssid for network in state.visible_networks):
            actions.append(ActionProposal(action=WifiActionId.SCAN))
        actions.append(ActionProposal(action=WifiActionId.CONNECT, args={"ssid": goal.ssid}))
        return actions


class WifiCommandCompiler:
    _connect = re.compile(r"^connect(?:\s+to)?\s+(.+?)$", re.IGNORECASE)

    def compile(self, command: str) -> WifiGoal:
        normalized = " ".join(command.strip().split())
        lowered = normalized.casefold()
        if lowered in {"wifi on", "on wifi", "enable wifi", "turn wifi on", "turn on wifi"}:
            return WifiGoal(type="wifi_enabled")
        if lowered in {"wifi off", "disable wifi", "turn wifi off"}:
            return WifiGoal(type="wifi_disabled")
        if lowered in {"disconnect wifi", "wifi disconnect", "disconnect from wifi"}:
            return WifiGoal(type="disconnected")
        match = self._connect.fullmatch(normalized)
        if match:
            ssid = match.group(1).strip()
            if ssid.casefold() in {"best", "the best network", "best network"}:
                raise IntentError("'connect best' requires the contextual-bandit route, which is not implemented")
            return WifiGoal(type="connected", ssid=ssid)
        raise IntentError(f"Unsupported command: {command}")


class WifiOrchestrator:
    def __init__(self, adapter: SimulatedWifiAdapter) -> None:
        self.adapter = adapter
        self.compiler = WifiCommandCompiler()
        self.planner = WifiPlanner()
        self.doer = WifiDoer(adapter)
        self._task_lock = RLock()

    def run(self, command: str) -> TaskResult:
        # One task owns the observe-plan-act loop at a time. Without this boundary,
        # concurrent requests could invalidate each other's plans between actions.
        with self._task_lock:
            goal = self.compiler.compile(command)
            initial_state = self.adapter.observe()
            plan = self.planner.plan(initial_state, goal)
            executions: list[ActionResult] = []

            for proposal in plan:
                result = self.doer.execute(proposal)
                executions.append(result)
                if result.status == "failed":
                    return TaskResult(
                        command=command,
                        goal=goal,
                        plan=plan,
                        executions=executions,
                        status="failed",
                        final_state=result.observed_state,
                        error=result.message,
                    )
                if goal.is_satisfied_by(result.observed_state):
                    break

            final_state = self.adapter.observe()
            succeeded = goal.is_satisfied_by(final_state)
            return TaskResult(
                command=command,
                goal=goal,
                plan=plan,
                executions=executions,
                status="succeeded" if succeeded else "failed",
                final_state=final_state,
                error=None if succeeded else "Plan completed without satisfying the goal",
            )
