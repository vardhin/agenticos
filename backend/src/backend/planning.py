from __future__ import annotations

import heapq
import hashlib
import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .environment import (
    ActionResult,
    ActionSpec,
    ActionProposal,
    ActionRegistry,
    FactoredState,
    GeneratedSimulator,
    JsonValue,
    RISK_POINTS,
    StochasticSimulator,
    TaskAutomaton,
    condition_holds,
)


class RewardConfig(BaseModel):
    terminal: float = 20
    milestone: float = 3
    step: float = -0.05
    failure: float = -2
    risk: float = -0.2


class TrainingConfig(BaseModel):
    episodes: int = Field(default=1200, ge=1)
    max_steps: int = Field(default=50, ge=1)
    seed: int = 0x5EED1234
    alpha: float = Field(default=0.25, gt=0, le=1)
    gamma: float = Field(default=0.9, ge=0, le=1)
    epsilon_start: float = Field(default=0.9, ge=0, le=1)
    epsilon_end: float = Field(default=0.05, ge=0, le=1)
    rewards: RewardConfig = Field(default_factory=RewardConfig)


class TrainingTrace(BaseModel):
    episode: int
    steps: int
    reward: float
    succeeded: bool
    failures: int = 0
    transitions: list[str] = Field(default_factory=list)


class TrainedPolicy(BaseModel):
    version: str
    cache_key: str
    q_table: dict[str, dict[str, float]]
    traces: list[TrainingTrace]
    action_space: list[str]

    def proposal(self, state: FactoredState, task: TaskAutomaton) -> ActionProposal | None:
        values = self.q_table.get(policy_state_key(state, task), {})
        if not values:
            return None
        encoded = max(values, key=lambda key: (values[key], key))
        payload = json.loads(encoded)
        return ActionProposal(action=payload["action"], args=payload["args"], policy_version=self.version)

    def propose(
        self,
        state: FactoredState,
        task: TaskAutomaton,
        actions: tuple[ActionSpec, ...],
        history: tuple[ActionResult, ...],
    ) -> ActionProposal | None:
        return self.proposal(state, task)


class PolicyCache:
    def __init__(self, path: str | Path | None = None) -> None:
        self._entries: dict[str, TrainedPolicy] = {}
        self.path = Path(path) if path else None
        self.hits = 0
        self.misses = 0

    def key(self, registry: ActionRegistry, task: TaskAutomaton) -> str:
        payload = {
            "environment": registry.environment_version,
            "semantics": registry.semantics_version,
            "task": task.model_dump(mode="json"),
            "constraints": task.constraints,
        }
        import hashlib
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def get(self, key: str) -> TrainedPolicy | None:
        value = self._entries.get(key)
        if value is None and self.path:
            policy_path = self.path / f"{key}.json"
            if policy_path.exists():
                value = TrainedPolicy.model_validate_json(policy_path.read_text())
                self._entries[key] = value
        if value is None:
            self.misses += 1
        else:
            self.hits += 1
        return value

    def put(self, policy: TrainedPolicy) -> None:
        self._entries[policy.cache_key] = policy
        if self.path:
            self.path.mkdir(parents=True, exist_ok=True)
            (self.path / f"{policy.cache_key}.json").write_text(policy.model_dump_json())


def policy_state_key(state: FactoredState, task: TaskAutomaton) -> str:
    # The goal signature makes this a goal-conditioned representation: the same
    # observed desktop state can safely participate in policies for many names,
    # paths, and targets.
    goal_signature = hashlib.sha256(
        json.dumps(task.model_dump(mode="json"), sort_keys=True).encode()
    ).hexdigest()[:16]
    return f"{goal_signature}:{task.progress(state)}:{state.state_hash()}"


def encode_proposal(proposal: ActionProposal) -> str:
    return json.dumps({"action": proposal.action, "args": proposal.args}, sort_keys=True, separators=(",", ":"))


_RELEVANCE_CACHE: dict[tuple[int, str, int, str], frozenset[str]] = {}


