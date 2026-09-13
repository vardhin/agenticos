from __future__ import annotations

import re
from collections.abc import Mapping
from threading import RLock
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from .environment import (
    ActionProposal as GenericProposal,
    ActionRegistry,
    ActionSpec,
    ArgumentSpec,
    BindingSpec,
    Condition,
    Doer,
    Effect,
    FactoredState,
    JsonValue,
    Latency,
    Risk,
)


class WifiActionId:
    ENABLE = "wifi.enable"
    DISABLE = "wifi.disable"
    SCAN = "wifi.scan"
    CONNECT = "wifi.connect"
    DISCONNECT = "wifi.disconnect"
    FORGET = "wifi.forget"
    TEST_INTERNET = "wifi.test_internet"


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


class ActionProposal(BaseModel):
    action: str
    args: dict[str, Any] = Field(default_factory=dict)


class ActionResult(BaseModel):
    action: str
    args: dict[str, Any]
    status: Literal["succeeded", "failed"]
    message: str
    observed_state: WifiState
    verified: bool = False
    state_diff: list[dict[str, Any]] = Field(default_factory=list)


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
    environment_version = "agentos-wifi-v2"

    def __init__(self) -> None:
        self._lock = RLock()
        self._available = {
            "StudioNet": NetworkState(ssid="StudioNet", signal_strength=92, known=True),
            "PineHouse": NetworkState(ssid="PineHouse", signal_strength=73, known=True),
            "Guest": NetworkState(ssid="Guest", signal_strength=48, known=False),
        }
        self._revision = 0
        self.reset()

    def reset(self, *, enabled: bool = False, ssid: str | None = None) -> WifiState:
        with self._lock:
            self._enabled = enabled or ssid is not None
            self._ssid = ssid
            self._known_networks = {"StudioNet", "PineHouse"}
            self._visible_networks: dict[str, NetworkState] = {}
            self._revision += 1
            return self.observe()

    def observe(self) -> WifiState:
        with self._lock:
            return WifiState(
                enabled=self._enabled,
                connected=self._ssid is not None,
                ssid=self._ssid,
                known_networks=sorted(self._known_networks),
                visible_networks=[item.model_copy() for item in self._visible_networks.values()],
                internet_available=self._ssid is not None,
            )

    def observe_environment(self) -> FactoredState:
        state = self.observe()
        return FactoredState(
            environment_version=self.environment_version,
            revision=self._revision,
            fields={"wifi": {
                "enabled": state.enabled,
                "connected": state.connected,
                "ssid": state.ssid,
                "known_networks": state.known_networks,
                "visible_ssids": [item.ssid for item in state.visible_networks],
                "internet_available": state.internet_available,
            }},
        )

    def execute(self, action_id: str, args: Mapping[str, JsonValue]) -> str:
        with self._lock:
            ssid = str(args.get("ssid", "")).strip()
            if action_id == WifiActionId.ENABLE:
                self._enabled = True
                message = "Wi-Fi enabled"
            elif action_id == WifiActionId.DISABLE:
                self._enabled, self._ssid, self._visible_networks = False, None, {}
                message = "Wi-Fi disabled"
            elif action_id == WifiActionId.SCAN:
                self._visible_networks = {
                    name: item.model_copy(update={"known": name in self._known_networks})
                    for name, item in self._available.items()
                }
                message = f"Found {len(self._visible_networks)} networks"
            elif action_id == WifiActionId.CONNECT:
                if ssid not in self._visible_networks:
                    raise WifiOperationError(f"Network not found: {ssid}")
                self._ssid = ssid
                self._known_networks.add(ssid)
                message = f"Connected to {ssid}"
            elif action_id == WifiActionId.DISCONNECT:
                self._ssid = None
                message = "Wi-Fi disconnected"
            elif action_id == WifiActionId.FORGET:
                self._known_networks.discard(ssid)
                if self._ssid == ssid:
                    self._ssid = None
                message = f"Forgot {ssid}"
            elif action_id == WifiActionId.TEST_INTERNET:
                if self._ssid is None:
                    raise WifiOperationError("No internet connection")
                message = "Internet connection verified"
            else:
                raise WifiOperationError(f"Unsupported Wi-Fi action: {action_id}")
            self._revision += 1
            return message


class WifiBinding:
    def __init__(self, adapter: SimulatedWifiAdapter) -> None:
        self.adapter = adapter

    def observe(self) -> FactoredState:
        return self.adapter.observe_environment()

    def execute(self, action_id: str, args: Mapping[str, JsonValue]) -> str:
        return self.adapter.execute(action_id, args)


def cond(field: str, operator: str = "eq", value: JsonValue = None, arg: str | None = None) -> Condition:
    return Condition(field=field, operator=operator, value=value, value_from_argument=arg)  # type: ignore[arg-type]


def effect(field: str, operation: str = "set", value: JsonValue = None, arg: str | None = None) -> Effect:
    return Effect(field=field, operation=operation, value=value, value_from_argument=arg)  # type: ignore[arg-type]


