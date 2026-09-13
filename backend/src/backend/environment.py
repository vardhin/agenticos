from __future__ import annotations

import hashlib
import json
import random
import time
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from threading import Event, RLock
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, model_validator


# JSON-compatible values are validated by action argument schemas. Keeping the
# storage annotation non-recursive avoids Python 3.13/Pydantic schema recursion.
JsonValue = Any


class Risk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Latency(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ArgumentSpec(BaseModel):
    type: Literal["string", "integer", "number", "boolean", "array", "object"]
    required: bool = True
    description: str = ""


class Condition(BaseModel):
    field: str
    operator: Literal["eq", "neq", "contains", "not_contains", "truthy", "falsy", "exists"] = "eq"
    value: JsonValue = None
    value_from_argument: str | None = None


class Effect(BaseModel):
    field: str
    operation: Literal["set", "add", "remove", "clear"] = "set"
    value: JsonValue = None
    value_from_argument: str | None = None


class BindingSpec(BaseModel):
    simulator: str
    live: str | None = None


class ActionSpec(BaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
    description: str
    arguments: dict[str, ArgumentSpec] = Field(default_factory=dict)
    preconditions: list[Condition] = Field(default_factory=list)
    postconditions: list[Condition] = Field(default_factory=list)
    effects: list[Effect] = Field(default_factory=list)
    affected_fields: list[str] = Field(default_factory=list)
    cost: float = Field(default=1, ge=0)
    latency: Latency = Latency.LOW
    risk: Risk = Risk.LOW
    reversible: bool = True
    confirmation_required: bool = False
    binding: BindingSpec

    @model_validator(mode="after")
    def derive_and_validate_fields(self) -> ActionSpec:
        effect_fields = list(dict.fromkeys(effect.field for effect in self.effects))
        if not self.affected_fields:
            self.affected_fields = effect_fields
        elif not set(effect_fields).issubset(self.affected_fields):
            raise ValueError("affected_fields must include every effect field")
        if self.risk == Risk.HIGH or not self.reversible:
            self.confirmation_required = True
        return self


class FactoredState(BaseModel):
    environment_version: str
    revision: int = Field(default=0, ge=0)
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    fields: dict[str, JsonValue] = Field(default_factory=dict)
    unknown_fields: set[str] = Field(default_factory=set)
    working_memory: dict[str, JsonValue] = Field(default_factory=dict)

    def value(self, path: str) -> JsonValue:
        if any(path == unknown or path.startswith(f"{unknown}.") for unknown in self.unknown_fields):
            raise KeyError(path)
        current: Any = self.fields
        for part in path.split("."):
            if not isinstance(current, Mapping) or part not in current:
                raise KeyError(path)
            current = current[part]
        return current

    def canonical(self) -> str:
        payload = {
            "environment_version": self.environment_version,
            "fields": self.fields,
            "unknown_fields": sorted(self.unknown_fields),
            "working_memory": self.working_memory,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def state_hash(self) -> str:
        return hashlib.sha256(self.canonical().encode()).hexdigest()


class Goal(BaseModel):
    id: str
    predicate: Condition
    description: str = ""

    def is_satisfied(self, state: FactoredState, arguments: Mapping[str, Any] | None = None) -> bool:
        return condition_holds(self.predicate, state, arguments or {})


class Milestone(BaseModel):
    id: str
    goals: list[Goal]
    mode: Literal["all", "any"] = "all"

    def is_satisfied(self, state: FactoredState) -> bool:
        results = [goal.is_satisfied(state) for goal in self.goals]
        return all(results) if self.mode == "all" else any(results)


class TaskAutomaton(BaseModel):
    id: str
    milestones: list[Milestone]
    constraints: dict[str, JsonValue] = Field(default_factory=dict)

    def progress(self, state: FactoredState) -> int:
        progress = 0
        for milestone in self.milestones:
            if not milestone.is_satisfied(state):
                break
            progress += 1
        return progress

    def is_satisfied(self, state: FactoredState) -> bool:
        return self.progress(state) == len(self.milestones)


class ActionProposal(BaseModel):
    action: str
    args: dict[str, JsonValue] = Field(default_factory=dict)
    confirmed: bool = False
    policy_version: str | None = None


class StateChange(BaseModel):
    field: str
    before: JsonValue = None
    after: JsonValue = None
    before_known: bool = True
    after_known: bool = True


class ActionResult(BaseModel):
    action: str
    args: dict[str, JsonValue]
    status: Literal["succeeded", "failed", "cancelled", "confirmation_required"]
    message: str
    error_code: str | None = None
    verified: bool = False
    before_state: FactoredState
    observed_state: FactoredState
    state_diff: list[StateChange] = Field(default_factory=list)
    duration_ms: int = Field(ge=0)


class LoopEvent(BaseModel):
    """One observable phase of the environment control loop."""

    sequence: int = Field(ge=0)
    phase: Literal["observe", "propose", "validate", "act", "verify", "recover"]
    action: str | None = None
    state_hash: str | None = None
    status: str
    detail: str = ""


class ExecutionLimits(BaseModel):
    max_steps: int = Field(default=50, ge=1)
    timeout_seconds: float = Field(default=30, gt=0)
    max_cumulative_risk: int = Field(default=20, ge=0)
    max_state_visits: int = Field(default=3, ge=1)


class TaskResult(BaseModel):
    task_id: str
    status: Literal["succeeded", "failed", "cancelled", "confirmation_required"]
    executions: list[ActionResult]
    final_state: FactoredState
    progress: int
    error: str | None = None
    pending_proposal: ActionProposal | None = None
    timeline: list[LoopEvent] = Field(default_factory=list)
    duration_ms: int = Field(default=0, ge=0)


class EnvironmentBinding(Protocol):
    def observe(self) -> FactoredState: ...

    def execute(self, action_id: str, args: Mapping[str, JsonValue]) -> str: ...


class Policy(Protocol):
    version: str

    def propose(
        self,
        state: FactoredState,
        task: TaskAutomaton,
        actions: tuple[ActionSpec, ...],
        history: tuple[ActionResult, ...],
    ) -> ActionProposal | None: ...


def _resolved_value(item: Condition | Effect, args: Mapping[str, Any]) -> Any:
    if item.value_from_argument is not None:
        return args.get(item.value_from_argument)

    def resolve_template(value: Any) -> Any:
        if isinstance(value, dict):
            if set(value) == {"$arg"}:
                return args.get(str(value["$arg"]))
            return {key: resolve_template(nested) for key, nested in value.items()}
        if isinstance(value, list):
            return [resolve_template(nested) for nested in value]
        return value

    return resolve_template(item.value)


def condition_holds(condition: Condition, state: FactoredState, args: Mapping[str, Any]) -> bool:
    try:
        actual = state.value(condition.field)
    except KeyError:
        return False
    expected = _resolved_value(condition, args)
    if condition.operator == "eq":
        return actual == expected
    if condition.operator == "neq":
        return actual != expected
    if condition.operator == "truthy":
        return bool(actual)
    if condition.operator == "falsy":
        return not actual
    if condition.operator == "exists":
        return True
    try:
        contained = expected in actual  # type: ignore[operator]
    except (TypeError, ValueError):
        contained = False
    return contained if condition.operator == "contains" else not contained


def state_diff(before: FactoredState, after: FactoredState) -> list[StateChange]:
    missing = object()
    changes: list[StateChange] = []

    def walk(prefix: str, left: Any, right: Any) -> None:
        if isinstance(left, dict) and isinstance(right, dict):
            for key in sorted(set(left) | set(right)):
                walk(f"{prefix}.{key}" if prefix else key, left.get(key, missing), right.get(key, missing))
            return
        if left != right:
            before_known = left is not missing and not any(
                prefix == unknown or prefix.startswith(f"{unknown}.") for unknown in before.unknown_fields
            )
            after_known = right is not missing and not any(
                prefix == unknown or prefix.startswith(f"{unknown}.") for unknown in after.unknown_fields
            )
            changes.append(
                StateChange(
                    field=prefix,
                    before=None if left is missing else left,
                    after=None if right is missing else right,
                    before_known=before_known,
                    after_known=after_known,
                )
            )

    walk("", before.fields, after.fields)
    return changes


class ActionRegistry:
    def __init__(self, environment_version: str) -> None:
        self.environment_version = environment_version
        self._actions: dict[str, ActionSpec] = {}
        self._discovered: tuple[ActionSpec, ...] | None = None

    def register(self, spec: ActionSpec) -> None:
        if spec.id in self._actions:
            raise ValueError(f"Action already registered: {spec.id}")
        self._actions[spec.id] = spec
        self._discovered = None

    def get(self, action_id: str) -> ActionSpec:
        try:
            return self._actions[action_id]
        except KeyError as exc:
            raise ValueError(f"Unknown action: {action_id}") from exc

    def discover(self) -> tuple[ActionSpec, ...]:
        if self._discovered is None:
            self._discovered = tuple(self._actions[key] for key in sorted(self._actions))
        return self._discovered

    @property
    def semantics_version(self) -> str:
        payload = [item.model_dump(mode="json") for item in self.discover()]
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]

    def validate(self, proposal: ActionProposal, state: FactoredState) -> str | None:
        try:
            spec = self.get(proposal.action)
        except ValueError as exc:
            return str(exc)
        for name, argument in spec.arguments.items():
            if argument.required and name not in proposal.args:
                return f"Missing required argument: {name}"
            if name in proposal.args and not _matches_type(proposal.args[name], argument.type):
                return f"Invalid type for argument {name}: expected {argument.type}"
        extra = set(proposal.args) - set(spec.arguments)
        if extra:
            return f"Unknown argument(s): {', '.join(sorted(extra))}"
        for condition in spec.preconditions:
            if not condition_holds(condition, state, proposal.args):
                return f"Precondition failed: {condition.field} {condition.operator}"
        return None


def _matches_type(value: Any, expected: str) -> bool:
    types: dict[str, type | tuple[type, ...]] = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    if expected in {"integer", "number"} and isinstance(value, bool):
        return False
    return isinstance(value, types[expected])


class GeneratedSimulator:
    """In-memory environment whose transitions come only from registered effects."""

    def __init__(self, registry: ActionRegistry, initial_fields: dict[str, JsonValue]) -> None:
        self.registry = registry
        self._fields = json.loads(json.dumps(initial_fields))
        self._revision = 0
        self._lock = RLock()
        self._undo: list[dict[str, JsonValue]] = []
        self._redo: list[dict[str, JsonValue]] = []

    def observe(self) -> FactoredState:
        with self._lock:
            return FactoredState(
                environment_version=self.registry.environment_version,
                revision=self._revision,
                fields=json.loads(json.dumps(self._fields)),
            )

    def execute(self, action_id: str, args: Mapping[str, JsonValue]) -> str:
        spec = self.registry.get(action_id)
        with self._lock:
            if action_id == "system.undo_last":
                if not self._undo:
                    raise RuntimeError("Nothing to undo")
                self._redo.append(json.loads(json.dumps(self._fields)))
                self._fields = self._undo.pop()
                self._set_history_flags()
                self._revision += 1
                return "Last action undone"
            if action_id == "system.redo_last":
                if not self._redo:
                    raise RuntimeError("Nothing to redo")
                self._undo.append(json.loads(json.dumps(self._fields)))
                self._fields = self._redo.pop()
                self._set_history_flags()
                self._revision += 1
                return "Last action redone"
            if spec.reversible and action_id not in {"system.observe", "system.wait", "system.begin_task"}:
                self._undo.append(json.loads(json.dumps(self._fields)))
                self._undo = self._undo[-50:]
                self._redo.clear()
            for effect in spec.effects:
                self._apply(effect, args)
            self._set_history_flags()
            self._revision += 1
        return f"{action_id} completed"

    def snapshot(self) -> dict[str, JsonValue]:
        with self._lock:
            return json.loads(json.dumps(self._fields))

    def restore_snapshot(self, fields: Mapping[str, JsonValue]) -> None:
        with self._lock:
            self._fields = json.loads(json.dumps(fields))
            self._set_history_flags()
            self._revision += 1

    def _set_history_flags(self) -> None:
        system = self._fields.get("system")
        if isinstance(system, dict):
            system["undo_available"] = bool(self._undo)
            system["redo_available"] = bool(self._redo)

    def record_failure(self, action_id: str) -> None:
        """Expose a normalized action failure to the next policy decision."""
        with self._lock:
            task = self._fields.get("task")
            if not isinstance(task, dict):
                return
            task["last_failure"] = {
                "action": action_id,
                "code": "action_failed",
                "recoverable": True,
            }
            self._revision += 1

    def _apply(self, effect: Effect, args: Mapping[str, JsonValue]) -> None:
        parts = effect.field.split(".")
        target: dict[str, Any] = self._fields
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        key = parts[-1]
        value = _resolved_value(effect, args)
        if effect.operation == "set":
            target[key] = value
        elif effect.operation == "clear":
            target[key] = None
        elif effect.operation == "add":
            current = target.setdefault(key, [])
            if value not in current:
                current.append(value)
        elif effect.operation == "remove":
            current = target.setdefault(key, [])
            if value in current:
                current.remove(value)


class StochasticSimulator(GeneratedSimulator):
    """Generated simulator with reproducible, non-destructive action failures."""

    def __init__(
        self,
        registry: ActionRegistry,
        initial_fields: dict[str, JsonValue],
        *,
        failure_probabilities: Mapping[str, float] | None = None,
        failure_schedule: Mapping[str, int] | None = None,
        seed: int = 0x5EED1234,
    ) -> None:
        super().__init__(registry, initial_fields)
        self.failure_probabilities = dict(failure_probabilities or {})
        self.failure_schedule = dict(failure_schedule or {})
        self._rng = random.Random(seed)

    def execute(self, action_id: str, args: Mapping[str, JsonValue]) -> str:
        remaining = self.failure_schedule.get(action_id, 0)
        if remaining > 0:
            self.failure_schedule[action_id] = remaining - 1
            raise RuntimeError(f"Injected timeout: {action_id}")
        probability = self.failure_probabilities.get(action_id, 0)
        if probability and self._rng.random() < probability:
            raise RuntimeError(f"Stochastic timeout: {action_id}")
        return super().execute(action_id, args)


class Doer:
    """The sole mutation boundary. Policies and planners can only submit proposals."""

    def __init__(self, registry: ActionRegistry, binding: EnvironmentBinding) -> None:
        self.registry = registry
        self.binding = binding
        self._lock = RLock()

    def execute(self, proposal: ActionProposal, *, cancelled: Event | None = None) -> ActionResult:
        with self._lock:
            started = time.monotonic()
            before = self.binding.observe()
            if cancelled and cancelled.is_set():
                return self._result(proposal, "cancelled", "Task cancelled", "cancelled", before, before, started)
            error = self.registry.validate(proposal, before)
            if error:
                return self._result(proposal, "failed", error, "invalid_proposal", before, before, started)
            spec = self.registry.get(proposal.action)
            if spec.confirmation_required and not proposal.confirmed:
                return self._result(
                    proposal, "confirmation_required", "Action requires confirmation", "confirmation_required",
                    before, before, started,
                )
            try:
                message = self.binding.execute(proposal.action, proposal.args)
            except Exception as exc:  # bindings convert platform failures into structured results
                record_failure = getattr(self.binding, "record_failure", None)
                if callable(record_failure):
                    record_failure(proposal.action)
                after = self.binding.observe()
                return self._result(proposal, "failed", str(exc), "binding_error", before, after, started)
            after = self.binding.observe()
            verified = all(condition_holds(item, after, proposal.args) for item in spec.postconditions)
            if not verified:
                record_failure = getattr(self.binding, "record_failure", None)
                if callable(record_failure):
                    record_failure(proposal.action)
                    after = self.binding.observe()
                return self._result(
                    proposal, "failed", "Postcondition verification failed", "verification_failed",
                    before, after, started,
                )
            return self._result(proposal, "succeeded", message, None, before, after, started, verified=True)

    @staticmethod
    def _result(
        proposal: ActionProposal,
        status: Literal["succeeded", "failed", "cancelled", "confirmation_required"],
        message: str,
        error_code: str | None,
        before: FactoredState,
        after: FactoredState,
        started: float,
        verified: bool = False,
    ) -> ActionResult:
        return ActionResult(
            action=proposal.action,
            args=proposal.args,
            status=status,
            message=message,
            error_code=error_code,
            verified=verified,
            before_state=before,
            observed_state=after,
            state_diff=state_diff(before, after),
            duration_ms=max(0, round((time.monotonic() - started) * 1000)),
        )


class TaskController:
    def __init__(self) -> None:
        self._tasks: dict[str, Event] = {}
        self._lock = RLock()

    def token(self, task_id: str) -> Event:
        with self._lock:
            return self._tasks.setdefault(task_id, Event())

    def cancel(self, task_id: str) -> bool:
        with self._lock:
            token = self._tasks.get(task_id)
            if token is None:
                return False
            token.set()
            return True

    def finish(self, task_id: str) -> None:
        with self._lock:
            self._tasks.pop(task_id, None)


RISK_POINTS = {Risk.LOW: 1, Risk.MEDIUM: 4, Risk.HIGH: 10}


class ExecutionEngine:
    def __init__(
        self,
        registry: ActionRegistry,
        doer: Doer,
        policy: Policy,
        controller: TaskController | None = None,
    ) -> None:
        self.registry = registry
        self.doer = doer
        self.policy = policy
        self.controller = controller or TaskController()

    def run(self, task: TaskAutomaton, limits: ExecutionLimits | None = None) -> TaskResult:
        limits = limits or ExecutionLimits()
        token = self.controller.token(task.id)
        executions: list[ActionResult] = []
        visits: dict[str, int] = {}
        cumulative_risk = 0
        started = time.monotonic()
        timeline: list[LoopEvent] = []

        def record(phase: Literal["observe", "propose", "validate", "act", "verify", "recover"], status: str, *, action: str | None = None, state: FactoredState | None = None, detail: str = "") -> None:
            timeline.append(LoopEvent(
                sequence=len(timeline), phase=phase, action=action,
                state_hash=state.state_hash() if state else None,
                status=status, detail=detail,
            ))

        def result(status: Literal["succeeded", "failed", "cancelled", "confirmation_required"], state: FactoredState, error: str | None = None, pending: ActionProposal | None = None) -> TaskResult:
            return self._task_result(
                task, status, executions, state, error, pending,
                timeline=timeline,
                duration_ms=max(0, round((time.monotonic() - started) * 1000)),
            )
        try:
            for _ in range(limits.max_steps):
                state = self.doer.binding.observe()
                record("observe", "ok", state=state, detail=f"milestone {task.progress(state)}/{len(task.milestones)}")
                if task.is_satisfied(state):
                    return result("succeeded", state)
                if token.is_set():
                    return result("cancelled", state, "Task cancelled")
                if time.monotonic() - started >= limits.timeout_seconds:
                    return result("failed", state, "Task timed out")
                fingerprint = f"{task.progress(state)}:{state.state_hash()}"
                visits[fingerprint] = visits.get(fingerprint, 0) + 1
                if visits[fingerprint] > limits.max_state_visits:
                    return result("failed", state, "Cycle detected")

                proposal = self.policy.propose(state, task, self.registry.discover(), tuple(executions))
                if proposal is None:
                    record("propose", "error", state=state, detail="Policy returned no proposal")
                    return result("failed", state, "Policy returned no proposal")
                record("propose", "ok", action=proposal.action, state=state, detail=proposal.policy_version or self.policy.version)
                validation_error = self.registry.validate(proposal, state)
                if validation_error:
                    record("validate", "error", action=proposal.action, state=state, detail=validation_error)
                    return result("failed", state, validation_error)
                record("validate", "ok", action=proposal.action, state=state)
                spec = self.registry.get(proposal.action)
                cumulative_risk += RISK_POINTS[spec.risk]
                if cumulative_risk > limits.max_cumulative_risk:
                    return result("failed", state, "Cumulative risk limit exceeded")

                action_result = self.doer.execute(proposal, cancelled=token)
                executions.append(action_result)
                record("act", action_result.status, action=proposal.action, state=action_result.observed_state, detail=action_result.message)
                record("verify", "ok" if action_result.verified else "error", action=proposal.action, state=action_result.observed_state, detail="postconditions satisfied" if action_result.verified else action_result.error_code or "not verified")
                if action_result.status == "confirmation_required":
                    return result("confirmation_required", action_result.observed_state, action_result.message, proposal)
                if action_result.status in {"failed", "cancelled"}:
                    # The next policy decision sees the failure and fresh observation. A
                    # cancellation is terminal; ordinary failures may be recovered from.
                    if action_result.status == "cancelled":
                        return result("cancelled", action_result.observed_state, action_result.message)
                    record("recover", "retry", action=proposal.action, state=action_result.observed_state, detail="control returned to policy")
            final = self.doer.binding.observe()
            if task.is_satisfied(final):
                return result("succeeded", final)
            return result("failed", final, "Maximum step limit reached")
        finally:
            self.controller.finish(task.id)

    @staticmethod
    def _task_result(
        task: TaskAutomaton,
        status: Literal["succeeded", "failed", "cancelled", "confirmation_required"],
        executions: list[ActionResult],
        state: FactoredState,
        error: str | None = None,
        pending: ActionProposal | None = None,
        *,
        timeline: list[LoopEvent] | None = None,
        duration_ms: int = 0,
    ) -> TaskResult:
        return TaskResult(
            task_id=task.id,
            status=status,
            executions=executions,
            final_state=state,
            progress=task.progress(state),
            error=error,
            pending_proposal=pending,
            timeline=timeline or [],
            duration_ms=duration_ms,
        )


@dataclass(frozen=True)
class RulePolicy:
    """Small deterministic baseline; it proposes but never mutates."""

    rule: Callable[[FactoredState, TaskAutomaton, tuple[ActionSpec, ...], tuple[ActionResult, ...]], ActionProposal | None]
    version: str = "rule-v1"

    def propose(
        self,
        state: FactoredState,
        task: TaskAutomaton,
        actions: tuple[ActionSpec, ...],
        history: tuple[ActionResult, ...],
    ) -> ActionProposal | None:
        return self.rule(state, task, actions, history)


def register_all(registry: ActionRegistry, specs: Iterable[ActionSpec]) -> ActionRegistry:
    for spec in specs:
        registry.register(spec)
    return registry