def proposals_for(registry: ActionRegistry, task: TaskAutomaton, state: FactoredState) -> list[ActionProposal]:
    goals = [goal for milestone in task.milestones for goal in milestone.goals]
    progress = task.progress(state)
    target_goals = task.milestones[progress].goals if progress < len(task.milestones) else []
    relevance_key = (id(registry), task.id, progress, state.state_hash())
    cached_relevant = _RELEVANCE_CACHE.get(relevance_key)
    if cached_relevant is None:
        needed_conditions = [goal.predicate for goal in target_goals]
        relevant: set[str] = set()

        def can_satisfy(effect: Any, condition: Any) -> bool:
            if effect.field != condition.field:
                return False
            if effect.value_from_argument is not None:
                return True
            # A dynamic precondition (for example ``visible_ssids contains
            # args.ssid``) is grounded when the dependent action proposal is
            # built.  During the backwards relevance pass we do not have that
            # proposal's arguments yet, so any compatible producer of the
            # field must remain in the search graph.
            if condition.value_from_argument is not None:
                if condition.operator == "contains":
                    return effect.operation in {"add", "set"}
                if condition.operator == "not_contains":
                    return effect.operation in {"remove", "set", "clear"}
                return effect.operation in {"set", "clear"}
            if condition.operator == "eq":
                return effect.operation in {"set", "clear"} and effect.value == condition.value
            if condition.operator == "contains":
                return effect.operation == "add" and effect.value == condition.value or (
                    effect.operation == "set" and isinstance(effect.value, list) and condition.value in effect.value
                )
            if condition.operator == "not_contains":
                return effect.operation == "remove" and effect.value == condition.value
            if condition.operator == "truthy":
                return effect.operation == "set" and bool(effect.value)
            if condition.operator == "falsy":
                return effect.operation in {"set", "clear"} and not effect.value
            return effect.operation != "clear" or condition.operator == "exists"

        # Work backwards from goal fields through action preconditions. This keeps a
        # large dynamic registry tractable without teaching the compiler a route.
        changed = True
        while changed:
            changed = False
            for spec in registry.discover():
                if spec.id in relevant or not any(
                    can_satisfy(effect, condition)
                    for effect in spec.effects
                    for condition in needed_conditions
                ):
                    continue
                relevant.add(spec.id)
                before = len(needed_conditions)
                known = {(condition.field, condition.operator, repr(condition.value), condition.value_from_argument) for condition in needed_conditions}
                for condition in spec.preconditions:
                    if condition.value_from_argument is None and condition_holds(condition, state, {}):
                        continue
                    key = (condition.field, condition.operator, repr(condition.value), condition.value_from_argument)
                    if key not in known:
                        needed_conditions.append(condition)
                        known.add(key)
                changed = changed or len(needed_conditions) != before
        cached_relevant = frozenset(relevant)
        _RELEVANCE_CACHE[relevance_key] = cached_relevant

    def default_argument(name: str) -> JsonValue:
        defaults: dict[str, JsonValue] = {
            "app_id": "app:files",
            "archive_name": task.constraints.get("filename", "archive"),
            "content": state.fields.get("clipboard", {}).get("current", ""),
            "file_id": state.fields.get("filesystem", {}).get("found_id") or "file:search-result",
            "node_id": state.fields.get("filesystem", {}).get("found_id") or "file:search-result",
            "node_ids": [state.fields.get("filesystem", {}).get("found_id") or "file:search-result"],
            "parent": task.constraints.get("save_parent", "Documents"),
            "path": task.constraints.get("folder", "Documents"),
            "position": 0,
            "resource": "current_page",
            "query": task.constraints.get("source", task.constraints.get("filename", "current item")),
            "side": "right",
            "window_id": "window:editor",
        }
        return defaults.get(name)

    proposals: list[ActionProposal] = []
    for spec in registry.discover():
        if spec.id not in cached_relevant:
            continue
        args: dict[str, JsonValue] = {}
        for name, argument in spec.arguments.items():
            matched = False
            # Prefer the active milestone. Later goals can legitimately target
            # the same field (for example workspace 2, then workspace 1).
            for goal_set in (target_goals, goals):
                for effect in spec.effects:
                    if effect.value_from_argument != name:
                        continue
                    for goal in goal_set:
                        if goal.predicate.field == effect.field and goal.predicate.value is not None:
                            args[name] = goal.predicate.value
                            matched = True
                            break
                    if matched:
                        break
                if matched:
                    break
            if not matched:
                default = default_argument(name)
                if default is not None:
                    args[name] = default
                    matched = True
            if argument.required and not matched:
                break
        else:
            proposal = ActionProposal(action=spec.id, args=args)
            if registry.validate(proposal, state) is None and not spec.confirmation_required:
                proposals.append(proposal)
    return proposals


