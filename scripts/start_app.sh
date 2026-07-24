#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

if [[ ! -x "$BACKEND_DIR/.venv/bin/uvicorn" ]]; then
  echo "Backend virtualenv missing: $BACKEND_DIR/.venv" >&2
  exit 1
fi
if [[ ! -x "$FRONTEND_DIR/node_modules/.bin/vite" ]]; then
  echo "Frontend dependencies missing. Run: cd frontend && npm install" >&2
  exit 1
fi

cleanup() {
  status=$?
  trap - EXIT INT TERM
  [[ -n "${BACKEND_PID:-}" ]] && kill "$BACKEND_PID" 2>/dev/null || true
  [[ -n "${FRONTEND_PID:-}" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
  wait 2>/dev/null || true
  exit "$status"
}
trap cleanup EXIT INT TERM

echo "VanRakshak backend: http://127.0.0.1:8000"
echo "VanRakshak frontend: http://127.0.0.1:5173"
(cd "$BACKEND_DIR" && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000) & BACKEND_PID=$!
(cd "$FRONTEND_DIR" && npm run dev -- --host 127.0.0.1) & FRONTEND_PID=$!
wait -n "$BACKEND_PID" "$FRONTEND_PID"
