#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

(cd "$project_dir/backend" && uv run backend) &
backend_pid=$!

(cd "$project_dir/frontend" && bun run dev) &
frontend_pid=$!

cleanup() {
	trap - EXIT INT TERM
	kill "$backend_pid" "$frontend_pid" 2>/dev/null || true
	wait "$backend_pid" "$frontend_pid" 2>/dev/null || true
}

trap cleanup EXIT INT TERM
wait -n "$backend_pid" "$frontend_pid"
