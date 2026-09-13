from __future__ import annotations

from collections import deque
from threading import RLock
from typing import Any

from pydantic import BaseModel, Field


class TaskMeasurement(BaseModel):
    task_id: str
    status: str
    training_ms: float = Field(ge=0)
    inference_ms: float = Field(ge=0)
    environment_steps: int = Field(ge=0)
    unnecessary_actions: int = Field(ge=0)
    recoveries: int = Field(ge=0)
    failures: int = Field(ge=0)
    cache_hit: bool = False
    bfs_steps: int | None = None
    astar_steps: int | None = None
    rl_steps: int | None = None
    live_simulator_divergences: int = Field(default=0, ge=0)
    llm_escalations: int = Field(default=0, ge=0)
    llm_cost: float = Field(default=0, ge=0)


class EvaluationTracker:
    """Thread-safe rolling task metrics used by the Inspector and benchmarks."""

    def __init__(self, capacity: int = 200) -> None:
        self._items: deque[TaskMeasurement] = deque(maxlen=capacity)
        self._lock = RLock()

    def record(self, item: TaskMeasurement) -> None:
        with self._lock:
            self._items.append(item)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            items = list(self._items)
        total = len(items)
        succeeded = sum(item.status == "succeeded" for item in items)
        failures = sum(item.failures for item in items)
        recoveries = sum(item.recoveries for item in items)

        def average(attribute: str) -> float:
            return round(sum(float(getattr(item, attribute)) for item in items) / total, 3) if total else 0.0

        return {
            "tasks": total,
            "success_rate": succeeded / total if total else 0.0,
            "training_time_ms": average("training_ms"),
            "inference_time_ms": average("inference_ms"),
            "environment_steps": sum(item.environment_steps for item in items),
            "unnecessary_actions": sum(item.unnecessary_actions for item in items),
            "recovery_rate": recoveries / failures if failures else 0.0,
            "policy_cache_hit_rate": sum(item.cache_hit for item in items) / total if total else 0.0,
            "planner_vs_rl": {
                "bfs_steps": sum(item.bfs_steps or 0 for item in items),
                "astar_steps": sum(item.astar_steps or 0 for item in items),
                "rl_steps": sum(item.rl_steps or 0 for item in items),
            },
            "live_simulator_divergence": sum(item.live_simulator_divergences for item in items),
            "llm_escalation_frequency": sum(item.llm_escalations for item in items) / total if total else 0.0,
            "llm_cost": round(sum(item.llm_cost for item in items), 6),
            "recent": [item.model_dump(mode="json") for item in reversed(items[-20:])],
        }
