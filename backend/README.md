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

Run tests with `uv run pytest`.
