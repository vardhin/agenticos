from backend.environment import Condition, Goal, Milestone, TaskAutomaton
from backend.planning import PolicyCache, QLearner, TrainingConfig, search_plan
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
