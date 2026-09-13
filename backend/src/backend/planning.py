from __future__ import annotations

import heapq
import json
import random
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from .environment import (
    ActionProposal,
    ActionRegistry,
    FactoredState,
    GeneratedSimulator,
    JsonValue,
    RISK_POINTS,
    TaskAutomaton,
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


class PolicyCache:
    def __init__(self) -> None:
        self._entries: dict[str, TrainedPolicy] = {}
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
        if value is None:
            self.misses += 1
        else:
            self.hits += 1
        return value

    def put(self, policy: TrainedPolicy) -> None:
        self._entries[policy.cache_key] = policy


def policy_state_key(state: FactoredState, task: TaskAutomaton) -> str:
    return f"{task.progress(state)}:{state.state_hash()}"


def encode_proposal(proposal: ActionProposal) -> str:
    return json.dumps({"action": proposal.action, "args": proposal.args}, sort_keys=True, separators=(",", ":"))


def proposals_for(registry: ActionRegistry, task: TaskAutomaton, state: FactoredState) -> list[ActionProposal]:
    goals = [goal for milestone in task.milestones for goal in milestone.goals]
    proposals: list[ActionProposal] = []
    for spec in registry.discover():
        args: dict[str, JsonValue] = {}
        for name, argument in spec.arguments.items():
            matched = False
            for effect in spec.effects:
                if effect.value_from_argument != name:
                    continue
                for goal in goals:
                    if goal.predicate.field == effect.field and goal.predicate.value is not None:
                        args[name] = goal.predicate.value
                        matched = True
                        break
                if matched:
                    break
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
            simulator = GeneratedSimulator(self.registry, initial_fields)
            total_reward = 0.0
            steps = 0
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
                simulator.execute(proposal.action, proposal.args)
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
            traces.append(TrainingTrace(episode=episode, steps=steps, reward=round(total_reward, 6),
                                        succeeded=task.is_satisfied(simulator.observe())))

        policy = TrainedPolicy(
            version=self.version,
            cache_key=cache_key,
            q_table=q_table,
            traces=traces,
            action_space=[spec.id for spec in self.registry.discover()],
        )
        self.cache.put(policy)
        return policy


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
            heuristic = len(task.milestones) - task.progress(child_state) if algorithm == "astar" else 0
            heapq.heappush(queue, _QueueItem(cost + heuristic, counter, child_state.fields, [*item.path, proposal]))
    return None
