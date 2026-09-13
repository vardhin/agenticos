from __future__ import annotations

from threading import Event

from backend.environment import (
    ActionProposal,
    ActionRegistry,
    ActionSpec,
    ArgumentSpec,
    BindingSpec,
    Condition,
    Doer,
    Effect,
    ExecutionEngine,
    ExecutionLimits,
    FactoredState,
    GeneratedSimulator,
    Goal,
    Milestone,
    Risk,
    RulePolicy,
    TaskAutomaton,
)


def registry() -> ActionRegistry:
    result = ActionRegistry("test-v1")
    binding = BindingSpec(simulator="generated")
    result.register(
        ActionSpec(
            id="lamp.enable",
            description="Enable the lamp",
            effects=[Effect(field="lamp.enabled", value=True)],
            postconditions=[Condition(field="lamp.enabled", value=True)],
            binding=binding,
        )
    )
    result.register(
        ActionSpec(
            id="lamp.name",
            description="Name the lamp",
            arguments={"name": ArgumentSpec(type="string")},
            preconditions=[Condition(field="lamp.enabled", value=True)],
            effects=[Effect(field="lamp.name", value_from_argument="name")],
            postconditions=[Condition(field="lamp.name", value_from_argument="name")],
            binding=binding,
        )
    )
    result.register(
        ActionSpec(
            id="lamp.destroy",
            description="Destroy the lamp",
            effects=[Effect(field="lamp.exists", value=False)],
            postconditions=[Condition(field="lamp.exists", value=False)],
            risk=Risk.HIGH,
            reversible=False,
            binding=binding,
        )
    )
    return result


def test_generated_simulator_and_doer_verify_and_diff() -> None:
    actions = registry()
    simulator = GeneratedSimulator(actions, {"lamp": {"enabled": False, "name": None, "exists": True}})
    doer = Doer(actions, simulator)

    invalid = doer.execute(ActionProposal(action="lamp.name", args={"name": "Ada"}))
    assert invalid.status == "failed"
    assert invalid.error_code == "invalid_proposal"
    assert invalid.state_diff == []

    enabled = doer.execute(ActionProposal(action="lamp.enable"))
    assert enabled.status == "succeeded"
    assert enabled.verified is True
    assert enabled.state_diff[0].field == "lamp.enabled"
    assert enabled.state_diff[0].before is False
    assert enabled.state_diff[0].after is True

    named = doer.execute(ActionProposal(action="lamp.name", args={"name": "Ada"}))
    assert named.status == "succeeded"
    assert named.observed_state.value("lamp.name") == "Ada"


def test_confirmation_is_checked_immediately_before_doer_mutation() -> None:
    actions = registry()
    simulator = GeneratedSimulator(actions, {"lamp": {"enabled": True, "exists": True}})
    doer = Doer(actions, simulator)

    denied = doer.execute(ActionProposal(action="lamp.destroy"))
    assert denied.status == "confirmation_required"
    assert simulator.observe().value("lamp.exists") is True

    accepted = doer.execute(ActionProposal(action="lamp.destroy", confirmed=True))
    assert accepted.status == "succeeded"
    assert simulator.observe().value("lamp.exists") is False


def test_engine_observes_proposes_validates_acts_and_verifies() -> None:
    actions = registry()
    simulator = GeneratedSimulator(actions, {"lamp": {"enabled": False, "name": None, "exists": True}})

    def next_action(state, task, discovered, history):
        assert {item.id for item in discovered} == {"lamp.enable", "lamp.name", "lamp.destroy"}
        if not state.value("lamp.enabled"):
            return ActionProposal(action="lamp.enable")
        return ActionProposal(action="lamp.name", args={"name": "Ada"}, policy_version="test-policy")

    task = TaskAutomaton(
        id="name-lamp",
        milestones=[
            Milestone(id="enabled", goals=[Goal(id="lamp-on", predicate=Condition(field="lamp.enabled", value=True))]),
            Milestone(id="named", goals=[Goal(id="lamp-named", predicate=Condition(field="lamp.name", value="Ada"))]),
        ],
    )
    engine = ExecutionEngine(actions, Doer(actions, simulator), RulePolicy(next_action))
    result = engine.run(task)

    assert result.status == "succeeded"
    assert result.progress == 2
    assert [item.action for item in result.executions] == ["lamp.enable", "lamp.name"]
    assert all(item.verified for item in result.executions)


def test_engine_bounds_cycles_risk_and_cancellation() -> None:
    actions = registry()
    simulator = GeneratedSimulator(actions, {"lamp": {"enabled": False, "exists": True}})
    impossible = TaskAutomaton(
        id="bounded",
        milestones=[Milestone(id="never", goals=[Goal(id="never", predicate=Condition(field="missing", value=True))])],
    )
    looping = RulePolicy(lambda *_: ActionProposal(action="lamp.enable"))
    result = ExecutionEngine(actions, Doer(actions, simulator), looping).run(
        impossible, ExecutionLimits(max_steps=8, max_state_visits=2)
    )
    assert result.status == "failed"
    assert result.error in {"Precondition failed: lamp.enabled eq", "Cycle detected", "Maximum step limit reached"}

    cancelled = Event()
    cancelled.set()
    stopped = Doer(actions, simulator).execute(ActionProposal(action="lamp.enable"), cancelled=cancelled)
    assert stopped.status == "cancelled"

    risky = RulePolicy(lambda *_: ActionProposal(action="lamp.destroy", confirmed=True))
    risk_result = ExecutionEngine(actions, Doer(actions, simulator), risky).run(
        impossible.model_copy(update={"id": "risky"}), ExecutionLimits(max_cumulative_risk=5)
    )
    assert risk_result.status == "failed"
    assert risk_result.error == "Cumulative risk limit exceeded"


def test_factored_state_hash_is_stable_and_unknown_is_not_false() -> None:
    first = FactoredState(environment_version="v1", fields={"b": 2, "a": False}, unknown_fields={"x"})
    second = FactoredState(environment_version="v1", fields={"a": False, "b": 2}, unknown_fields={"x"})
    assert first.state_hash() == second.state_hash()
    assert Condition(field="x", operator="falsy").model_dump()["field"] == "x"
    assert Goal(id="unknown", predicate=Condition(field="x", operator="falsy")).is_satisfied(first) is False
    nested = FactoredState(environment_version="v1", fields={"wifi": {"enabled": False}}, unknown_fields={"wifi"})
    assert Goal(id="nested", predicate=Condition(field="wifi.enabled", operator="falsy")).is_satisfied(nested) is False
