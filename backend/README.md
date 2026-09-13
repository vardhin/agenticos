# AgentOS backend

FastAPI + SQLite persistence for the simulated desktop. It owns the virtual filesystem,
whole-desktop state snapshots, action history, search, and the remote command stream.

```sh
uv sync
uv run backend
```

The API runs at `http://127.0.0.1:8000`; interactive OpenAPI docs are available at
`http://127.0.0.1:8000/docs`. The database defaults to `backend/data/agentos.db` when
started from this directory. Set `AGENTOS_DB_PATH` to choose a different file and
`AGENTOS_CORS_ORIGINS` to change the comma-separated browser origins.

Useful endpoints:

- `GET/PUT/PATCH /api/state`
- `GET/POST /api/files`, `GET/PATCH/DELETE /api/files/{id}`
- `GET /api/files/search?q=...`, `GET/PUT /api/files/{id}/content` (JSON text or raw bytes)
- `GET/POST /api/events`
- `GET/POST /api/control` (SSE subscriber / command publisher)
- `GET /api/wifi/state`, `GET /api/wifi/actions`
- `POST /api/wifi/{enable,disable,scan,connect,disconnect,forget}`
- `POST /api/agent/tasks` (compile, train/plan, execute, and verify Wi-Fi or desktop goals)

The Wi-Fi endpoints currently use a deterministic simulated adapter. All operations pass
through the action registry and Doer, so a NetworkManager adapter can replace the simulator
without changing the planner or command compiler.

## Uniform environment contract

`backend.environment` is the domain-independent control boundary. It provides factored
observations (including explicit unknown fields and task working memory), semantic goals and
ordered milestones, typed registered actions, generated simulation, structured state diffs,
and the bounded observe → propose → validate → act → verify execution loop. Policies only
return proposals; `Doer` is the sole mutation boundary.

The generic discovery and inspection endpoints are:

- `GET /api/actions` — action metadata plus environment/semantics versions
- `GET /api/environment/state` — canonical factored observation and state hash
- `GET /api/desktop/state` — complete desktop observation and state hash
- `POST /api/agent/compile` — constrained language/DSL to semantic task automata
- `POST /api/actions/{action_id}/execute` — validated, confirmed, verified execution
- `POST /api/agent/tasks/{task_id}/cancel` — request cancellation between actions
- `GET /api/agent/policies/{cache_key}` — inspect a trained Q-table and replayable traces

`backend.compiler` supports `SEQUENCE`, `AND`, `OR`, `NOT`, `UNTIL`, `IF`, `PRESERVE`, and
`CONFIRM_BEFORE`, with structured reference ambiguity. `backend.planning` supplies seeded
tabular Q-learning, replayable traces, semantics-aware policy caching, and BFS/A* baselines.
Training operates only on a simulator generated from registry effects.
Stochastic training can inject seeded transient failures; live benchmark execution uses the
same normalized failure observation so the learned policy can choose a recovery action.

Run tests with `uv run pytest`.
