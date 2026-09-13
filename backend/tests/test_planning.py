from backend.compiler import TaskCompiler
from backend.desktop import DesktopEnvironment, build_desktop_registry, desktop_initial_fields
from backend.environment import (
    ActionProposal,
    Condition,
    Doer,
    ExecutionEngine,
    ExecutionLimits,
    Goal,
    Milestone,
    TaskAutomaton,
)
from backend.planning import AdaptivePolicy, PolicyCache, QLearner, TrainingConfig, search_plan
from backend.wifi import SimulatedWifiAdapter, build_action_registry


def connected_task() -> TaskAutomaton:
    return TaskAutomaton(
        id="connect-studionet",
        milestones=[
            Milestone(
                id="connected",
                goals=[Goal(id="ssid", predicate=Condition(field="wifi.ssid", value="StudioNet"))],
            )
        ],
    )


def initial_fields() -> dict:
    return {
        "wifi": {
            "enabled": False,
            "connected": False,
            "ssid": None,
            "known_networks": ["PineHouse", "StudioNet"],
            "visible_ssids": [],
            "internet_available": False,
        }
    }


def test_bfs_and_astar_discover_registry_driven_plan() -> None:
    registry = build_action_registry(SimulatedWifiAdapter())
    expected = ["wifi.enable", "wifi.scan", "wifi.connect"]
    for algorithm in ("bfs", "astar"):
        plan = search_plan(registry, connected_task(), initial_fields(), algorithm=algorithm)
        assert plan is not None
        assert [item.action for item in plan] == expected


def test_q_learning_is_seeded_inspectable_and_cached() -> None:
    registry = build_action_registry(SimulatedWifiAdapter())
    cache = PolicyCache()
    learner = QLearner(registry, cache)
    config = TrainingConfig(episodes=300, max_steps=12, seed=42)
    first = learner.train(connected_task(), initial_fields(), config)
    second = learner.train(connected_task(), initial_fields(), config)

    assert first is second
    assert cache.misses == 1
    assert cache.hits == 1
    assert first.action_space == [item.id for item in registry.discover()]
    assert len(first.traces) == 300
    assert first.traces[-1].succeeded is True
    assert first.q_table


def test_action_semantics_change_invalidates_policy_cache() -> None:
    adapter = SimulatedWifiAdapter()
    first_registry = build_action_registry(adapter)
    cache = PolicyCache()
    first_key = cache.key(first_registry, connected_task())
    first_registry.get("wifi.scan").cost = 99
    second_key = cache.key(first_registry, connected_task())
    assert first_key != second_key


def test_planner_discovers_the_ten_action_clipboard_report_workflow() -> None:
    compiled = TaskCompiler().compile(
        "Read the clipboard, create a Reports folder, make a new document, paste the clipboard, "
        "save it as hero, close the editor, open Files, find hero, move it into Reports, and star it."
    )
    assert compiled.automaton is not None

    plan = search_plan(
        build_desktop_registry(),
        compiled.automaton,
        desktop_initial_fields(),
        algorithm="astar",
        max_steps=30,
    )

    assert plan is not None
    assert [item.action for item in plan] == [
        "clipboard.read_current",
        "filesystem.create_folder",
        "editor.new_document",
        "editor.paste_content",
        "editor.save_as",
        "editor.close_document",
        "application.launch",
        "filesystem.search",
        "filesystem.move",
        "filesystem.star",
    ]


def test_learned_policy_completes_the_cross_workspace_writing_workflow() -> None:
    compiled = TaskCompiler().compile(
        "Open workspace two, launch Files, find hero, copy its contents, switch to workspace one, "
        "open the editor, create a document, paste it, save it as hero-copy, and close it."
    )
    assert compiled.automaton is not None
    task = compiled.automaton
    registry = build_desktop_registry()
    environment = DesktopEnvironment(registry)
    doer = Doer(registry, environment)
    started = doer.execute(
        ActionProposal(action="system.begin_task", args={"task_id": task.id})
    )
    assert started.status == "succeeded"
    initial = environment.observe().fields

    plan = search_plan(registry, task, initial, algorithm="astar", max_steps=30)
    assert plan is not None
    assert [proposal.action for proposal in plan] == [
        "workspace.switch",
        "application.launch",
        "filesystem.search",
        "filesystem.read",
        "workspace.switch",
        "editor.open",
        "editor.new_document",
        "editor.paste_content",
        "editor.save_as",
        "editor.close_document",
    ]
    assert [proposal.args for proposal in plan if proposal.action == "workspace.switch"] == [
        {"index": 2},
        {"index": 1},
    ]

    trained = QLearner(registry).train(
        task,
        initial,
        TrainingConfig(episodes=220, max_steps=40),
    )
    assert all(trace.succeeded for trace in trained.traces)

    result = ExecutionEngine(registry, doer, AdaptivePolicy(registry, trained)).run(
        task,
        ExecutionLimits(max_steps=40, max_state_visits=5),
    )

    assert result.status == "succeeded"
    assert result.progress == 10
    assert [item.action for item in result.executions] == [
        proposal.action for proposal in plan
    ]
    assert result.final_state.value("workspace.current") == 1
    assert result.final_state.value("editor.filename") == "hero-copy"
    assert result.final_state.value("editor.document_open") is False


