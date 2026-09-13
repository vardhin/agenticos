from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest

from backend.desktop import DesktopEnvironment, build_desktop_registry, desktop_initial_fields
from backend.environment import ActionProposal, Condition, Doer, FactoredState, GeneratedSimulator, Goal


REGISTRY = build_desktop_registry()
ACTION_IDS = [item.id for item in REGISTRY.discover()]


def arguments_for(action_id: str) -> dict[str, Any]:
    spec = REGISTRY.get(action_id)
    by_name: dict[str, Any] = {
        "app_id": "app:files", "archive_id": "archive:1", "archive_name": "bundle",
        "command": "pwd", "content": "hello", "delta": 5, "destination": "Documents",
        "device_id": "device:headphones", "direction": "next", "display_id": "display:primary",
        "duration": "5 minutes", "enabled": True, "field": "name", "file_id": "file:hero",
        "height": 600, "index": 2, "item_id": "recent:1", "key": "theme",
        "mime_type": "text/plain", "name": "example", "node_id": "file:hero",
        "node_ids": ["file:hero"], "notification_id": "notification:1", "parent": "Documents",
        "path": "Documents", "percent": 60, "position": 0, "query": "hero",
        "range": {"start": 0, "end": 1}, "rect": {"x": 0, "y": 0, "width": 10, "height": 10},
        "replacement": "world", "resolution": "1920x1080", "resource": "current_page",
        "resource_id": "file:hero", "result_id": "result:1", "section_id": "display",
        "side": "right", "ssid": "StudioNet", "target": {"kind": "screen"},
        "target_id": "editor:document", "theme": "dark", "type": "text", "url": "https://example.com",
        "url_or_query": "https://example.com", "value": {"enabled": True}, "width": 800,
        "window_id": "window:editor", "x": 10, "y": 20, "task_id": "contract-task",
    }
    fallback = {"string": "value", "integer": 1, "number": 1, "boolean": True, "array": [], "object": {}}
    expected_types: dict[str, type | tuple[type, ...]] = {
        "string": str, "integer": int, "number": (int, float), "boolean": bool,
        "array": list, "object": dict,
    }
    result: dict[str, Any] = {}
    for name, argument in spec.arguments.items():
        candidate = by_name.get(name, fallback[argument.type])
        if not isinstance(candidate, expected_types[argument.type]):
            candidate = fallback[argument.type]
        result[name] = deepcopy(candidate)
    return result


def satisfy(fields: dict[str, Any], condition: Condition, args: dict[str, Any]) -> None:
    expected = args.get(condition.value_from_argument) if condition.value_from_argument else condition.value
    target = fields
    parts = condition.field.split(".")
    for part in parts[:-1]:
        target = target.setdefault(part, {})
    key = parts[-1]
    if condition.operator in {"eq", "truthy", "exists"}:
        target[key] = expected if condition.operator == "eq" else (target.get(key) or True)
    elif condition.operator == "falsy":
        target[key] = False
    elif condition.operator == "contains":
        target[key] = [expected]
    elif condition.operator == "not_contains":
        target[key] = []
    elif condition.operator == "neq":
        target[key] = "different"


def prepared(action_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    fields = desktop_initial_fields()
    args = arguments_for(action_id)
    for condition in REGISTRY.get(action_id).preconditions:
        satisfy(fields, condition, args)
    return fields, args


@pytest.mark.parametrize("action_id", ACTION_IDS)
def test_every_action_precondition_effect_and_goal_predicate(action_id: str) -> None:
    fields, args = prepared(action_id)
    simulator = GeneratedSimulator(REGISTRY, fields)
    doer = Doer(REGISTRY, simulator)
    if action_id in {"system.undo_last", "system.redo_last"}:
        doer.execute(ActionProposal(action="display.set_theme", args={"theme": "dark"}))
        if action_id == "system.redo_last":
            doer.execute(ActionProposal(action="system.undo_last"))
    result = doer.execute(ActionProposal(
        action=action_id,
        args=args,
        confirmed=REGISTRY.get(action_id).confirmation_required,
    ))
    assert result.status == "succeeded", (action_id, result.message)
    assert result.verified
    for index, predicate in enumerate(REGISTRY.get(action_id).postconditions):
        assert Goal(id=f"{action_id}-{index}", predicate=predicate).is_satisfied(
            result.observed_state, args
        )


@pytest.mark.parametrize("action_id", [item for item in ACTION_IDS if not item.startswith("system.undo") and not item.startswith("system.redo")])
def test_generated_simulator_and_live_binding_have_equivalent_transitions(action_id: str) -> None:
    fields, args = prepared(action_id)
    simulator = GeneratedSimulator(REGISTRY, fields)
    live = DesktopEnvironment(REGISTRY, fields)
    proposal = ActionProposal(
        action=action_id,
        args=args,
        confirmed=REGISTRY.get(action_id).confirmation_required,
    )
    simulated = Doer(REGISTRY, simulator).execute(proposal)
    actual = Doer(REGISTRY, live).execute(proposal)
    assert actual.status == simulated.status
    assert actual.observed_state.fields == simulated.observed_state.fields


def test_goal_conditioning_separates_same_state_for_different_targets() -> None:
    from backend.compiler import TaskCompiler
    from backend.planning import policy_state_key

    first = TaskCompiler().compile('make a file from the clipboard and save it as "one"').automaton
    second = TaskCompiler().compile('make a file from the clipboard and save it as "two"').automaton
    assert first is not None and second is not None
    state = FactoredState(environment_version="v1", fields=desktop_initial_fields())
    assert policy_state_key(state, first) != policy_state_key(state, second)