class QLearner:
    version = "tabular-q-v2"

    def __init__(self, registry: ActionRegistry, cache: PolicyCache | None = None) -> None:
        self.registry = registry
        self.cache = cache or PolicyCache()

    def train(
        self,
        task: TaskAutomaton,
        initial_fields: dict[str, JsonValue],
        config: TrainingConfig | None = None,
    ) -> TrainedPolicy:
        config = config or TrainingConfig()
        cache_key = self.cache.key(self.registry, task)
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached
        rng = random.Random(config.seed)
        q_table: dict[str, dict[str, float]] = {}
        traces: list[TrainingTrace] = []

        for episode in range(config.episodes):
            failure_probabilities = task.constraints.get("stochastic_failures", {})
            simulator: GeneratedSimulator = StochasticSimulator(
                self.registry,
                initial_fields,
                failure_probabilities=failure_probabilities if isinstance(failure_probabilities, dict) else {},
                seed=config.seed + episode,
            )
            total_reward = 0.0
            steps = 0
            failures = 0
            transitions: list[str] = []
            epsilon = max(
                config.epsilon_end,
                config.epsilon_start * (1 - episode / config.episodes),
            )
            for steps in range(1, config.max_steps + 1):
                state = simulator.observe()
                if task.is_satisfied(state):
                    break
                candidates = proposals_for(self.registry, task, state)
                if not candidates:
                    total_reward += config.rewards.failure
                    break
                key = policy_state_key(state, task)
                values = q_table.setdefault(key, {})
                encoded = [encode_proposal(item) for item in candidates]
                for item in encoded:
                    values.setdefault(item, 0.0)
                selected = rng.randrange(len(candidates)) if rng.random() < epsilon else max(
                    range(len(candidates)), key=lambda index: (values[encoded[index]], encoded[index])
                )
                proposal = candidates[selected]
                previous_progress = task.progress(state)
                try:
                    simulator.execute(proposal.action, proposal.args)
                    transitions.append(encode_proposal(proposal))
                except RuntimeError:
                    simulator.record_failure(proposal.action)
                    failures += 1
                    total_reward += config.rewards.failure
                    transitions.append(f"failed:{encode_proposal(proposal)}")
                next_state = simulator.observe()
                next_progress = task.progress(next_state)
                spec = self.registry.get(proposal.action)
                reward = config.rewards.step - config.rewards.risk * RISK_POINTS[spec.risk]
                if next_progress > previous_progress:
                    reward += config.rewards.terminal if task.is_satisfied(next_state) else config.rewards.milestone
                elif next_state.state_hash() == state.state_hash():
                    reward += config.rewards.failure
                next_values = q_table.setdefault(policy_state_key(next_state, task), {})
                future = max(next_values.values(), default=0.0)
                action_key = encode_proposal(proposal)
                values[action_key] += config.alpha * (reward + config.gamma * future - values[action_key])
                total_reward += reward
                if task.is_satisfied(next_state):
                    break
            traces.append(TrainingTrace(
                episode=episode,
                steps=steps,
                reward=round(total_reward, 6),
                succeeded=task.is_satisfied(simulator.observe()),
                failures=failures,
                transitions=transitions,
            ))

        policy = TrainedPolicy(
            version=self.version,
            cache_key=cache_key,
            q_table=q_table,
            traces=traces,
            action_space=[spec.id for spec in self.registry.discover()],
        )
        self.cache.put(policy)
        return policy


@dataclass
class AdaptivePolicy:
    """Use learned values when known and re-plan after unseen live divergence."""

    registry: ActionRegistry
    trained: TrainedPolicy
    algorithm: str = "astar"
    version: str = "adaptive-q-v1"
    replans: int = 0

    def propose(
        self,
        state: FactoredState,
        task: TaskAutomaton,
        actions: tuple[ActionSpec, ...],
        history: tuple[ActionResult, ...],
    ) -> ActionProposal | None:
        learned = self.trained.proposal(state, task)
        if learned is not None and self.registry.validate(learned, state) is None:
            return learned
        plan = search_plan(
            self.registry,
            task,
            state.fields,
            algorithm="astar" if self.algorithm == "astar" else "bfs",
        )
        self.replans += 1
        if not plan:
            return None
        proposal = plan[0]
        proposal.policy_version = self.version
        return proposal


@dataclass(order=True)
class _QueueItem:
    priority: float
    counter: int
    fields: dict[str, JsonValue] = field(compare=False)
    path: list[ActionProposal] = field(compare=False)


def search_plan(
    registry: ActionRegistry,
    task: TaskAutomaton,
    initial_fields: dict[str, JsonValue],
    *,
    algorithm: Literal["bfs", "astar"] = "bfs",
    max_steps: int = 50,
) -> list[ActionProposal] | None:
    """Deterministic BFS/A* baseline over the same generated transitions."""
    counter = 0
    queue: list[_QueueItem] = [_QueueItem(0, counter, initial_fields, [])]
    seen: set[str] = set()
    while queue:
        item = heapq.heappop(queue)
        simulator = GeneratedSimulator(registry, item.fields)
        state = simulator.observe()
        if task.is_satisfied(state):
            return item.path
        if len(item.path) >= max_steps or state.state_hash() in seen:
            continue
        seen.add(state.state_hash())
        for proposal in proposals_for(registry, task, state):
            child = GeneratedSimulator(registry, state.fields)
            child.execute(proposal.action, proposal.args)
            child_state = child.observe()
            counter += 1
            cost = len(item.path) + 1
            child_progress = task.progress(child_state)
            if algorithm == "astar":
                unmet = 0
                if child_progress < len(task.milestones):
                    unmet = sum(
                        not goal.is_satisfied(child_state)
                        for goal in task.milestones[child_progress].goals
                    )
                # A completed ordered milestone dominates cosmetic state changes.
                heuristic = (len(task.milestones) - child_progress) * 10 + unmet
            else:
                heuristic = 0
            heapq.heappush(queue, _QueueItem(cost + heuristic, counter, child_state.fields, [*item.path, proposal]))
    return None