def test_learned_policy_completes_the_settings_evidence_workflow() -> None:
    compiled = TaskCompiler().compile(
        "Turn on dark mode, set brightness to 60%, enable Do Not Disturb, take a screenshot, "
        "save it as setup, open Files, find setup, move it to Pictures, star it, and return to the desktop."
    )
    assert compiled.automaton is not None
    task = compiled.automaton
    registry = build_desktop_registry()
    environment = DesktopEnvironment(registry)
    doer = Doer(registry, environment)
    started = doer.execute(
        ActionProposal(action="system.begin_task", args={"task_id": task.id})
    )
    assert started.status == "succeeded"
    initial = environment.observe().fields

    plan = search_plan(registry, task, initial, algorithm="astar", max_steps=30)
    assert plan is not None
    assert [(proposal.action, proposal.args) for proposal in plan] == [
        ("display.set_theme", {"theme": "dark"}),
        ("display.set_brightness", {"percent": 60}),
        ("notification.set_dnd", {"enabled": True}),
        ("capture.fullscreen", {}),
        ("capture.save", {"name": "setup", "parent": "Pictures"}),
        ("application.launch", {"app_id": "app:files"}),
        ("filesystem.search", {"query": "setup"}),
        ("filesystem.move", {"node_id": "file:search-result", "parent": "Pictures"}),
        ("filesystem.star", {"node_id": "file:search-result", "enabled": True}),
        ("system.show_desktop", {}),
    ]

    trained = QLearner(registry).train(
        task,
        initial,
        TrainingConfig(episodes=220, max_steps=40),
    )
    assert all(trace.succeeded for trace in trained.traces)

    result = ExecutionEngine(registry, doer, AdaptivePolicy(registry, trained)).run(
        task,
        ExecutionLimits(max_steps=40, max_state_visits=5),
    )

    assert result.status == "succeeded"
    assert result.progress == 10
    assert [item.action for item in result.executions] == [
        proposal.action for proposal in plan
    ]
    assert result.final_state.value("display.theme") == "dark"
    assert result.final_state.value("display.brightness") == 60
    assert result.final_state.value("notification.dnd") is True
    assert result.final_state.value("capture.saved_name") == "setup"
    assert result.final_state.value("filesystem.last_parent") == "Pictures"
    assert result.final_state.value("filesystem.starred") is True
    assert result.final_state.value("system.desktop_visible") is True


def test_learned_policy_observes_a_timeout_and_recovers_instead_of_replaying_a_fixed_plan() -> None:
    compiled = TaskCompiler().compile(
        "Connect to StudioNet, verify internet access, open the browser, visit the project page, "
        "copy its address, make a note from it, save it as online, move it to Research, and star it."
    )
    assert compiled.automaton is not None
    task = compiled.automaton
    registry = build_desktop_registry()
    environment = DesktopEnvironment(registry)
    doer = Doer(registry, environment)
    started = doer.execute(
        ActionProposal(action="system.begin_task", args={"task_id": task.id})
    )
    assert started.status == "succeeded"
    initial = environment.observe().fields

    deterministic_plan = search_plan(
        registry,
        task,
        initial,
        algorithm="astar",
        max_steps=30,
    )
    assert deterministic_plan is not None
    assert len(deterministic_plan) == 10

    trained = QLearner(registry).train(
        task,
        initial,
        TrainingConfig(episodes=600, max_steps=40),
    )
    assert any(trace.failures for trace in trained.traces)
    assert sum(trace.succeeded for trace in trained.traces) >= 590

    environment.inject_failures({"wifi.connect": 1})
    policy = AdaptivePolicy(registry, trained)
    result = ExecutionEngine(registry, doer, policy).run(
        task,
        ExecutionLimits(max_steps=40, max_state_visits=5),
    )

    assert result.status == "succeeded"
    assert result.progress == 10
    assert [(item.action, item.status) for item in result.executions] == [
        ("wifi.connect", "failed"),
        ("wifi.connect", "succeeded"),
        ("wifi.test_internet", "succeeded"),
        ("browser.open", "succeeded"),
        ("browser.navigate", "succeeded"),
        ("browser.copy_url", "succeeded"),
        ("editor.new_document", "succeeded"),
        ("editor.paste_content", "succeeded"),
        ("editor.save_as", "succeeded"),
        ("filesystem.move", "succeeded"),
        ("filesystem.star", "succeeded"),
    ]
    assert "timeout" in result.executions[0].message
    assert result.final_state.value("task.last_failure") == {
        "action": "wifi.connect",
        "code": "action_failed",
        "recoverable": True,
    }
    assert policy.replans == 0
