#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Starting Market Analysis Dashboard..."
(cd "$SCRIPT_DIR/backend" && uvicorn main:app --reload --host 0.0.0.0 --port 8000) &
BACKEND_PID=$!
(cd "$SCRIPT_DIR/frontend" && npm run dev) &
FRONTEND_PID=$!
trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null' INT TERM
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
wait $BACKEND_PID $FRONTEND_PID
