#!/bin/bash
set -e
echo "Starting Market Analysis Dashboard..."
cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ../frontend && npm run dev &
FRONTEND_PID=$!
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
wait $BACKEND_PID $FRONTEND_PID
