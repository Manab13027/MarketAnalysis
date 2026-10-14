#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ── Free ports before starting ────────────────────────────────────────────────
free_port() {
  local pids
  pids=$(lsof -ti:"$1" 2>/dev/null)
  if [ -n "$pids" ]; then
    echo "Freeing port $1 (PIDs: $pids)"
    echo "$pids" | xargs kill -9 2>/dev/null
    sleep 0.3
  fi
}

free_port 8000
free_port 5174

# ── Cleanup on exit (INT / TERM / EXIT) ───────────────────────────────────────
cleanup() {
  echo ""
  echo "Shutting down..."
  [ -n "$BACKEND_PID" ]  && kill "$BACKEND_PID"  2>/dev/null
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null
  # Wait briefly then force-free ports in case children spawned sub-processes
  sleep 0.5
  free_port 8000
  free_port 5174
  exit 0
}
trap cleanup INT TERM EXIT

# ── Start services ─────────────────────────────────────────────────────────────
echo "Starting Market Analysis Dashboard..."
(cd "$SCRIPT_DIR" && /Users/fighter/miniforge3/bin/uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000) &
BACKEND_PID=$!

(cd "$SCRIPT_DIR/frontend" && npm run dev) &
FRONTEND_PID=$!

echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5174"

wait $BACKEND_PID $FRONTEND_PID