def build_action_registry(adapter: SimulatedWifiAdapter) -> ActionRegistry:
    registry = ActionRegistry(adapter.environment_version)
    binding = BindingSpec(simulator="generated", live="simulated-wifi")
    specs = [
        ActionSpec(id="wifi.enable", description="Enable Wi-Fi",
                   effects=[effect("wifi.enabled", value=True)],
                   postconditions=[cond("wifi.enabled", value=True)], cost=1, binding=binding),
        ActionSpec(id="wifi.disable", description="Disable Wi-Fi",
                   preconditions=[cond("wifi.enabled", value=True)],
                   effects=[effect("wifi.enabled", value=False), effect("wifi.connected", value=False), effect("wifi.ssid", "clear"), effect("wifi.visible_ssids", value=[]), effect("wifi.internet_available", value=False)],
                   postconditions=[cond("wifi.enabled", value=False), cond("wifi.connected", value=False)],
                   affected_fields=["wifi.enabled", "wifi.connected", "wifi.ssid", "wifi.visible_ssids", "wifi.internet_available"], cost=3, binding=binding),
        ActionSpec(id="wifi.scan", description="Refresh visible networks",
                   preconditions=[cond("wifi.enabled", value=True)],
                   effects=[effect("wifi.visible_ssids", value=list(adapter._available))],
                   postconditions=[cond("wifi.visible_ssids", "exists")], cost=1, latency=Latency.MEDIUM, binding=binding),
        ActionSpec(id="wifi.connect", description="Connect to a visible network",
                   arguments={"ssid": ArgumentSpec(type="string")},
                   preconditions=[cond("wifi.enabled", value=True), cond("wifi.visible_ssids", "contains", arg="ssid")],
                   effects=[effect("wifi.connected", value=True), effect("wifi.ssid", arg="ssid"), effect("wifi.known_networks", "add", arg="ssid"), effect("wifi.internet_available", value=True)],
                   postconditions=[cond("wifi.connected", value=True), cond("wifi.ssid", arg="ssid")],
                   cost=2, latency=Latency.MEDIUM, binding=binding),
        ActionSpec(id="wifi.disconnect", description="Disconnect from Wi-Fi",
                   preconditions=[cond("wifi.connected", value=True)],
                   effects=[effect("wifi.connected", value=False), effect("wifi.ssid", "clear"), effect("wifi.internet_available", value=False)],
                   postconditions=[cond("wifi.connected", value=False)], cost=1, binding=binding),
        ActionSpec(id="wifi.forget", description="Forget a saved network",
                   arguments={"ssid": ArgumentSpec(type="string")},
                   preconditions=[cond("wifi.known_networks", "contains", arg="ssid")],
                   effects=[effect("wifi.known_networks", "remove", arg="ssid")],
                   postconditions=[cond("wifi.known_networks", "not_contains", arg="ssid")],
                   affected_fields=["wifi.known_networks", "wifi.connected", "wifi.ssid"], cost=10,
                   risk=Risk.MEDIUM, reversible=False, confirmation_required=True, binding=binding),
        ActionSpec(id="wifi.test_internet", description="Verify internet access",
                   preconditions=[cond("wifi.connected", value=True)],
                   postconditions=[cond("wifi.internet_available", value=True)],
                   latency=Latency.MEDIUM, binding=binding),
    ]
    for spec in specs:
        registry.register(spec)
    return registry


class WifiDoer:
    def __init__(self, adapter: SimulatedWifiAdapter) -> None:
        self.adapter = adapter
        self.registry = build_action_registry(adapter)
        self.generic = Doer(self.registry, WifiBinding(adapter))

    def execute(self, proposal: ActionProposal, *, confirmed: bool = False) -> ActionResult:
        result = self.generic.execute(GenericProposal(action=proposal.action, args=proposal.args, confirmed=confirmed))
        message = result.message
        if proposal.action == WifiActionId.CONNECT and result.error_code == "invalid_proposal":
            if "visible_ssids" in message:
                message = f"Network not found: {proposal.args.get('ssid', '')}"
        return ActionResult(
            action=result.action, args=result.args,
            status="succeeded" if result.status == "succeeded" else "failed",
            message=message, observed_state=self.adapter.observe(), verified=result.verified,
            state_diff=[change.model_dump(mode="json") for change in result.state_diff],
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
        if not any(item.ssid == goal.ssid for item in state.visible_networks):
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
    """Compatibility facade over the shared observe/propose/validate/act/verify contract."""

    def __init__(self, adapter: SimulatedWifiAdapter) -> None:
        self.adapter = adapter
        self.compiler = WifiCommandCompiler()
        self.planner = WifiPlanner()
        self.doer = WifiDoer(adapter)
        self._task_lock = RLock()

    def run(self, command: str) -> TaskResult:
        with self._task_lock:
            goal = self.compiler.compile(command)
            plan = self.planner.plan(self.adapter.observe(), goal)
            executions: list[ActionResult] = []
            for proposal in plan:
                result = self.doer.execute(proposal)
                executions.append(result)
                if result.status == "failed":
                    return TaskResult(command=command, goal=goal, plan=plan, executions=executions,
                                      status="failed", final_state=result.observed_state, error=result.message)
                if goal.is_satisfied_by(result.observed_state):
                    break
            final_state = self.adapter.observe()
            succeeded = goal.is_satisfied_by(final_state)
            return TaskResult(command=command, goal=goal, plan=plan, executions=executions,
                              status="succeeded" if succeeded else "failed", final_state=final_state,
                              error=None if succeeded else "Plan completed without satisfying the goal")
