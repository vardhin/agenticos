from __future__ import annotations

from pathlib import Path

from backend.benchmarks import evaluate_ten_action_benchmarks
from backend.compiler import TaskCompiler
from backend.desktop import DesktopEnvironment, build_desktop_registry
from backend.environment import ActionProposal, Doer, ExecutionEngine, ExecutionLimits, RulePolicy
from backend.evaluation import EvaluationTracker, TaskMeasurement
from backend.planning import PolicyCache, QLearner, TrainingConfig, assess_representation


def test_compositional_grammar_builds_sequence_and_parallel_goal_groups() -> None:
    compiler = TaskCompiler()
    sequence = compiler.compile("SEQUENCE(set brightness to 42%, set volume to 35%)")
    assert sequence.automaton is not None
    assert [item.goals[0].predicate.field for item in sequence.automaton.milestones] == [
        "display.brightness", "audio.volume"
    ]
    parallel = compiler.compile("AND(wifi on, bluetooth on)")
    assert parallel.automaton is not None
    assert parallel.automaton.milestones[0].mode == "all"
    assert {goal.predicate.field for goal in parallel.automaton.milestones[0].goals} == {
        "wifi.enabled", "bluetooth.enabled"
    }


def test_policy_cache_replays_from_disk(tmp_path: Path) -> None:
    compiler = TaskCompiler()
    task = compiler.compile("SEQUENCE(set brightness to 42%, set volume to 35%)").automaton
    assert task is not None
    registry = build_desktop_registry()
    environment = DesktopEnvironment(registry)
    first_cache = PolicyCache(tmp_path)
    trained = QLearner(registry, first_cache).train(
        task, environment.observe().fields, TrainingConfig(episodes=30, max_steps=10)
    )
    second_cache = PolicyCache(tmp_path)
    replayed = second_cache.get(trained.cache_key)
    assert replayed is not None
    assert replayed.q_table == trained.q_table
    assert second_cache.hits == 1


def test_named_failure_injections_are_structured_and_detected() -> None:
    registry = build_desktop_registry()
    for mode, action, args, expected_code in [
        ("timeout", "display.set_theme", {"theme": "dark"}, "binding_error"),
        ("permission_denied", "display.set_theme", {"theme": "dark"}, "binding_error"),
        ("missing_file", "filesystem.read", {"file_id": "file:missing"}, "binding_error"),
        ("stale_state", "display.set_theme", {"theme": "dark"}, "verification_failed"),
        ("disappearing_network", "wifi.connect", {"ssid": "StudioNet"}, "binding_error"),
        ("duplicate_filename", "filesystem.create_file", {"parent": "Documents", "name": "hero", "content": ""}, "binding_error"),
    ]:
        environment = DesktopEnvironment(registry)
        environment.inject_failure_modes({action: mode})
        result = Doer(registry, environment).execute(ActionProposal(action=action, args=args))
        assert result.status == "failed", mode
        assert result.error_code == expected_code, mode
        assert result.observed_state.value("task.last_failure")["recoverable"] is True


def test_undo_and_redo_restore_reversible_state() -> None:
    registry = build_desktop_registry()
    environment = DesktopEnvironment(registry)
    doer = Doer(registry, environment)
    changed = doer.execute(ActionProposal(action="display.set_theme", args={"theme": "dark"}))
    assert changed.observed_state.value("display.theme") == "dark"
    undone = doer.execute(ActionProposal(action="system.undo_last"))
    assert undone.status == "succeeded"
    assert undone.observed_state.value("display.theme") == "light"
    redone = doer.execute(ActionProposal(action="system.redo_last"))
    assert redone.status == "succeeded"
    assert redone.observed_state.value("display.theme") == "dark"


def test_all_ten_action_benchmarks_plan_from_multiple_initial_states() -> None:
    report = evaluate_ten_action_benchmarks()
    assert report["passing"] == report["total"] == 10
    assert report["multiple_initial_states"] >= 2


def test_bounded_execution_and_representation_gate() -> None:
    task = TaskCompiler().compile("set brightness to 42%").automaton
    assert task is not None
    registry = build_desktop_registry()
    environment = DesktopEnvironment(registry)
    looping = RulePolicy(lambda *_: ActionProposal(action="system.observe"))
    result = ExecutionEngine(registry, Doer(registry, environment), looping).run(
        task, ExecutionLimits(max_steps=2, max_state_visits=1)
    )
    assert result.status == "failed"
    assert result.timeline[0].phase == "observe"
    assessment = assess_representation(environment.observe(), threshold=10**9)
    assert assessment.recommended is False
    assert assessment.algorithm == "tabular_q"


def test_evaluation_tracker_reports_every_required_metric() -> None:
    tracker = EvaluationTracker()
    tracker.record(TaskMeasurement(
        task_id="example", status="succeeded", training_ms=10, inference_ms=2,
        environment_steps=5, unnecessary_actions=1, recoveries=1, failures=1,
        cache_hit=True, bfs_steps=5, astar_steps=4, rl_steps=5,
        live_simulator_divergences=0, llm_escalations=0, llm_cost=0,
    ))
    metrics = tracker.snapshot()
    for key in (
        "success_rate", "training_time_ms", "inference_time_ms", "environment_steps",
        "unnecessary_actions", "recovery_rate", "policy_cache_hit_rate", "planner_vs_rl",
        "live_simulator_divergence", "llm_escalation_frequency", "llm_cost",
    ):
        assert key in metrics
